import sqlite3
from typing import Optional, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone
import json


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    if data.get("goals"):
        data["goals"] = json.loads(data["goals"])
    if data.get("personality_signals"):
        data["personality_signals"] = json.loads(data["personality_signals"])
    return data


def get_student_by_email(db: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
    row = db.execute(
        "SELECT student_id, email, name, password_hash, created_at FROM students WHERE email = ?",
        (email,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def create_student(db: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    student_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT INTO students (student_id, email, name, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            student_id,
            data["email"],
            data.get("name"),
            data.get("password_hash"),
            now,
        ),
    )

    profile_payload = {
        "student_id": student_id,
        "name": data.get("name"),
        "email": data["email"],
        "bio": data.get("bio"),
        "goals": json.dumps(data.get("goals", [])),
        "completeness": data.get("completeness", 0),
        "personality_signals": json.dumps(data.get("personality_signals", {})),
        "updated_at": now,
    }
    db.execute(
        """
        INSERT INTO profiles (student_id, name, email, bio, goals, completeness, personality_signals, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            profile_payload["student_id"],
            profile_payload["name"],
            profile_payload["email"],
            profile_payload["bio"],
            profile_payload["goals"],
            profile_payload["completeness"],
            profile_payload["personality_signals"],
            profile_payload["updated_at"],
        ),
    )

    return {
        "student_id": student_id,
        "email": data["email"],
        "name": data.get("name"),
        "password_hash": data.get("password_hash"),
        "created_at": now,
    }


def get_student_profile(db: sqlite3.Connection, student_id: str) -> Optional[Dict[str, Any]]:
    row = db.execute(
        """
        SELECT student_id, name, email, bio, goals, completeness, personality_signals,
               contradiction_score, conversation_stage, behavioral_drift
        FROM profiles
        WHERE student_id = ?
        """,
        (student_id,),
    ).fetchone()
    return _row_to_dict(row) if row else None


def update_student_profile(db: sqlite3.Connection, student_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    existing = get_student_profile(db, student_id)
    payload = {
        "name": data.get("name", existing.get("name") if existing else None),
        "email": data.get("email", existing.get("email") if existing else None),
        "bio": data.get("bio", existing.get("bio") if existing else None),
        "goals": json.dumps(data.get("goals", existing.get("goals") if existing else [])),
        "completeness": data.get("completeness", existing.get("completeness") if existing else 0),
        "personality_signals": json.dumps(
            data.get("personality_signals", existing.get("personality_signals") if existing else {})
        ),
        "contradiction_score": data.get("contradiction_score", existing.get("contradiction_score") if existing else 0),
        "conversation_stage": data.get("conversation_stage", existing.get("conversation_stage") if existing else "EXPLORATION"),
        "behavioral_drift": data.get("behavioral_drift", existing.get("behavioral_drift") if existing else None),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    db.execute(
        """
        INSERT INTO profiles (student_id, name, email, bio, goals, completeness, personality_signals,
                             contradiction_score, conversation_stage, behavioral_drift, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id) DO UPDATE SET
            name = excluded.name,
            email = excluded.email,
            bio = excluded.bio,
            goals = excluded.goals,
            completeness = excluded.completeness,
            personality_signals = excluded.personality_signals,
            contradiction_score = excluded.contradiction_score,
            conversation_stage = excluded.conversation_stage,
            behavioral_drift = excluded.behavioral_drift,
            updated_at = excluded.updated_at
        """,
        (
            student_id,
            payload["name"],
            payload["email"],
            payload["bio"],
            payload["goals"],
            payload["completeness"],
            payload["personality_signals"],
            payload["contradiction_score"],
            payload["conversation_stage"],
            payload["behavioral_drift"],
            payload["updated_at"],
        ),
    )

    return {
        "student_id": student_id,
        "name": payload["name"],
        "email": payload["email"],
        "bio": payload["bio"],
        "goals": json.loads(payload["goals"]),
        "completeness": payload["completeness"],
        "personality_signals": json.loads(payload["personality_signals"]),
    }


def create_conversation(db: sqlite3.Connection, session_id: str, student_id: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO conversations (session_id, student_id, created_at) VALUES (?, ?, ?)",
        (session_id, student_id, now),
    )
    return {"session_id": session_id, "student_id": student_id, "created_at": now}


def save_chat_message(
    db: sqlite3.Connection,
    session_id: str,
    role: str,
    content: str,
    agent: Optional[str] = None,
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        """
        INSERT INTO chat_messages (session_id, role, content, agent, confidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, role, content, agent, confidence, now),
    )
    return {
        "id": cursor.lastrowid,
        "session_id": session_id,
        "role": role,
        "content": content,
        "agent": agent,
        "confidence": confidence,
        "created_at": now,
    }


def get_conversation_history(
    db: sqlite3.Connection, session_id: str, limit: int = 20
) -> list:
    rows = db.execute(
        """
        SELECT role, content, agent, confidence, created_at
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    result = [dict(r) for r in rows]
    result.reverse()
    return result


def save_memory(
    db: sqlite3.Connection,
    student_id: str,
    memory_type: str,
    content: str,
    confidence: float = 0.0,
    session_ref: Optional[str] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    cursor = db.execute(
        """
        INSERT INTO memories (student_id, type, content, confidence, session_ref, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (student_id, memory_type, content, confidence, session_ref, now),
    )
    return {
        "id": cursor.lastrowid,
        "student_id": student_id,
        "type": memory_type,
        "content": content,
        "confidence": confidence,
        "session_ref": session_ref,
        "created_at": now,
    }


def get_student_memories(
    db: sqlite3.Connection, student_id: str, memory_type: Optional[str] = None, limit: int = 50
) -> list:
    if memory_type:
        rows = db.execute(
            """
            SELECT id, type, content, confidence, session_ref, created_at
            FROM memories
            WHERE student_id = ? AND type = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (student_id, memory_type, limit),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT id, type, content, confidence, session_ref, created_at
            FROM memories
            WHERE student_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (student_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_memory_count(db: sqlite3.Connection, student_id: str) -> int:
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM memories WHERE student_id = ?",
        (student_id,),
    ).fetchone()
    return row["cnt"] if row else 0


def compute_profile_completeness(profile: Dict[str, Any]) -> int:
    fields = ["name", "email", "bio", "goals", "personality_signals"]
    filled = 0
    for f in fields:
        val = profile.get(f)
        if val and val not in ([], {}, "", None, "[]", "{}"):
            filled += 1
    return int((filled / len(fields)) * 100)
