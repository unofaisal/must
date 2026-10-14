"""Review-session logic behind the web page.

One in-memory session for one user: upload a CSV, the pipeline runs once,
and the human then edits, approves, rejects, and sends each reply.
Restarting the server clears the session. Sent replies are kept in
outbox/sent.csv.
"""
from __future__ import annotations

import csv
import io
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from src.drafting import Drafter, find_placeholders
from src.grouping import Grouper
from src.inbox_helper import load_candidates, process_row, read_rows
from src.safety import SafetyGate

ROOT = Path(__file__).resolve().parent.parent
OUTBOX_PATH = ROOT / "outbox" / "sent.csv"
MAX_BYTES = 1_000_000
MAX_ROWS = 500
MAX_DRAFT_CHARS = 5000
WORKERS = 4  # messages processed in parallel (matters with live models)

_lock = threading.RLock()
_items: dict[str, dict] = {}
_mode = "offline"


class ServiceError(Exception):
    """An error the page can show to the user as-is."""

    def __init__(self, detail: str, status_code: int = 409):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


# --- providers --------------------------------------------------------------

def current_mode() -> str:
    return "live" if os.getenv("OPENROUTER_API_KEY", "").strip() else "offline"


def build_pipeline():
    """Pick the models for a run. This is the one place a settings page
    (keys, provider, model) will plug in later."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key:
        from src.harness.chat import ChatProvider
        from src.harness.decide import DecideProvider
        decide = DecideProvider(api_key=key)
        return Grouper(decide), Drafter(ChatProvider(api_key=key)), SafetyGate(decide), "live"
    return Grouper(), Drafter(), SafetyGate(), "offline"


# --- helpers ----------------------------------------------------------------

def _cell(value) -> str:
    """Stop spreadsheet apps from running an email's text as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _public(item: dict) -> dict:
    return {**item, "placeholders": find_placeholders(item["draft"])}


def _get(key: str) -> dict:
    item = _items.get(key)
    if item is None:
        raise ServiceError("That message is not in the current batch.", 404)
    return item


def _check_sendable(item: dict) -> None:
    if not item["draft"].strip():
        raise ServiceError("Write a reply before approving.")
    missing = find_placeholders(item["draft"])
    if missing:
        raise ServiceError("Fill in " + ", ".join(f"[{p}]" for p in missing)
                           + " before approving.")


def _new_item(key: str, row: dict, result, quarantine) -> dict:
    base = {"key": key, "id": row.get("id") or "", "sender": row.get("sender") or "",
            "email": row.get("email") or "", "subject": row.get("subject") or "",
            "body": row.get("body") or "", "status": "pending", "sent_at": None}
    if quarantine:
        return {**base, "kind": "quarantined", "labels": [], "primary": "", "confidence": "",
                "draft": "", "draft_source": "", "reasons": quarantine["reasons"]}
    return {**base, "kind": "draft", "labels": result.labels, "primary": result.intent,
            "confidence": result.confidence, "draft": result.draft,
            "draft_source": result.draft_source, "reasons": []}


# --- session ----------------------------------------------------------------

def reset() -> None:
    global _mode
    with _lock:
        _items.clear()
        _mode = current_mode()


def snapshot() -> dict:
    with _lock:
        return {"mode": _mode if _items else current_mode(),
                "items": [_public(i) for i in _items.values()]}


def load_csv(data: bytes) -> dict:
    global _mode
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ServiceError("The file is not UTF-8 text. Save it as CSV (UTF-8) and try again.", 400)
    try:
        rows = read_rows(io.StringIO(text))
    except (ValueError, csv.Error) as e:
        raise ServiceError(f"{e}. The CSV needs the columns id, sender, subject and body "
                           "(email is optional).", 422)
    if not rows:
        raise ServiceError("The CSV has a header but no messages.", 422)
    if len(rows) > MAX_ROWS:
        raise ServiceError(f"The CSV has {len(rows)} messages; the limit is {MAX_ROWS}.", 413)

    grouper, drafter, safety, mode = build_pipeline()
    cands = load_candidates()

    def work(row):
        try:
            return process_row(row, cands, grouper, drafter, safety)
        except Exception as e:  # fail closed: a human looks at anything that broke
            return None, {"reasons": [f"processing error, needs a human ({type(e).__name__})"]}

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        outcomes = list(pool.map(work, rows))
    items = {str(i): _new_item(str(i), row, result, quarantine)
             for i, (row, (result, quarantine)) in enumerate(zip(rows, outcomes))}
    with _lock:
        _items.clear()
        _items.update(items)
        _mode = mode
    return snapshot()


def patch(key: str, draft: str | None, status: str | None) -> dict:
    with _lock:
        item = _get(key)
        if item["status"] == "sent":
            raise ServiceError("This reply was already sent and can't be changed.")
        if draft is not None:
            if len(draft) > MAX_DRAFT_CHARS:
                raise ServiceError(f"Replies are limited to {MAX_DRAFT_CHARS} characters.", 422)
            if draft != item["draft"]:
                item["draft"] = draft
                if item["status"] == "approved":  # an edit cancels the approval
                    item["status"] = "pending"
        if status is not None:
            if status == "approved":
                _check_sendable(item)
            item["status"] = status
        return _public(item)


def deliver(item: dict, sent_at: str) -> None:
    """Stub delivery: records the reply in outbox/sent.csv. No email leaves
    this machine. Replace the body of this function to send through SMTP,
    Gmail, or another service."""
    try:
        OUTBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
        is_new = not OUTBOX_PATH.exists()
        with open(OUTBOX_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(["sent_at", "id", "sender", "email", "subject", "reply"])
            w.writerow([sent_at, _cell(item["id"]), _cell(item["sender"]), _cell(item["email"]),
                        _cell(item["subject"]), _cell(item["draft"])])
    except OSError as e:
        raise ServiceError(f"Could not write the outbox file: {e}", 500)


def send(key: str) -> dict:
    with _lock:
        item = _get(key)
        if item["status"] == "sent":
            raise ServiceError("This reply was already sent.")
        if item["status"] != "approved":
            raise ServiceError("Approve the reply before sending it.")
        _check_sendable(item)
        sent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        deliver(item, sent_at)  # raises before the status changes if it fails
        item["status"] = "sent"
        item["sent_at"] = sent_at
        return _public(item)


def export_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "sender", "email", "subject", "intent", "reply", "status", "sent_at"])
    with _lock:
        for item in _items.values():
            if item["status"] in ("approved", "sent"):
                w.writerow([_cell(item["id"]), _cell(item["sender"]), _cell(item["email"]),
                            _cell(item["subject"]),
                            ";".join(item["labels"]) or "needs a human",
                            _cell(item["draft"]), item["status"], item["sent_at"] or ""])
    return buf.getvalue()
