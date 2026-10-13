import json

from src.harness.decide import DecideProvider


def test_build_request_encodes_pipeline_state_as_json_text():
    state = {
        "sender": {"name": "Sofia Reyes", "stage": "Quest"},
        "message": {"subject": "Status", "body": "Any update?"},
    }

    request = DecideProvider(api_key="test-key").build_request(state, {})

    assert request["state"] == json.dumps(state, ensure_ascii=False)
    assert isinstance(request["state"], str)
    assert json.loads(request["state"]) == state


def test_build_request_accepts_string_state():
    request = DecideProvider(api_key="test-key").build_request("candidate asks for status", {})

    assert request["state"] == "candidate asks for status"


def test_build_request_rejects_unsupported_state_type():
    try:
        DecideProvider(api_key="test-key").build_request([], {})
    except TypeError as error:
        assert "must be a string or dictionary" in str(error)
    else:
        assert False, "unsupported state type should raise TypeError"
