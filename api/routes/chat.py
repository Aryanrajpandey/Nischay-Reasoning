from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import sqlite3
from api.dependencies import get_db, get_student_id
from services.chat_service import ChatService
from schemas.chat import ChatRequest, ChatResponse
from db.queries import create_conversation
import json
import uuid

router = APIRouter()


@router.post("/new", response_model=dict)
async def new_session(
    db: sqlite3.Connection = Depends(get_db),
    student_id: str = Depends(get_student_id),
):
    """Create a new session ID for a student and persist it."""
    session_id = str(uuid.uuid4())
    create_conversation(db, session_id, student_id)
    return {"session_id": session_id, "student_id": student_id}


@router.post("/{session_id}", response_model=ChatResponse)
async def send_message(
    session_id: str,
    body: ChatRequest,
    db: sqlite3.Connection = Depends(get_db),
    student_id: str = Depends(get_student_id),
):
    svc = ChatService(db, student_id)
    return await svc.process_message(
        session_id=session_id,
        message=body.message,
        agent_override=body.agent_override,
    )


@router.post("/{session_id}/stream")
async def stream_message(
    session_id: str,
    body: ChatRequest,
    db: sqlite3.Connection = Depends(get_db),
    student_id: str = Depends(get_student_id),
):
    svc = ChatService(db, student_id)

    async def event_stream():
        async for chunk in svc.stream_message(
            session_id, body.message, agent_override=body.agent_override
        ):
            yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
