"""FastAPI app for the inbox helper review page.

Run from the project root:   uvicorn api.main:app --reload
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import gmail, service
from .gmail import GmailError
from .service import ServiceError

app = FastAPI(title="Inbox helper")


@app.exception_handler(ServiceError)
def service_error(_, exc: ServiceError):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(GmailError)
def gmail_error(_, exc: GmailError):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


class GmailConfigBody(BaseModel):
    client_id: str | None = Field(default=None, max_length=300)
    client_secret: str | None = Field(default=None, max_length=300)
    mcp_url: str | None = Field(default=None, max_length=300)
    scopes: str | None = Field(default=None, max_length=1000)
    redirect_uri: str | None = Field(default=None, max_length=300)


class GmailFetchBody(BaseModel):
    keywords: str = Field(default="", max_length=300)
    after: str = Field(default="", max_length=10)
    before: str = Field(default="", max_length=10)
    limit: int = Field(default=25, ge=1, le=gmail.MAX_FETCH)


class PatchBody(BaseModel):
    draft: str | None = Field(default=None, max_length=service.MAX_DRAFT_CHARS)
    status: Literal["pending", "approved", "rejected"] | None = None


class SettingsBody(BaseModel):
    api_key: str | None = Field(default=None, max_length=500)
    chat_model: str | None = Field(default=None, max_length=200)
    decide_model: str | None = Field(default=None, max_length=200)
    custom_prompt: str | None = Field(default=None, max_length=4000)


@app.get("/api/items")
def list_items():
    return service.snapshot()


@app.get("/api/settings")
def get_settings():
    return service.get_settings()


@app.put("/api/settings")
def put_settings(body: SettingsBody):
    return service.update_settings(
        api_key=body.api_key,
        chat_model=body.chat_model,
        decide_model=body.decide_model,
        custom_prompt=body.custom_prompt,
    )


@app.get("/api/check")
def check():
    """Tests the OpenRouter key and both models with one small call each."""
    return service.check_providers()


# --- Gmail connector (Google sign-in + Google's Gmail MCP server) -----------------

@app.get("/api/gmail")
def gmail_status():
    return gmail.status()


@app.put("/api/gmail/config")
def gmail_config(body: GmailConfigBody):
    return gmail.update_config(body.model_dump())


@app.get("/api/gmail/authorize")
def gmail_authorize(request: Request, return_to: str = ""):
    """The Connect Gmail button lands here and is sent on to Google's Allow screen."""
    origin = return_to or request.headers.get("origin") or request.headers.get("referer") or ""
    return RedirectResponse(gmail.authorize_url(origin))


@app.get("/api/gmail/callback")
def gmail_callback(code: str = "", state: str = "", error: str = ""):
    """Google sends the browser back here after you press Allow."""
    back = gmail.return_to_for(state)  # read first: finish_auth uses the state up
    try:
        if error or not code:
            raise GmailError("Google did not give access" + (f" ({error})." if error else "."), 400)
        gmail.finish_auth(code, state)
        result = "connected"
    except GmailError as e:
        result = "error&gmail_message=" + quote(e.detail)
    return RedirectResponse(f"{back}/?gmail={result}#/")


@app.post("/api/gmail/disconnect")
def gmail_disconnect():
    return gmail.disconnect()


@app.post("/api/gmail/test")
def gmail_test():
    return gmail.check_connection()


@app.post("/api/gmail/fetch")
def gmail_fetch(body: GmailFetchBody):
    return service.start_gmail(body.keywords, body.after, body.before, body.limit)


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    data = file.file.read(service.MAX_BYTES + 1)
    if len(data) > service.MAX_BYTES:
        raise ServiceError("The file is larger than 1 MB.", 413)
    return service.start_csv(data, Path(file.filename or "").stem or "Uploaded CSV")


@app.post("/api/sample")
def sample():
    return service.start_sample()


@app.get("/api/history")
def history():
    return service.list_history()


@app.post("/api/history/{batch_id}/open")
def open_history(batch_id: str):
    return service.open_batch(batch_id)


@app.delete("/api/history/{batch_id}")
def delete_history(batch_id: str):
    return service.delete_batch(batch_id)


@app.patch("/api/items/{key}")
def patch_item(key: str, body: PatchBody):
    return service.patch(key, body.draft, body.status)


@app.post("/api/items/{key}/send")
def send_item(key: str):
    return service.send(key)


@app.get("/api/export")
def export():
    return Response(service.export_csv(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="approved_replies.csv"'})


# Serve the built React page when it exists (npm run build in web/).
_dist = service.ROOT / "web" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")