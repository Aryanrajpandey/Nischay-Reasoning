from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ProfileResponse(BaseModel):
    student_id: str
    name: str
    email: str
    bio: Optional[str] = None
    goals: Optional[List[str]] = []
    completeness: int = 0
    personality_signals: Optional[Dict[str, Any]] = {}

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    goals: Optional[List[str]] = None
