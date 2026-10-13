import json

import pytest

from src.harness.chat import ChatProvider
from src import inbox_helper


class FakeResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.body


def test_chat_provider_reports_embedded_provider_error(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse({
            "id": "gen-test",
            "error": {
                "message": "JSON error injected into SSE stream",
                "code": 502,
                "metadata": {"error_type": "provider_unavailable"},
            },
        })

    monkeypatch.setattr("src.harness.chat.urllib.request.urlopen", fake_urlopen)
    provider = ChatProvider(api_key="test-key")

    with pytest.raises(RuntimeError) as exc_info:
        provider.complete("hello")

    assert "502, provider_unavailable" in str(exc_info.value)
    assert "JSON error injected into SSE stream" in str(exc_info.value)


def test_chat_provider_returns_successful_content(monkeypatch):
    def fake_urlopen(request, timeout):
        return FakeResponse({"choices": [{"message": {"content": "Hello"}}]})

    monkeypatch.setattr("src.harness.chat.urllib.request.urlopen", fake_urlopen)
    provider = ChatProvider(api_key="test-key")

    assert provider.complete("hello") == "Hello"


def test_cli_reports_provider_error_without_traceback(monkeypatch, capsys):
    def fail_pipeline(*args, **kwargs):
        raise RuntimeError(
            "chat provider error (502, provider_unavailable): temporarily unavailable"
        )

    monkeypatch.setattr(inbox_helper, "run_pipeline", fail_pipeline)

    assert inbox_helper.main(["--csv", "messages.csv"]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("error: chat provider error (502, provider_unavailable)")
    assert captured.out == ""
