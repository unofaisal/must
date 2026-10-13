import csv

def _load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def test_every_message_email_has_candidate():
    cands = _load("data/candidates.csv")
    by_email = {c["email"]: c for c in cands}
    msgs = _load("data/messages.csv")
    assert len(cands) == 30 and len(msgs) == 42
    orphans = [m["id"] for m in msgs if m["email"] not in by_email]
    assert orphans == []

def test_sender_names_match_candidate_names():
    by_email = {c["email"]: c["name"] for c in _load("data/candidates.csv")}
    for m in _load("data/messages.csv"):
        assert m["sender"] == by_email[m["email"]], m["id"]

def test_candidate_schema():
    want = ["candidate_id", "name", "email", "role_applied", "stage",
            "last_stage_change", "interview_date", "interview_time", "recruiter"]
    with open("data/candidates.csv", encoding="utf-8") as f:
        assert csv.DictReader(f).fieldnames == want
