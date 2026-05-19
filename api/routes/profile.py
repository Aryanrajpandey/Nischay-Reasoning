"""
Profile API routes.
"""

from fastapi import APIRouter, Depends, HTTPException
import sqlite3
from api.dependencies import get_db, get_student_id
from db.queries import get_student_profile, update_student_profile
from schemas.profile import ProfileResponse, ProfileUpdateRequest

router = APIRouter()


@router.get("/", response_model=ProfileResponse)
async def get_profile(
    db: sqlite3.Connection = Depends(get_db),
    student_id: str = Depends(get_student_id),
):
    profile = get_student_profile(db, student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Recompute completeness to ensure it's fresh
    from db.queries import compute_profile_completeness, update_student_profile
    new_pct = compute_profile_completeness(profile)
    if new_pct != profile.get('completeness'):
        profile = update_student_profile(db, student_id, {"completeness": new_pct})
        
    return ProfileResponse(**profile)


@router.patch("/", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    db: sqlite3.Connection = Depends(get_db),
    student_id: str = Depends(get_student_id),
):
    update_data = body.dict(exclude_none=True)
    
    # Get current profile to merge for completeness check
    current = get_student_profile(db, student_id) or {}
    merged = {**current, **update_data}
    
    from db.queries import compute_profile_completeness
    update_data["completeness"] = compute_profile_completeness(merged)
    
    updated = update_student_profile(db, student_id, update_data)
    return ProfileResponse(**updated)
