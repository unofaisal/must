"""Review-session logic behind the web page.

One in-memory session for one user: upload a CSV, the pipeline runs in the
background (the page watches it stage by stage), and the human then edits,
approves, rejects, and sends each reply.

Settings (API key, models, custom prompt) live in data/settings.json.
The current batch is persisted to data/session.json once the run finishes
and after every draft/status change, so a page refresh or server restart
restores the review workspace. Every finished batch is also kept as its own
JSON file in data/history/ (no database), so past work can be reopened from
the page. Sent replies are also kept in outbox/sent.csv.
"""
from __future__ import annotations

import copy
import csv
import io
import json
import os
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import gmail
from src.drafting import Drafter, find_placeholders
from src.grouping import Grouper
from src.inbox_helper import load_candidates, process_row, read_rows
from src.safety import SafetyGate

ROOT = Path(__file__).resolve().parent.parent
OUTBOX_PATH = ROOT / "outbox" / "sent.csv"
SAMPLE_PATH = ROOT / "data" / "messages.csv"
SETTINGS_PATH = ROOT / "data" / "settings.json"
SESSION_PATH = ROOT / "data" / "session.json"
HISTORY_DIR = ROOT / "data" / "history"
MAX_HISTORY = 50
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_BYTES = 1_000_000
MAX_ROWS = 500
MAX_DRAFT_CHARS = 5000

DEFAULT_SETTINGS = {
    "api_key": "",
    "chat_model": "nvidia/nemotron-3.5-lightning:free",
    "decide_model": "respan/span-01-lite",
    "custom_prompt": "",
}

_lock = threading.RLock()
_items: dict[str, dict] = {}
_mode = "offline"
_batch = {"id": "", "name": "", "created": ""}  # which batch is open
_run = {"state": "idle", "started": None, "finished": None, "delay_ms": 0}
_settings: dict = dict(DEFAULT_SETTINGS)
STAGES = ("safety", "grouping", "drafting")

# Live-model failures for the current run: how many, and the latest message.
_health: dict[str, dict] = {}


def _reset_health() -> None:
    _health.clear()
    _health.update({"chat": {"errors": 0, "last": ""}, "decide": {"errors": 0, "last": ""}})


_reset_health()


def _err(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"[:300]


def _workers() -> int:
    """Messages processed in parallel. Lower it (PIPELINE_WORKERS=1) if the
    provider rate-limits you."""
    try:
        return max(1, int(os.getenv("PIPELINE_WORKERS", "4")))
    except ValueError:
        return 4


class ServiceError(Exception):
    """An error the page can show to the user as-is."""

    def __init__(self, detail: str, status_code: int = 409):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


# --- settings ---------------------------------------------------------------

def _load_settings() -> None:
    global _settings
    try:
        if SETTINGS_PATH.is_file():
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = dict(DEFAULT_SETTINGS)
                for k in DEFAULT_SETTINGS:
                    if k in data and isinstance(data[k], str):
                        merged[k] = data[k]
                _settings = merged
                return
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    _settings = dict(DEFAULT_SETTINGS)


def _save_settings() -> None:
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(
            json.dumps(_settings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as e:
        raise ServiceError(f"Could not save settings: {e}", 500)


def get_settings() -> dict:
    """Public settings (API key is never returned in full)."""
    with _lock:
        key = _settings.get("api_key", "")
        return {
            "api_key_set": bool(key.strip()),
            "api_key_hint": f"••••{key[-4:]}" if len(key.strip()) >= 8 else ("set" if key.strip() else ""),
            "chat_model": _settings["chat_model"],
            "decide_model": _settings["decide_model"],
            "custom_prompt": _settings["custom_prompt"],
            "mode": "live" if key.strip() else "offline",
        }


def update_settings(
    api_key: str | None = None,
    chat_model: str | None = None,
    decide_model: str | None = None,
    custom_prompt: str | None = None,
) -> dict:
    with _lock:
        if api_key is not None:
            _settings["api_key"] = api_key.strip()
        if chat_model is not None:
            _settings["chat_model"] = chat_model.strip() or DEFAULT_SETTINGS["chat_model"]
        if decide_model is not None:
            _settings["decide_model"] = decide_model.strip() or DEFAULT_SETTINGS["decide_model"]
        if custom_prompt is not None:
            _settings["custom_prompt"] = custom_prompt
        _save_settings()
        return get_settings()


def _effective_key() -> str:
    """Settings file first, then environment variable."""
    with _lock:
        key = (_settings.get("api_key") or "").strip()
    if key:
        return key
    return os.getenv("OPENROUTER_API_KEY", "").strip()


# --- session persistence ----------------------------------------------------

def _session_payload() -> dict:
    """Minimal durable snapshot: drafts, statuses, and fields needed for review."""
    items = []
    for item in _items.values():
        items.append({
            "key": item["key"],
            "id": item["id"],
            "sender": item["sender"],
            "email": item["email"],
            "subject": item["subject"],
            "body": item["body"],
            "source": item.get("source", "csv"),
            "thread_id": item.get("thread_id", ""),
            "message_id": item.get("message_id", ""),
            "status": item["status"],
            "sent_at": item["sent_at"],
            "kind": item["kind"],
            "labels": item["labels"],
            "primary": item["primary"],
            "confidence": item["confidence"],
            "draft": item["draft"],
            "draft_source": item["draft_source"],
            "reasons": item["reasons"],
            "processing": item["processing"],
            "stages": item["stages"],
        })
    return {
        "mode": _mode,
        "batch": dict(_batch),
        "run": {
            "state": _run["state"],
            "started": _run["started"],
            "finished": _run["finished"],
            "delay_ms": _run.get("delay_ms", 0),
        },
        "items": items,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _prune_history() -> None:
    """Keep the newest MAX_HISTORY batches; never drop the open one."""
    files = sorted(HISTORY_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[MAX_HISTORY:]:
        if old.stem != _batch["id"]:
            old.unlink(missing_ok=True)


def _save_session() -> None:
    """Write the current batch so a refresh or restart can restore it, and
    keep a copy in data/history/ so it can be reopened later.
    Only persists when the run is finished (or idle with items)."""
    if not _items:
        try:
            if SESSION_PATH.is_file():
                SESSION_PATH.unlink()
        except OSError:
            pass
        return
    if _run["state"] == "running":
        return  # don't snapshot a half-finished pipeline
    try:
        text = json.dumps(_session_payload(), ensure_ascii=False) + "\n"
        _atomic_write(SESSION_PATH, text)
        if _batch["id"]:
            _atomic_write(HISTORY_DIR / f"{_batch['id']}.json", text)
            _prune_history()
    except OSError:
        pass  # persistence is best-effort; never break the request path


def _new_batch(name: str) -> None:
    now = datetime.now(timezone.utc)
    _batch.update(id=f"{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
                  name=(name or "Uploaded batch").strip()[:80],
                  created=now.isoformat(timespec="seconds"))


def _load_payload(data: dict, batch_id: str = "") -> bool:
    """Replace the open batch with a saved one. Returns False if it is unusable."""
    global _mode
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return False
    items = {}
    for raw in data["items"]:
        if not isinstance(raw, dict) or "key" not in raw:
            continue
        key = str(raw["key"])
        item = _new_item(key, {
            "id": raw.get("id", ""),
            "sender": raw.get("sender", ""),
            "email": raw.get("email", ""),
            "subject": raw.get("subject", ""),
            "body": raw.get("body", ""),
        })
        for field in ("source", "thread_id", "message_id",
                      "status", "sent_at", "kind", "labels", "primary",
                      "confidence", "draft", "draft_source", "reasons", "processing"):
            if field in raw:
                item[field] = raw[field]
        if isinstance(raw.get("stages"), dict):
            item["stages"] = raw["stages"]
        items[key] = item
    if not items:
        return False
    run = data.get("run") or {}
    saved = data.get("batch") if isinstance(data.get("batch"), dict) else {}
    with _lock:
        _items.clear()
        _items.update(items)
        _mode = data.get("mode") or current_mode()
        _run.update(
            state=run.get("state") or "done",
            started=run.get("started"),
            finished=run.get("finished") or time.time(),
            delay_ms=run.get("delay_ms") or 0,
        )
        _reset_health()
        if batch_id or saved.get("id"):
            _batch.update(id=batch_id or str(saved["id"]),
                          name=str(saved.get("name") or "Earlier batch"),
                          created=str(saved.get("created") or data.get("saved_at") or ""))
        else:  # a session saved before history existed
            _new_batch("Earlier batch")
            _batch["created"] = str(data.get("saved_at") or _batch["created"])
    return True


def _restore_session() -> None:
    """Load the last finished batch if present."""
    try:
        if not SESSION_PATH.is_file():
            return
        data = json.loads(SESSION_PATH.read_text(encoding="utf-8"))
        if _load_payload(data):
            _save_session()  # makes sure the batch has a history file
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        pass


# --- providers --------------------------------------------------------------

def current_mode() -> str:
    return "live" if _effective_key() else "offline"


class _Recorder:
    """Wraps a live provider so every failure is counted and the latest message
    kept, then re-raises it. The pipeline's own fallbacks (keyword rules,
    templates) still run exactly as before. This only makes failures visible."""

    def __init__(self, inner, kind: str):
        self._inner = inner
        self._kind = kind
        self.name = getattr(inner, "name", kind)

    def __getattr__(self, attr):  # model, api_key, ...
        return getattr(self._inner, attr)

    def _fail(self, message: str) -> None:
        with _lock:
            _health[self._kind]["errors"] += 1
            _health[self._kind]["last"] = message

    def ask(self, state, questions):
        try:
            return self._inner.ask(state, questions)
        except Exception as e:
            self._fail(_err(e))
            raise

    def complete(self, prompt):
        try:
            reply = self._inner.complete(prompt)
        except Exception as e:
            self._fail(_err(e))
            raise
        if not (reply or "").strip():
            self._fail("The model returned an empty reply.")
        return reply


def build_pipeline():
    """Pick the models for a run from saved settings (or env fallback)."""
    key = _effective_key()
    if key:
        from src.harness.chat import ChatProvider
        from src.harness.decide import DecideProvider
        with _lock:
            chat_model = _settings["chat_model"]
            decide_model = _settings["decide_model"]
            custom_prompt = _settings["custom_prompt"]
        decide = _Recorder(DecideProvider(model=decide_model, api_key=key), "decide")
        chat = _Recorder(ChatProvider(model=chat_model, api_key=key), "chat")
        return Grouper(decide), Drafter(chat, custom_prompt=custom_prompt), SafetyGate(decide), "live"
    return Grouper(), Drafter(), SafetyGate(), "offline"


def check_providers() -> dict:
    """One tiny call to each live model, so a bad key or model name shows up
    with the provider's own error message. Never returns the key itself."""
    key = _effective_key()
    out = {"key_present": bool(key), "key_hint": "", "models": None, "chat": None, "decide": None}
    if not key:
        return out
    out["key_hint"] = f"ends in {key[-4:]}" if len(key) >= 8 else "set, but very short"
    from src.harness.chat import ChatProvider
    from src.harness.decide import DecideProvider
    with _lock:
        chat_model = _settings["chat_model"]
        decide_model = _settings["decide_model"]
    chat = ChatProvider(model=chat_model, api_key=key)
    decide = DecideProvider(model=decide_model, api_key=key)
    out["models"] = {"chat": chat.model, "decide": decide.model}
    spec = {"asks_status": ("Is the sender asking for a status update?",
                            "Asks for a status update.", "Does not ask for one.")}
    for kind, call in (
        ("chat", lambda: chat.complete("Reply with the single word: ok")[:80]),
        ("decide", lambda: decide.ask_nouls("Any update on my application?", spec)),
    ):
        started = time.perf_counter()
        try:
            result = call()
            out[kind] = {"ok": True, "ms": round((time.perf_counter() - started) * 1000),
                         "result": result}
        except Exception as e:
            out[kind] = {"ok": False, "error": _err(e)}
    return out


# --- helpers ----------------------------------------------------------------

def _cell(value) -> str:
    """Stop spreadsheet apps from running an email's text as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _public(item: dict) -> dict:
    return {**copy.deepcopy(item), "placeholders": find_placeholders(item["draft"])}


def _get(key: str) -> dict:
    item = _items.get(key)
    if item is None:
        raise ServiceError("That message is not in the current batch.", 404)
    return item


def _check_ready(item: dict) -> None:
    if item["processing"] != "done":
        raise ServiceError("This message is still being processed.")


def _check_sendable(item: dict) -> None:
    if not item["draft"].strip():
        raise ServiceError("Write a reply before approving.")
    missing = find_placeholders(item["draft"])
    if missing:
        raise ServiceError("Fill in " + ", ".join(f"[{p}]" for p in missing)
                           + " before approving.")


def _new_item(key: str, row: dict) -> dict:
    return {"key": key, "id": row.get("id") or "", "sender": row.get("sender") or "",
            "email": row.get("email") or "", "subject": row.get("subject") or "",
            "body": row.get("body") or "", "status": "pending", "sent_at": None,
            "source": "csv", "thread_id": "", "message_id": "",  # gmail items fill these in
            "kind": "draft", "labels": [], "primary": "", "confidence": "",
            "draft": "", "draft_source": "", "reasons": [],
            "processing": "queued",  # queued -> running -> done
            "stages": {st: {"state": "waiting", "detail": {}, "ms": None} for st in STAGES}}


def _fill(item: dict, result, quarantine) -> None:
    """Store a finished message's outcome on its item."""
    if quarantine:
        item.update(kind="quarantined", reasons=quarantine["reasons"])
        if item["stages"]["safety"]["state"] != "done":  # it broke before the gate answered
            item["stages"]["safety"].update(state="done", detail={
                "flagged": True, "flags": {}, "reasons": quarantine["reasons"], "error": True})
        for st in ("grouping", "drafting"):
            if item["stages"][st]["state"] in ("waiting", "running"):
                item["stages"][st]["state"] = "skipped"
    else:
        item.update(kind="draft", labels=result.labels, primary=result.intent,
                    confidence=result.confidence, draft=result.draft,
                    draft_source=result.draft_source)
    item["processing"] = "done"


def demo_delay_ms() -> int:
    """Optional pause before every stage, for recording a demo. Offline runs
    finish in milliseconds, so the live pipeline view would flash past
    otherwise. Set DEMO_DELAY_MS=400 to slow it down. Default: no delay."""
    try:
        return max(0, int(os.getenv("DEMO_DELAY_MS", "0")))
    except ValueError:
        return 0


def _run_info() -> dict:
    started, finished = _run["started"], _run["finished"]
    elapsed = 0.0 if started is None else (finished or time.time()) - started
    return {"state": _run["state"], "total": len(_items), "elapsed": round(elapsed, 1),
            "done": sum(1 for i in _items.values() if i["processing"] == "done"),
            "demo_delay_ms": _run.get("delay_ms", 0),
            "provider_errors": copy.deepcopy(_health)}


# --- session ----------------------------------------------------------------

def reset() -> None:
    global _mode
    with _lock:
        _items.clear()
        _batch.update(id="", name="", created="")
        _mode = current_mode()
        _run.update(state="idle", started=None, finished=None, delay_ms=0)
        _reset_health()
        _save_session()


def snapshot() -> dict:
    with _lock:
        return {"mode": _mode if _items else current_mode(), "run": _run_info(),
                "batch": dict(_batch) if _items else None,
                "items": [_public(i) for i in _items.values()]}


def _run_job(rows, cands, grouper, drafter, safety, delay: float = 0.0) -> None:
    """Background run: every message goes through the pipeline, a few at a time,
    and each stage reports into its item as it happens."""

    def work(args):
        key, row = args
        started: dict[str, float] = {}

        def on_stage(stage, state, detail):
            now = time.perf_counter()
            with _lock:
                item = _items.get(key)
                if item is None:
                    return
                st = item["stages"][stage]
                if state == "running":
                    started[stage] = now
                    item["processing"] = "running"
                if state == "done":
                    st["ms"] = round((now - started.get(stage, now)) * 1000)
                    st["detail"] = detail
                    if stage == "safety" and detail.get("flagged"):
                        item["kind"] = "quarantined"
                st["state"] = state
            if state == "running" and delay:
                time.sleep(delay)  # demo pacing only; 0 by default

        try:
            result, quarantine = process_row(row, cands, grouper, drafter, safety,
                                             on_stage=on_stage)
        except Exception as e:  # fail closed: a human looks at anything that broke
            result, quarantine = None, {"reasons": [
                f"processing error, needs a human ({type(e).__name__})"]}
        with _lock:
            item = _items.get(key)
            if item is not None:
                _fill(item, result, quarantine)

    try:
        with ThreadPoolExecutor(max_workers=_workers()) as pool:
            list(pool.map(work, [(str(i), row) for i, row in enumerate(rows)]))
    finally:
        with _lock:
            _run.update(state="done", finished=time.time())
            _save_session()


def start_csv(data: bytes, name: str = "") -> dict:
    """Validate the CSV, then start the pipeline in the background and return
    straight away. The page polls snapshot() to watch it run."""
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

    return _start_rows(rows, name, source="csv")


def _start_rows(rows: list[dict], name: str, source: str) -> dict:
    """Start the pipeline on already-validated rows. `source` is "csv" or "gmail"."""
    global _mode
    grouper, drafter, safety, mode = build_pipeline()
    cands = load_candidates()
    with _lock:
        if _run["state"] == "running":
            raise ServiceError("A batch is still running. Wait for it to finish.")
        _items.clear()
        _items.update({str(i): _new_item(str(i), row) for i, row in enumerate(rows)})
        if source == "gmail":
            # Only rows that came from our own Gmail fetch may carry Gmail ids.
            # A CSV can't claim them, so an upload can never trigger a Gmail send.
            for i, row in enumerate(rows):
                _items[str(i)].update(source="gmail", thread_id=row.get("thread_id", ""),
                                      message_id=row.get("message_id", ""))
        _new_batch(name)
        _mode = mode
        delay_ms = demo_delay_ms()
        _reset_health()
        _run.update(state="running", started=time.time(), finished=None, delay_ms=delay_ms)
    threading.Thread(target=_run_job, args=(rows, cands, grouper, drafter, safety, delay_ms / 1000),
                     daemon=True).start()
    return snapshot()


def start_gmail(keywords: str, after: str, before: str, limit: int) -> dict:
    """Pull matching emails from Gmail (through the MCP connector) and run them like a CSV."""
    with _lock:
        if _run["state"] == "running":
            raise ServiceError("A batch is still running. Wait for it to finish.")
    try:
        rows = gmail.fetch_messages(keywords, after, before, limit)
    except gmail.GmailError as e:
        raise ServiceError(e.detail, e.status_code)
    if not rows:
        raise ServiceError("No emails in the inbox matched those keywords and dates.", 404)
    label = keywords.strip() or "inbox"
    return _start_rows(rows[:MAX_ROWS], f"Gmail: {label}", source="gmail")


def start_sample() -> dict:
    try:
        data = SAMPLE_PATH.read_bytes()
    except FileNotFoundError:
        raise ServiceError("The sample file data/messages.csv was not found.", 404)
    return start_csv(data, "Sample inbox")


def patch(key: str, draft: str | None, status: str | None) -> dict:
    with _lock:
        item = _get(key)
        _check_ready(item)
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
        _save_session()
        return _public(item)


def _record_outbox(item: dict, sent_at: str) -> None:
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


def deliver(item: dict, sent_at: str) -> None:
    """Gmail messages are answered through the Gmail connector, in their thread.
    Everything else (CSV batches) is only recorded in outbox/sent.csv; no email
    leaves this machine for those. Every send is also logged to outbox/sent.csv."""
    if item.get("source") == "gmail":
        try:
            gmail.send_reply(item.get("message_id", ""), item.get("thread_id", ""),
                             item["draft"], item.get("email", ""), item.get("subject", ""))
        except gmail.GmailError as e:
            raise ServiceError(e.detail, e.status_code)
        try:  # the email is already out; a logging problem must not make it look unsent
            _record_outbox(item, sent_at)
        except ServiceError:
            pass
        return
    _record_outbox(item, sent_at)


def send(key: str) -> dict:
    with _lock:
        item = _get(key)
        _check_ready(item)
        if item["status"] == "sent":
            raise ServiceError("This reply was already sent.")
        if item["status"] != "approved":
            raise ServiceError("Approve the reply before sending it.")
        _check_sendable(item)
        sent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        deliver(item, sent_at)  # raises before the status changes if it fails
        item["status"] = "sent"
        item["sent_at"] = sent_at
        _save_session()
        return _public(item)


# --- past work --------------------------------------------------------------

def list_history() -> list[dict]:
    """One summary per saved batch, newest first."""
    out = []
    try:
        files = list(HISTORY_DIR.glob("*.json"))
    except OSError:
        return out
    with _lock:
        open_id = _batch["id"] if _items else ""
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items = [i for i in data.get("items", []) if isinstance(i, dict)]
        except (OSError, json.JSONDecodeError, AttributeError):
            continue
        meta = data.get("batch") if isinstance(data.get("batch"), dict) else {}
        counts = {"pending": 0, "approved": 0, "rejected": 0, "sent": 0}
        for i in items:
            st = i.get("status", "pending")
            counts[st] = counts.get(st, 0) + 1
        out.append({
            "id": path.stem,
            "name": meta.get("name") or "Earlier batch",
            "created": meta.get("created") or data.get("saved_at") or "",
            "saved_at": data.get("saved_at") or "",
            "total": len(items),
            "quarantined": sum(1 for i in items if i.get("kind") == "quarantined"),
            "counts": counts,
            "open": path.stem == open_id,
        })
    out.sort(key=lambda e: e["created"], reverse=True)
    return out


def _history_path(batch_id: str) -> Path:
    if not _ID_RE.match(batch_id):
        raise ServiceError("That batch was not found.", 404)
    return HISTORY_DIR / f"{batch_id}.json"


def open_batch(batch_id: str) -> dict:
    """Make a saved batch the open one so it can be reviewed again."""
    path = _history_path(batch_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ServiceError("That batch was not found.", 404)
    with _lock:
        if _run["state"] == "running":
            raise ServiceError("A batch is still running. Wait for it to finish.")
        if not _load_payload(data, batch_id):
            raise ServiceError("That saved batch could not be read.", 422)
        _save_session()
    return snapshot()


def delete_batch(batch_id: str) -> dict:
    """Remove a saved batch. If it is the open one, the workspace is cleared."""
    path = _history_path(batch_id)
    with _lock:
        if _run["state"] == "running" and _batch["id"] == batch_id:
            raise ServiceError("A batch is still running. Wait for it to finish.")
        try:
            path.unlink(missing_ok=True)
        except OSError:
            raise ServiceError("Could not delete that batch.", 500)
        if _batch["id"] == batch_id:
            reset()
    return snapshot()


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


# Boot: load settings and restore the last finished batch if any.
_load_settings()
_restore_session()