import sqlite3
from contextlib import contextmanager
from core.config import settings


def _parse_sqlite_path(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "", 1)
    return url


def init_db() -> None:
    db_path = _parse_sqlite_path(settings.DATABASE_URL)
    
    # Dynamic sync from Supabase Storage during cold start
    from db.sync import download_database_from_supabase
    download_database_from_supabase(db_path)
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                student_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                bio TEXT,
                goals TEXT,
                completeness INTEGER DEFAULT 0,
                personality_signals TEXT,
                contradiction_score INTEGER DEFAULT 0,
                conversation_stage TEXT DEFAULT 'EXPLORATION',
                behavioral_drift TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(student_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(student_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                agent TEXT,
                confidence REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES conversations(session_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                session_ref TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(student_id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db() -> sqlite3.Connection:
    db_path = _parse_sqlite_path(settings.DATABASE_URL)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    has_committed = False
    try:
        yield conn
        conn.commit()
        has_committed = True
    finally:
        conn.close()
        # Persist the changes back to Supabase Storage after committing
        if has_committed:
            from db.sync import upload_database_to_supabase
            upload_database_to_supabase(db_path)
