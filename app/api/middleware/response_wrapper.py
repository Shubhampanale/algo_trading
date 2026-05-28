from __future__ import annotations

import json
from typing import Any, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_400_BAD_REQUEST

_SKIP_HEADERS = {"content-length", "content-type", "transfer-encoding"}


class ResponseWrapperMiddleware(BaseHTTPMiddleware):
    """Normalize API responses to a common envelope.

    Success: {status:'success', status_code, message, data}
    Error:   {status:'error',   status_code, message, data}
    """

    EXCLUDE_PATHS = {"/openapi.json", "/docs", "/redoc", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        # ✅ Skip Swagger/OpenAPI/doc routes — don't wrap them
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        try:
            resp: Response = await call_next(request)

            content_type = resp.headers.get("content-type", "")

            if "application/json" not in content_type:
                return resp

            try:
                body_bytes = b""
                async for chunk in resp.body_iterator:  # type: ignore[attr-defined]
                    body_bytes += chunk
                raw = body_bytes.decode("utf-8") if body_bytes else ""
                data_parsed: Any = json.loads(raw) if raw else None

            except Exception:
                return Response(
                    content=body_bytes,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    media_type=content_type,
                )

            safe_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() not in _SKIP_HEADERS
            }

            # Already an envelope — return as-is
            if (
                isinstance(data_parsed, dict)
                and "status" in data_parsed
                and "data" in data_parsed
                and "message" in data_parsed
            ):
                return JSONResponse(
                    status_code=resp.status_code,
                    content=data_parsed,
                    headers=safe_headers,
                )

            is_error = resp.status_code >= 400
            default_message = "error" if is_error else "success"

            if isinstance(data_parsed, dict) and "message" in data_parsed:
                message = data_parsed.pop("message", default_message) or default_message
                data_out: Any = data_parsed if data_parsed else None
            else:
                message = default_message
                data_out = data_parsed

            wrapped = {
                "status": "error" if is_error else "success",
                "status_code": resp.status_code,
                "message": message,
                "data": data_out,
            }
            return JSONResponse(
                status_code=resp.status_code,
                content=wrapped,
                headers=safe_headers,
            )

        except Exception as exc:
            status_code = getattr(exc, "status_code", HTTP_400_BAD_REQUEST)
            detail = getattr(exc, "detail", str(exc))
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "error",
                    "status_code": status_code,
                    "message": detail,
                    "data": None,
                },
            )