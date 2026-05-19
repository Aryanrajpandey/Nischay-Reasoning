from fastapi import APIRouter, Depends, HTTPException, status
import sqlite3
from api.dependencies import get_db
from core.security import hash_password, verify_password, create_access_token
from db.queries import get_student_by_email, create_student
from schemas.auth import RegisterRequest, LoginRequest, TokenResponse
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: sqlite3.Connection = Depends(get_db)):
    existing = get_student_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    hashed = hash_password(body.password)
    student = create_student(db, {
        "email": body.email,
        "name": body.name,
        "password_hash": hashed,
    })

    token = create_access_token({"sub": student["student_id"]})
    logger.info("student_registered", student_id=student["student_id"])
    return TokenResponse(access_token=token, student_id=student["student_id"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: sqlite3.Connection = Depends(get_db)):
    student = get_student_by_email(db, body.email)
    if not student:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(body.password, student["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({"sub": student["student_id"]})
    logger.info("student_login", student_id=student["student_id"])
    return TokenResponse(access_token=token, student_id=student["student_id"])
