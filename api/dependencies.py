from fastapi import Depends
import sqlite3
from db.client import get_db as get_sqlite_db
from core.security import get_current_student_id


def get_db() -> sqlite3.Connection:
    with get_sqlite_db() as conn:
        yield conn


async def get_student_id(
    student_id: str = Depends(get_current_student_id),
) -> str:
    return student_id
