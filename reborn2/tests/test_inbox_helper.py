from src.inbox_helper import process
from src.grouping import Grouper, OTHER
from src.harness.decide import RuleDecide

SENDER = {"name": "Test User", "stage": "Screen", "role_applied": "Backend"}

def _labels(subject, body):
    return Grouper(RuleDecide()).label({"subject": subject, "body": body}, SENDER).labels

def test_each_intent():
    assert "status_update" in _labels("Status?", "any news on my application status?")
    assert "reschedule" in _labels("Reschedule", "need to reschedule my interview")
    assert "hiring_process" in _labels("Process?", "what are the next steps and timeline?")
    assert "pay_or_contract" in _labels("Salary", "what compensation and contract terms?")
    assert "withdrawal" in _labels("Bye", "please withdraw, not interested")
    assert "feedback" in _labels("Rejected", "please share feedback on my rejection")

def test_multi_label():
    labels = _labels("Reschedule + pay", "move my interview to Monday; also what is the salary band?")
    assert "reschedule" in labels and "pay_or_contract" in labels

def test_other_fallback():
    assert _labels("Hello", "just saying hi, excited!") == [OTHER]

def test_process_counts():
    res = process("data/messages.csv")
    assert len(res) == 42
    intents = {r.intent for r in res}
    assert {"status_update", "reschedule", "hiring_process", "pay_or_contract",
            "withdrawal", "feedback", "other"} <= intents

def test_process_multilabel_present():
    res = {r.id: r for r in process("data/messages.csv")}
    assert len(res["19"].labels) >= 2  # reschedule + pay email

def test_drafts_mention_sender():
    res = process("data/messages.csv")
    for r in res:
        assert r.sender.split()[0] in r.draft

def test_missing_column(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("id,sender\n1,A\n")
    try:
        process(str(p))
        assert False, "should raise"
    except ValueError as e:
        assert "missing columns" in str(e)
