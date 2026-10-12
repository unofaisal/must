from datetime import date
import pytest
from src.stall_alerter import load_stalls, action_for

CSV = "data/hiring_board.csv"
TODAY = date(2026, 10, 12)

def test_flags_and_sorts():
    stalls, total = load_stalls(CSV, 7, TODAY)
    assert total == 12
    assert len(stalls) == 8  # check sample data
    days = [s.days_stalled for s in stalls]
    assert days == sorted(days, reverse=True)
    assert stalls[0].candidate_id == "112"  # oldest: 58d

def test_threshold_filters():
    stalls7, _ = load_stalls(CSV, 7, TODAY)
    stalls14, _ = load_stalls(CSV, 14, TODAY)
    assert len(stalls14) < len(stalls7)

def test_action_map():
    assert action_for("Quest") == "Nudge submission or mark dropped"
    assert action_for("offer") == "Follow up daily until signed"
    assert action_for("weird") == "Review manually"

def test_reason_one_sentence():
    stalls, _ = load_stalls(CSV, 7, TODAY)
    for s in stalls:
        assert s.reason.count(".") == 1, s.reason

def test_missing_column(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("candidate_id,name\n1,A\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_stalls(str(p), 7, TODAY)

def test_bad_date(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("candidate_id,name,stage,last_moved_date,owner,role\n1,A,Screen,not-a-date,O,R\n")
    with pytest.raises(ValueError, match="bad date"):
        load_stalls(str(p), 7, TODAY)

def test_future_date_is_zero(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text("candidate_id,name,stage,last_moved_date,owner,role\n1,A,Screen,2026-10-20,O,R\n")
    stalls, _ = load_stalls(str(p), 7, TODAY)
    assert stalls == []
