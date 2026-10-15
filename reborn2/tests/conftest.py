"""Importing api.service restores the open batch at boot, which can rewrite
data/session.json and create data/history/. Put both back after the test run so
running the tests never changes your real work."""
import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
_session = DATA / "session.json"
_before = _session.read_bytes() if _session.is_file() else None
_had_history = (DATA / "history").exists()


def pytest_sessionfinish(session, exitstatus):
    if _before is not None:
        _session.write_bytes(_before)
    if not _had_history:
        shutil.rmtree(DATA / "history", ignore_errors=True)
