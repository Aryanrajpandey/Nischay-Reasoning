from fastapi import APIRouter, Depends
import sqlite3
from api.dependencies import get_db, get_student_id
from db.queries import get_student_memories, get_memory_count

router = APIRouter()


@router.get("/")
async def get_memory(
    type: str = None,
    db: sqlite3.Connection = Depends(get_db),
    student_id: str = Depends(get_student_id),
):
    memories = get_student_memories(db, student_id, memory_type=type, limit=50)
    count = get_memory_count(db, student_id)
    return {"memories": memories, "total": count}
