"""FastAPI app for the inbox helper review page.

Run from the project root:   uvicorn api.main:app --reload
"""
from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import service
from .service import ServiceError

app = FastAPI(title="Inbox helper")


@app.exception_handler(ServiceError)
def service_error(_, exc: ServiceError):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


class PatchBody(BaseModel):
    draft: str | None = Field(default=None, max_length=service.MAX_DRAFT_CHARS)
    status: Literal["pending", "approved", "rejected"] | None = None


@app.get("/api/items")
def list_items():
    return service.snapshot()


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    data = file.file.read(service.MAX_BYTES + 1)
    if len(data) > service.MAX_BYTES:
        raise ServiceError("The file is larger than 1 MB.", 413)
    return service.load_csv(data)


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
