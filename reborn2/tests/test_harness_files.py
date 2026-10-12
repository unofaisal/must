from src.harness.files import build_content, file_part
from src.harness.openrouter import OpenRouterProvider
from src.harness import Harness

def test_url_pdf_part():
    p = file_part("https://example.com/document.pdf")
    assert p["type"] == "file" and p["file"]["file_data"].startswith("https://")

def test_url_image_part():
    p = file_part("https://example.com/x.png")
    assert p["type"] == "image_url"

def test_local_text_inline(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hello world")
    p = file_part(str(f))
    assert p["type"] == "text" and "hello world" in p["text"]

def test_local_pdf_base64(tmp_path):
    f = tmp_path / "d.pdf"
    f.write_bytes(b"%PDF-1.4 fake")
    p = file_part(str(f))
    assert p["type"] == "file" and p["file"]["file_data"].startswith("data:application/pdf;base64,")

def test_build_payload_both_styles(tmp_path):
    f = tmp_path / "n.txt"
    f.write_text("hi")
    prov = OpenRouterProvider(model="openai/gpt-4o-mini", api_key="dummy")
    payload = prov.build_payload("summarize", files=["https://example.com/document.pdf", str(f)])
    content = payload["messages"][0]["content"]
    assert len(content) == 3 and content[0]["type"] == "text"
    assert payload["model"] == "openai/gpt-4o-mini"

def test_harness_passes_files():
    h = Harness()
    r = h.run("quest deadline?", files=["https://example.com/document.pdf"])
    assert r.passed and r.files == ["https://example.com/document.pdf"]
