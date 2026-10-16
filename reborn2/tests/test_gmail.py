"""Gmail connector tests. Gmail's REST API is faked in-process (httpx.request is replaced),
so nothing here touches Google."""
import base64
import email
import time
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from api import gmail, service
from api.main import app


def _b(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _msg(mid, tid, sender, subject, body, labels=("INBOX",), message_id=None):
    return {"id": mid, "threadId": tid, "labelIds": list(labels), "snippet": body[:40],
            "payload": {"mimeType": "multipart/alternative",
                        "headers": [{"name": "From", "value": sender}, {"name": "Subject", "value": subject},
                                    {"name": "Message-ID", "value": message_id or f"<{mid}@mail.example>"}],
                        "parts": [{"mimeType": "text/plain", "body": {"data": _b(body)}},
                                  {"mimeType": "text/html", "body": {"data": _b("<p>html</p>")}}]}}


THREADS = {
    "t1": [_msg("m1", "t1", "Ann Lee <ann@example.com>", "Interview schedule",
                "Hi, can we move the interview to Friday?\n\nOn Mon, 5 Oct 2026, Team wrote:\n> old text")],
    "t2": [_msg("m2", "t2", "Bo <bo@example.com>", "Salary question", "What is the pay band?"),
           _msg("m3", "t2", "me@example.com", "Re: Salary question", "We will share it soon.", labels=("SENT",))],
}
CALLS: list[tuple[str, str, dict]] = []


def _fake_request(method, url, params=None, json=None, headers=None, timeout=None):
    path = urlparse(url).path.replace("/gmail/v1", "")
    CALLS.append((method, path, {"params": params, "json": json}))
    assert headers["Authorization"] == "Bearer test-token"

    def ok(data):
        return httpx.Response(200, json=data, request=httpx.Request(method, url))

    if method == "GET" and path == "/users/me/threads":
        return ok({"threads": [{"id": t} for t in THREADS][: int(params["maxResults"])]})
    if method == "GET" and path.startswith("/users/me/threads/"):
        tid = path.rsplit("/", 1)[1]
        return ok({"id": tid, "messages": THREADS[tid]})
    if method == "GET" and path.startswith("/users/me/messages/"):
        mid = path.rsplit("/", 1)[1]
        for msgs in THREADS.values():
            for m in msgs:
                if m["id"] == mid:
                    return ok(m)
    if method == "GET" and path == "/users/me/profile":
        return ok({"emailAddress": "me@example.com"})
    if method == "POST" and path == "/users/me/messages/send":
        return ok({"id": "sent1", "threadId": json.get("threadId", "")})
    return httpx.Response(404, json={"error": {"message": "not found"}}, request=httpx.Request(method, url))


def _sent_calls():
    return [c for c in CALLS if c[0] == "POST" and c[1] == "/users/me/messages/send"]


@pytest.fixture()
def fake_gmail(tmp_path, monkeypatch):
    CALLS.clear()
    monkeypatch.setattr(gmail, "CONFIG_PATH", tmp_path / "gmail.json")
    monkeypatch.setattr(gmail, "TOKEN_PATH", tmp_path / "token.json")
    monkeypatch.setattr(gmail, "_access_token", lambda: "test-token")
    monkeypatch.setattr(gmail.httpx, "request", _fake_request)
    # keep the real data/ folder untouched
    monkeypatch.setattr(service, "SESSION_PATH", tmp_path / "session.json")
    monkeypatch.setattr(service, "HISTORY_DIR", tmp_path / "history")
    monkeypatch.setattr(service, "OUTBOX_PATH", tmp_path / "outbox" / "sent.csv")
    yield


def test_build_query():
    assert gmail.build_query() == "in:inbox -from:me"
    assert gmail.build_query("interview") == "in:inbox -from:me subject:interview"
    q = gmail.build_query("quest status, offer letter", "2026-10-01", "2026-10-31")
    assert 'subject:(quest status OR "offer letter")' not in q  # multi-word terms are quoted
    assert 'subject:("quest status" OR "offer letter")' in q
    assert "after:2026/10/01" in q and "before:2026/11/01" in q  # To date is inclusive
    with pytest.raises(gmail.GmailError):
        gmail.build_query("", "10/01/2026", "")
    with pytest.raises(gmail.GmailError):
        gmail.build_query("", "2026-10-10", "2026-10-01")


def test_clean_body_drops_quoted_history():
    text = "Thanks!\n> earlier\nOn Mon, 5 Oct 2026, Team <t@x.com> wrote:\nstuff"
    assert gmail._clean_body(text) == "Thanks!"


def test_fetch_messages_reads_latest_incoming_per_thread(fake_gmail):
    rows = gmail.fetch_messages("interview, salary", "", "", 10)
    assert [r["id"] for r in rows] == ["m1", "m2"]  # m3 is ours (SENT), so m2 is used
    assert rows[0]["email"] == "ann@example.com" and rows[0]["sender"] == "Ann Lee"
    assert "old text" not in rows[0]["body"] and rows[0]["thread_id"] == "t1"
    listing = [c for c in CALLS if c[1] == "/users/me/threads"][0]
    assert "subject:(interview OR salary)" in listing[2]["params"]["q"]


def test_end_to_end_fetch_approve_send(fake_gmail):
    client = TestClient(app)
    batch = client.post("/api/gmail/fetch", json={"keywords": "interview", "limit": 5}).json()
    assert len(batch["items"]) == 2 and all(i["source"] == "gmail" for i in batch["items"])
    for _ in range(100):  # wait for the offline pipeline
        if client.get("/api/items").json()["run"]["state"] == "done":
            break
        time.sleep(0.05)
    item = next(i for i in client.get("/api/items").json()["items"] if i["message_id"] == "m1")

    # not approved yet: must refuse to send
    assert client.post(f"/api/items/{item['key']}/send").status_code == 409
    assert not _sent_calls()

    draft = "Hi Ann, Friday works. Please share 2-3 slots."
    assert client.patch(f"/api/items/{item['key']}", json={"draft": draft, "status": "approved"}).status_code == 200
    sent = client.post(f"/api/items/{item['key']}/send").json()
    assert sent["status"] == "sent"
    (call,) = _sent_calls()
    assert call[2]["json"]["threadId"] == "t1"
    raw = base64.urlsafe_b64decode(call[2]["json"]["raw"] + "==")
    mail = email.message_from_bytes(raw)
    assert mail["To"] == "ann@example.com" and mail["Subject"] == "Re: Interview schedule"
    assert mail["In-Reply-To"] == "<m1@mail.example>"
    assert mail.get_payload().strip() == draft
    assert (service.OUTBOX_PATH).is_file()  # still logged locally


def test_connection_check_reports_account(fake_gmail):
    result = gmail.check_connection()
    assert result["ok"] and result["missing"] == [] and "me@example.com" in result["tools"][0]


def test_api_errors_are_explained(tmp_path, monkeypatch):
    monkeypatch.setattr(gmail, "CONFIG_PATH", tmp_path / "gmail.json")
    monkeypatch.setattr(gmail, "_access_token", lambda: "t")

    def fail(code, msg):
        return lambda *a, **k: httpx.Response(code, json={"error": {"message": msg}},
                                              request=httpx.Request("GET", "http://x"))

    monkeypatch.setattr(gmail.httpx, "request", fail(403, "Gmail API has not been used in project 1 before or it is disabled."))
    with pytest.raises(gmail.GmailError, match="not enabled"):
        gmail.check_connection()
    monkeypatch.setattr(gmail.httpx, "request", fail(401, "Invalid Credentials"))
    with pytest.raises(gmail.GmailError, match="Connect Gmail"):
        gmail.check_connection()


def test_old_mcp_url_in_settings_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(gmail, "CONFIG_PATH", tmp_path / "gmail.json")
    gmail.update_config({"mcp_url": "https://gmailmcp.googleapis.com/mcp/v1"})
    assert gmail._api_base() == "https://gmail.googleapis.com/gmail/v1"


def test_oauth_url_and_token_exchange(tmp_path, monkeypatch):
    monkeypatch.setattr(gmail, "CONFIG_PATH", tmp_path / "gmail.json")
    monkeypatch.setattr(gmail, "TOKEN_PATH", tmp_path / "token.json")
    with pytest.raises(gmail.GmailError):
        gmail.authorize_url()  # no client id yet
    gmail.update_config({"client_id": "cid.apps.googleusercontent.com", "client_secret": "sekret-1234"})
    url = gmail.authorize_url("http://localhost:5173")
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    assert q["client_id"] == "cid.apps.googleusercontent.com" and q["code_challenge_method"] == "S256"
    assert q["redirect_uri"] == "http://localhost:8000/api/gmail/callback"
    assert q["access_type"] == "offline" and "gmail.readonly" in q["scope"] and "gmail.compose" in q["scope"]

    sent = {}

    class Resp:
        status_code = 200
        text = ""
        def json(self):
            return {"access_token": "at", "refresh_token": "rt", "expires_in": 3600, "scope": "x"}

    monkeypatch.setattr(gmail.httpx, "post", lambda url, data=None, timeout=0: sent.update(data) or Resp())
    assert gmail.return_to_for(q["state"]) == "http://localhost:5173"
    assert gmail.finish_auth("the-code", q["state"]) == "http://localhost:5173"
    assert sent["code"] == "the-code" and sent["code_verifier"] and sent["client_secret"] == "sekret-1234"
    st = gmail.status()
    assert st["connected"] and st["configured"] and st["secret_hint"] == "••••1234"
    assert "client_secret" not in st  # the secret is never sent back to the page
    with pytest.raises(gmail.GmailError):
        gmail.finish_auth("again", q["state"])  # state is single-use
    assert not gmail.disconnect()["connected"]


def test_return_to_only_local_addresses():
    assert gmail._safe_origin("https://evil.example.com/x") == ""
    assert gmail._safe_origin("http://localhost:5173/#/") == "http://localhost:5173"