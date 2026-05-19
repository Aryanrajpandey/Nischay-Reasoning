from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import sqlite3
from api.dependencies import get_student_id, get_db
from services.resume_service import ResumeService

router = APIRouter()

@router.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    student_id: str = Depends(get_student_id),
    db: sqlite3.Connection = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    contents = await file.read()
    svc = ResumeService()
    
    text = svc.extract_text(contents, file.filename)
    feedback = await svc.analyze(text)

    return {
        "filename": file.filename,
        "student_id": student_id,
        "feedback": feedback
    }
