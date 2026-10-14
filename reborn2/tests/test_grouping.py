from src.grouping import Grouper, GROUP_THRESHOLD, OTHER, INTENTS, GROUP_SPECS


class StubDecide:
    name = "stub"

    def __init__(self, probs=None, fail=False):
        self.probs = probs or {}
        self.fail = fail
        self.seen = []

    def ask(self, state, questions):
        if self.fail:
            raise RuntimeError("boom")
        self.seen.append((state, questions))
        return {qid: {"type": "noul", "noul": self.probs.get(qid, 0.01)}
                for qid in questions}


MSG = {"subject": "Update?", "body": "Any news?"}
SENDER = {"name": "Amina Yusuf", "email": "a@x.com", "stage": "Quest",
          "role_applied": "Backend"}


def test_multi_label_fires_each():
    g = Grouper(StubDecide({"status_update": 0.9, "pay_or_contract": 0.75}))
    r = g.label(MSG, SENDER)
    assert r.labels == ["status_update", "pay_or_contract"]
    assert r.primary == "status_update"


def test_other_when_nothing_fires():
    r = Grouper(StubDecide()).label(MSG, SENDER)
    assert r.labels == [OTHER] and r.scores[OTHER] == 1.0


def test_boundary_at_threshold():
    g = Grouper(StubDecide({"feedback": GROUP_THRESHOLD}))
    assert g.label(MSG, SENDER).labels == ["feedback"]
    g2 = Grouper(StubDecide({"feedback": GROUP_THRESHOLD - 0.01}))
    assert g2.label(MSG, SENDER).labels == [OTHER]


def test_provider_error_uses_rule_fallback():
    g = Grouper(StubDecide(fail=True))
    r = g.label({"subject": "Bye", "body": "please withdraw me"}, SENDER)
    assert r.labels == ["withdrawal"] and r.provider == "stub"


def test_malformed_answer_counts_as_no_signal():
    class Weird:
        name = "weird"
        def ask(self, state, questions):
            return {"status_update": {"type": "choice", "choice": "x"}}
    assert Grouper(Weird()).label(MSG, SENDER).labels == [OTHER]


def test_state_carries_sender_record():
    stub = StubDecide()
    Grouper(stub).label(MSG, SENDER)
    state = stub.seen[0][0]
    assert state["sender"]["stage"] == "Quest"
    assert state["message"]["subject"] == "Update?"
    assert set(stub.seen[0][1]) == set(GROUP_SPECS)


def test_rule_fallback_end_to_end():
    from src.harness.decide import RuleDecide
    g = Grouper(RuleDecide())
    assert "withdrawal" in g.label({"subject": "x", "body": "I quit, withdraw me"}, SENDER).labels
    assert g.label({"subject": "hi", "body": "just saying hello"}, SENDER).labels == [OTHER]


def test_new_groups_can_fire_and_are_sorted_by_score():
    g = Grouper(StubDecide({"technical_issue": 0.9, "deadline_extension": 0.7,
                            "thanks_or_ack": 0.6, "other": 0.99}))
    r = g.label(MSG, SENDER)
    assert r.labels == ["technical_issue", "deadline_extension", "thanks_or_ack"]
    assert r.primary == "technical_issue"
    assert set(INTENTS) | {OTHER} == set(GROUP_SPECS)  # every question asked is also read


def test_offline_rules_cover_technical_and_extension():
    from src.harness.decide import RuleDecide
    g = Grouper(RuleDecide())
    assert g.label({"subject": "x", "body": "login failed, cannot access quest page"}, SENDER).primary == "technical_issue"
    assert "deadline_extension" in g.label({"subject": "x", "body": "could I get an extension?"}, SENDER).labels
