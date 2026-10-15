"""Gmail connector: Google sign-in (OAuth) plus the regular Gmail REST API.

What lives here
  * settings   data/gmail.json  (client id/secret, server URL, scopes, redirect URI)
  * login      data/gmail_token.json  (written after you click "Connect Gmail")
  * reading    fetch_messages()  -> rows the pipeline already understands
  * sending    send_reply()      -> replies in the original Gmail thread

Nothing here sends mail on its own. service.send() calls send_reply() only
for a draft the person approved and then clicked Send on.

Setup values can also come from the environment, so you can skip the Settings
screen: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GMAIL_MCP_URL, GMAIL_REDIRECT_URI.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlencode, urlparse

import httpx

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "data" / "gmail.json"
TOKEN_PATH = ROOT / "data" / "gmail_token.json"

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

DEFAULTS = {
    "client_id": "",
    "client_secret": "",
    "mcp_url": "https://gmail.googleapis.com/gmail/v1",  # name kept for the Settings page; this is the REST base
    # read the inbox + send mail (gmail.compose is enough for messages.send)
    "scopes": ("https://www.googleapis.com/auth/gmail.readonly "
               "https://www.googleapis.com/auth/gmail.compose"),
    "redirect_uri": "http://localhost:8000/api/gmail/callback",
}
_ENV = {
    "client_id": "GOOGLE_CLIENT_ID",
    "client_secret": "GOOGLE_CLIENT_SECRET",
    "mcp_url": "GMAIL_MCP_URL",
    "redirect_uri": "GMAIL_REDIRECT_URI",
}

MAX_FETCH = 100
MAX_BODY_CHARS = 8000
_lock = threading.RLock()
_pending: dict[str, dict] = {}  # OAuth state -> {verifier, return_to, created}


class GmailError(Exception):
    """A problem the person can act on. `detail` is shown in the page."""

    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


# --- settings -----------------------------------------------------------------

def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)  # holds secrets
        except OSError:
            pass
        os.replace(tmp, path)
    except OSError as e:
        raise GmailError(f"Could not save {path.name}: {e}", 500)


def config() -> dict:
    """Saved settings first, then environment variables, then defaults."""
    saved = _read_json(CONFIG_PATH)
    out = {}
    for key, default in DEFAULTS.items():
        value = saved.get(key)
        if not (isinstance(value, str) and value.strip()):
            value = os.getenv(_ENV[key], "") if key in _ENV else ""
        out[key] = value.strip() if value and value.strip() else default
    return out


def update_config(patch: dict) -> dict:
    with _lock:
        saved = _read_json(CONFIG_PATH)
        for key in DEFAULTS:
            value = patch.get(key)
            if value is None:
                continue
            value = value.strip()
            if value:
                saved[key] = value
            else:
                saved.pop(key, None)  # blank = back to the default
        _write_json(CONFIG_PATH, saved)
    return status()


def _token() -> dict:
    return _read_json(TOKEN_PATH)


def status() -> dict:
    cfg = config()
    tok = _token()
    secret = cfg["client_secret"]
    return {
        "client_id": cfg["client_id"],
        "secret_set": bool(secret),
        "secret_hint": f"••••{secret[-4:]}" if len(secret) >= 8 else ("set" if secret else ""),
        "mcp_url": cfg["mcp_url"],
        "scopes": cfg["scopes"],
        "redirect_uri": cfg["redirect_uri"],
        "configured": bool(cfg["client_id"] and secret),
        "connected": bool(tok.get("refresh_token") or tok.get("access_token")),
        "connected_at": tok.get("connected_at", ""),
    }


def disconnect() -> dict:
    with _lock:
        try:
            TOKEN_PATH.unlink()
        except FileNotFoundError:
            pass
        except OSError as e:
            raise GmailError(f"Could not remove the saved login: {e}", 500)
    return status()


# --- Google sign-in (OAuth with PKCE) -------------------------------------------

def _safe_origin(return_to: str) -> str:
    """Where to send the browser afterwards. Local addresses only."""
    try:
        u = urlparse(return_to)
        if u.scheme in ("http", "https") and u.hostname in ("localhost", "127.0.0.1", "::1"):
            return f"{u.scheme}://{u.netloc}"
    except ValueError:
        pass
    return ""


def return_to_for(state: str) -> str:
    """The page that started this sign-in (empty if unknown), without using the state up."""
    with _lock:
        return (_pending.get(state) or {}).get("return_to", "")


def authorize_url(return_to: str = "") -> str:
    cfg = config()
    if not (cfg["client_id"] and cfg["client_secret"]):
        raise GmailError("Add the Google client ID and client secret in Settings first.", 409)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    with _lock:
        now = time.time()
        for s in [s for s, v in _pending.items() if now - v["created"] > 900]:
            _pending.pop(s, None)  # forget sign-ins nobody finished
        _pending[state] = {"verifier": verifier, "return_to": _safe_origin(return_to), "created": now}
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": cfg["scopes"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",   # gives us a refresh token
        "prompt": "consent",        # ...every time, even on a second sign-in
        "include_granted_scopes": "true",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _google_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        text = body.get("error_description") or body.get("error") or resp.text
    except ValueError:
        text = resp.text
    return str(text)[:300]


def finish_auth(code: str, state: str) -> str:
    """Trade the code Google sent back for a login. Returns the page to open next."""
    with _lock:
        pending = _pending.pop(state, None)
    if pending is None:
        raise GmailError("That sign-in link expired or was already used. Click Connect Gmail again.", 400)
    cfg = config()
    try:
        resp = httpx.post(TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": cfg["redirect_uri"],
            "code_verifier": pending["verifier"],
        }, timeout=20)
    except httpx.HTTPError as e:
        raise GmailError(f"Could not reach Google: {e}")
    if resp.status_code != 200:
        raise GmailError(f"Google refused the sign-in: {_google_error(resp)}", 400)
    data = resp.json()
    old = _token()
    _write_json(TOKEN_PATH, {
        "access_token": data.get("access_token", ""),
        # Google only sends a refresh token on first consent; keep the old one otherwise.
        "refresh_token": data.get("refresh_token") or old.get("refresh_token", ""),
        "expires_at": time.time() + int(data.get("expires_in", 3600)),
        "scope": data.get("scope", ""),
        "connected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return pending["return_to"]


def _access_token() -> str:
    with _lock:
        tok = _token()
        if not tok.get("access_token") and not tok.get("refresh_token"):
            raise GmailError("Gmail is not connected. Open Settings and click Connect Gmail.", 409)
        if tok.get("access_token") and tok.get("expires_at", 0) - time.time() > 60:
            return tok["access_token"]
        if not tok.get("refresh_token"):
            raise GmailError("The Gmail login expired. Click Connect Gmail again.", 409)
        cfg = config()
        try:
            resp = httpx.post(TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": tok["refresh_token"],
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
            }, timeout=20)
        except httpx.HTTPError as e:
            raise GmailError(f"Could not reach Google: {e}")
        if resp.status_code != 200:
            raise GmailError("Google no longer accepts the saved login "
                             f"({_google_error(resp)}). Click Connect Gmail again.", 409)
        data = resp.json()
        tok.update(access_token=data["access_token"],
                   expires_at=time.time() + int(data.get("expires_in", 3600)))
        _write_json(TOKEN_PATH, tok)
        return tok["access_token"]


# --- talking to the Gmail REST API ---------------------------------------------------
#
# Why REST and not Google's Gmail MCP server: that server is in Google's Workspace
# Developer Preview, which only accepts Workspace (paid) accounts. The REST API works
# with any Gmail account and uses the same OAuth login and scopes.

def _api_base() -> str:
    url = config()["mcp_url"].rstrip("/")
    if "mcp" in url.lower():  # an old saved MCP address: use the REST one
        return DEFAULTS["mcp_url"].split("  #")[0]
    return url


def _api(method: str, path: str, *, params: dict | None = None, json_body: dict | None = None) -> dict:
    """One call to the Gmail API. Raises GmailError with a message the person can act on."""
    headers = {"Authorization": f"Bearer {_access_token()}"}
    try:
        resp = httpx.request(method, f"{_api_base()}{path}", params=params, json=json_body,
                             headers=headers, timeout=30)
    except httpx.HTTPError as e:
        raise GmailError(f"Could not reach Gmail: {e}"[:400])
    if resp.status_code < 300:
        try:
            return resp.json()
        except ValueError:
            return {}
    reason = _google_error(resp)
    try:  # Google's API errors look like {"error": {"message": ..., "status": ...}}
        err = resp.json().get("error")
        if isinstance(err, dict):
            reason = str(err.get("message") or reason)[:300]
    except ValueError:
        pass
    if resp.status_code == 401:
        raise GmailError("Gmail rejected the login. Click Connect Gmail again.", 409)
    if resp.status_code == 403:
        low = reason.lower()
        if "has not been used" in low or "disabled" in low:
            raise GmailError("The Gmail API is not enabled in your Google Cloud project. "
                             "Open APIs & Services, Library, enable \"Gmail API\", wait a minute, "
                             f"and try again. ({reason})", 403)
        if "scope" in low or "insufficient" in low:
            raise GmailError("The saved login is missing a permission. Click Connect Gmail again "
                             "and tick every box on Google's page.", 409)
        raise GmailError(f"Google blocked the request (403): {reason}", 403)
    if resp.status_code == 429:
        raise GmailError("Gmail says too many requests. Wait a minute and try again.", 429)
    raise GmailError(f"Gmail answered with an error ({resp.status_code}): {reason}")


# --- reading what comes back -----------------------------------------------------------

def _b64(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return ""


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", html)
    text = re.sub(r"<[^>]+>", "", html)
    import html as _html
    return re.sub(r"\n{3,}", "\n\n", _html.unescape(text))


def _find_part(payload: dict, mime: str) -> str:
    """Body text of the first part with this mime type (depth first)."""
    if not isinstance(payload, dict):
        return ""
    if payload.get("mimeType") == mime and (payload.get("body") or {}).get("data"):
        return _b64(payload["body"]["data"])
    for part in payload.get("parts") or []:
        found = _find_part(part, mime)
        if found:
            return found
    return ""


def _message_text(msg: dict) -> str:
    payload = msg.get("payload") or {}
    text = _find_part(payload, "text/plain")
    if not text:
        html = _find_part(payload, "text/html")
        text = _strip_html(html) if html else ""
    return text or str(msg.get("snippet", ""))


def _headers(msg: dict) -> dict[str, str]:
    return {h.get("name", "").lower(): h.get("value", "")
            for h in (msg.get("payload") or {}).get("headers", []) if isinstance(h, dict)}


_QUOTE_RE = re.compile(r"^(>.*|On .{5,200} wrote:)$", re.I)


def _clean_body(text: str) -> str:
    """Drop quoted history so the safety check and drafter see only the new message."""
    kept = []
    for line in str(text or "").replace("\r\n", "\n").split("\n"):
        if _QUOTE_RE.match(line.strip()):
            if line.strip().startswith(">"):
                continue
            break  # "On <date>, X wrote:" starts the quoted part
        kept.append(line)
    return "\n".join(kept).strip()[:MAX_BODY_CHARS]


# --- public: search and read ---------------------------------------------------------

def _parse_day(value: str, field: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise GmailError(f"{field} must look like 2026-10-31.", 422)


def _term(word: str) -> str:
    word = word.replace('"', "").strip()
    return f'"{word}"' if re.search(r"\s", word) else word


def build_query(keywords: str = "", after: str = "", before: str = "") -> str:
    """Gmail search text. Keywords (comma separated) match the subject; any one is enough."""
    parts = ["in:inbox", "-from:me"]
    words = [w for w in (k.strip() for k in (keywords or "").split(",")) if w]
    if len(words) == 1:
        parts.append(f"subject:{_term(words[0])}")
    elif words:
        parts.append("subject:(" + " OR ".join(_term(w) for w in words) + ")")
    start, end = _parse_day(after, "From date"), _parse_day(before, "To date")
    if start and end and end < start:
        raise GmailError("The To date is before the From date.", 422)
    if start:
        parts.append("after:" + start.strftime("%Y/%m/%d"))
    if end:  # Gmail's "before" is exclusive; make the To date inclusive
        parts.append("before:" + (end + timedelta(days=1)).strftime("%Y/%m/%d"))
    return " ".join(parts)


def _row_from_message(msg: dict, thread_id: str) -> dict | None:
    labels = msg.get("labelIds") or []
    if "SENT" in labels or "DRAFT" in labels:
        return None  # that one is ours
    message_id = str(msg.get("id", ""))
    if not message_id:
        return None
    h = _headers(msg)
    name, address = parseaddr(h.get("from", ""))
    return {
        "id": message_id,
        "sender": name or address or "Unknown sender",
        "email": address,
        "subject": h.get("subject", ""),
        "body": _clean_body(_message_text(msg)),
        "source": "gmail",
        "thread_id": thread_id or str(msg.get("threadId", "")),
        "message_id": message_id,
    }


def fetch_messages(keywords: str = "", after: str = "", before: str = "", limit: int = 25) -> list[dict]:
    """Newest matching threads from the inbox, one row per thread (its latest incoming message)."""
    limit = max(1, min(int(limit or 25), MAX_FETCH))
    found = _api("GET", "/users/me/threads",
                 params={"q": build_query(keywords, after, before), "maxResults": limit})
    rows = []
    for t in (found.get("threads") or [])[:limit]:
        tid = str(t.get("id", ""))
        if not tid:
            continue
        full = _api("GET", f"/users/me/threads/{tid}", params={"format": "full"})
        for msg in reversed(full.get("messages") or []):  # newest first
            row = _row_from_message(msg, tid)
            if row:
                rows.append(row)
                break
    return rows


# --- public: send --------------------------------------------------------------------

def send_reply(message_id: str, thread_id: str, body: str, to: str = "", subject: str = "") -> None:
    """Reply to one Gmail message, inside its thread. Raises GmailError on any failure."""
    if not (body or "").strip():
        raise GmailError("The reply is empty.", 422)
    if not message_id:
        raise GmailError("This message has no Gmail id, so it can't be answered through Gmail.", 422)

    # Read the original's headers so the reply threads properly in the other person's mail app too.
    orig = _api("GET", f"/users/me/messages/{message_id}",
                params=[("format", "metadata"), ("metadataHeaders", "From"), ("metadataHeaders", "Reply-To"),
                        ("metadataHeaders", "Subject"), ("metadataHeaders", "Message-ID"),
                        ("metadataHeaders", "References")])
    h = _headers(orig)
    recipient = parseaddr(h.get("reply-to") or h.get("from") or "")[1] or to
    if not recipient:
        raise GmailError("Could not work out who to reply to.", 422)
    orig_subject = h.get("subject") or subject or "your message"
    msg = EmailMessage()
    msg["To"] = recipient
    msg["Subject"] = orig_subject if re.match(r"(?i)^re:", orig_subject) else f"Re: {orig_subject}"
    if h.get("message-id"):
        msg["In-Reply-To"] = h["message-id"]
        msg["References"] = (h.get("references", "") + " " + h["message-id"]).strip()
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    tid = thread_id or orig.get("threadId", "")
    if tid:
        payload["threadId"] = tid
    _api("POST", "/users/me/messages/send", json_body=payload)


def check_connection() -> dict:
    """Ask Gmail who we are signed in as. Proves the login and the Gmail API setting work."""
    prof = _api("GET", "/users/me/profile")
    who = prof.get("emailAddress", "your account")
    return {"ok": True, "tools": [f"Signed in as {who}", "threads.list", "threads.get", "messages.send"],
            "missing": []}