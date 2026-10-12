from src.inbox_helper import classify, process

def test_each_intent():
    assert classify("Quest deadline", "when submit?")[0] == "quest_status"
    assert classify("Interview slot", "schedule a call, available")[0] == "schedule"
    assert classify("Salary", "what compensation ctc?")[0] == "salary"
    assert classify("Upload error", "cannot upload, failed")[0] == "technical_issue"
    assert classify("Bye", "withdraw, not interested")[0] == "withdrawal"
    assert classify("Hello", "just saying hi")[0] == "other"

def test_confidence():
    assert classify("Quest deadline submit upload", "quest submit")[1] == "high"
    assert classify("Hello", "just hi")[1] == "low"

def test_process_counts():
    res = process("data/messages.csv")
    assert len(res) == 12
    intents = {r.intent for r in res}
    assert {"quest_status", "schedule", "salary", "technical_issue", "withdrawal", "other"} <= intents

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
