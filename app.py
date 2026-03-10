"""
Trafilatura Extraction Service — tương thích web_search.py của chatbot.

POST /extract — body: {"url": "...", "output_format": "txt"}
Response: {"success": True, "data": {"text": "..."}}

Chatbot gọi: services/web_search._extract_via_trafilatura()
"""

import json
import logging
import os
from typing import Any

import trafilatura
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("trafilatura")


class ExtractRequest(BaseModel):
    url: str | None = Field(default=None, description="URL cần trích nội dung")
    html: str | None = Field(default=None, description="HTML thô (nếu có sẵn)")
    output_format: str = Field(default="txt", description="txt | json")

    @model_validator(mode="after")
    def validate_input(self) -> "ExtractRequest":
        url = (self.url or "").strip() if self.url else ""
        html = (self.html or "").strip() if self.html else ""
        if not url and not html:
            raise ValueError("Cần có 'url' hoặc 'html' (không được để trống).")
        if self.output_format not in {"json", "txt"}:
            raise ValueError("output_format phải là 'json' hoặc 'txt'.")
        if url and not url.startswith(("http://", "https://")):
            raise ValueError("URL phải bắt đầu bằng http:// hoặc https://")
        return self


app = FastAPI(
    title="Trafilatura Extraction Service",
    version="1.0.0",
    description="Trích nội dung chính từ webpage — chatbot web_search dùng endpoint /extract.",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Trả 422 với detail rõ ràng khi validation fail."""
    errors = exc.errors()
    detail = "; ".join(
        f"{e.get('loc', [])[-1]}: {e.get('msg', 'invalid')}" for e in errors
    ) if errors else str(exc)
    logger.warning("Validation error on %s: %s", request.url.path, detail)
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "errors": errors},
    )

_TIMEOUT = float(os.getenv("TRAFILATURA_TIMEOUT_SECONDS", "20"))
_NO_SSL = os.getenv("TRAFILATURA_NO_SSL", "false").lower() == "true"


def _fetch_url(url: str) -> str | None:
    """Tải HTML từ URL. Thử no_ssl nếu lần đầu thất bại."""
    downloaded = trafilatura.fetch_url(url, no_ssl=_NO_SSL, config=None)
    if downloaded:
        return downloaded
    if not _NO_SSL:
        downloaded = trafilatura.fetch_url(url, no_ssl=True, config=None)
    return downloaded


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract")
def extract(request: ExtractRequest) -> dict[str, Any]:
    source_html = (request.html or "").strip() or None
    source_url = (request.url or "").strip() or None

    if not source_html and source_url:
        logger.info("Fetching URL: %s", source_url[:80] + "..." if len(source_url) > 80 else source_url)
        source_html = _fetch_url(source_url)
        if not source_html:
            logger.warning("Failed to fetch URL: %s", source_url[:100])
            raise HTTPException(
                status_code=400,
                detail=f"Không tải được nội dung từ URL. (Site có thể chặn bot hoặc URL sai). URL: {(source_url[:80] + '...') if len(source_url) > 80 else source_url}",
            )

    if not source_html:
        raise HTTPException(status_code=400, detail="Không có nội dung để trích.")

    extracted = trafilatura.extract(
        source_html,
        url=source_url,
        favor_precision=True,
        include_links=False,
        include_images=False,
        include_comments=False,
        output_format=request.output_format,
        target_language=os.getenv("TRAFILATURA_TARGET_LANGUAGE") or None,
        deduplicate=True,
        with_metadata=request.output_format == "json",
    )

    if not extracted:
        raise HTTPException(
            status_code=422,
            detail="Trafilatura không trích được nội dung từ trang này.",
        )

    if request.output_format == "json":
        try:
            payload = json.loads(extracted)
        except json.JSONDecodeError:
            payload = {"raw": extracted}
    else:
        payload = {"text": extracted}

    return {
        "success": True,
        "source": {"url": source_url},
        "timeout_seconds": _TIMEOUT,
        "data": payload,
    }
