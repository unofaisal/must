from src.drafting import Drafter, build_prompt, find_placeholders, DRAFTS
from src.harness.chat import ChatProvider, DEFAULT_MODEL


class StubChat:
    name = "stub-chat"

    def __init__(self, text):
        self.text = text
        self.seen = []

    def complete(self, prompt):
        self.seen.append(prompt)
        return self.text


MSG = {"subject": "Reschedule?", "body": "Can we move Friday's call to Monday?"}
SENDER = {"name": "Linh Nguyen", "email": "l@x.com", "stage": "HR",
          "role_applied": "Backend"}


def test_prompt_has_email_group_sender_and_placeholder_line():
    p = build_prompt(MSG, ["reschedule"], SENDER)
    assert "Can we move Friday's call" in p
    assert "reschedule" in p
    assert "Linh Nguyen" in p and "HR" in p and "Backend" in p
    assert 'write "[place_holder_text eg date]"' in p
    assert "Never assert a fact you were not given" in p


def test_live_path_returns_text_and_placeholders():
    d = Drafter(StubChat("Hi Linh, how about [Monday 10am]? Pay is [salary band]."))
    r = d.draft(MSG, ["reschedule"], SENDER)
    assert r.provider == "stub-chat"
    assert r.placeholders == ["Monday 10am", "salary band"]


def test_find_placeholders():
    assert find_placeholders("no brackets here") == []
    assert find_placeholders("on [date] at [time]") == ["date", "time"]


def test_template_fallback_per_label():
    for label in ("status_update", "reschedule", "hiring_process",
                  "pay_or_contract", "withdrawal", "feedback", "other"):
        r = Drafter().draft(MSG, [label], SENDER)
        assert r.draft == DRAFTS[label].format(sender="Linh Nguyen")
        assert r.placeholders == [] and r.provider == "template"


def test_chat_payload_shape():
    prov = ChatProvider(model="x/y", api_key="dummy")
    payload = prov.build_payload("hello")
    assert payload == {"model": "x/y", "messages": [{"role": "user", "content": "hello"}], "reasoning": {"enabled": False}}
    assert DEFAULT_MODEL == "nvidia/nemotron-3.5-lightning:free"


def test_new_groups_have_templates():
    for label in ("technical_issue", "deadline_extension",
                  "submission_or_documents", "thanks_or_ack"):
        assert label in DRAFTS
        assert "Linh Nguyen" in Drafter().draft(MSG, [label], SENDER).draft


def test_provider_failure_falls_back_to_template():
    class Boom:
        name = "boom"
        def complete(self, prompt):
            raise RuntimeError("503")
    r = Drafter(Boom()).draft(MSG, ["reschedule"], SENDER)
    assert r.provider == "template (fallback)" and "Linh Nguyen" in r.draft
    assert Drafter(StubChat("   ")).draft(MSG, ["reschedule"], SENDER).provider == "template (fallback)"
