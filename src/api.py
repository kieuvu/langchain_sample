import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from exception.session_not_found import SessionNotFound
from schemas.api import (
    MessageRequest,
    MessageResponse,
    SessionCreated,
)
from services.chat import ChatService

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).with_name("static")
CHAT_PAGE = Path(__file__).parent / "static" / "chat.html"


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(service: ChatService | None = None) -> FastAPI:
    service = service if service is not None else ChatService()
    app = FastAPI(title="Chat Service", version="0.1.0")

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    chat_html = CHAT_PAGE.read_text(encoding="utf-8")

    @app.get("/", include_in_schema=False)
    async def chat_page() -> HTMLResponse:
        return HTMLResponse(chat_html)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/sessions", status_code=201)
    async def create_session() -> SessionCreated:
        return SessionCreated(session_id=service.create_session())

    @app.post("/v1/sessions/{session_id}/messages")
    async def send_message(session_id: str, body: MessageRequest) -> MessageResponse:
        try:
            answer = await service.send(session_id, body.message)
        except SessionNotFound as exc:
            raise HTTPException(status_code=404, detail="Session not found.") from exc
        except Exception as exc:
            logger.exception("Chat request failed")
            raise HTTPException(
                status_code=502, detail="Could not process the message."
            ) from exc
        return MessageResponse(session_id=session_id, answer=answer)

    @app.post("/v1/sessions/{session_id}/messages/stream")
    async def stream_message(
        session_id: str, body: MessageRequest
    ) -> StreamingResponse:
        try:
            service.require_session(session_id)
        except SessionNotFound as exc:
            raise HTTPException(status_code=404, detail="Session not found.") from exc

        async def events() -> AsyncIterator[str]:
            try:
                async for event, data in service.stream(session_id, body.message):
                    yield sse(event, data)
            except Exception:
                logger.exception("Chat stream failed")
                yield sse("error", {"message": "Could not process the message."})

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app
