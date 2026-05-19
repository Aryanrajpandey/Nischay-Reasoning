from fastapi import APIRouter, Depends
import sqlite3
from api.dependencies import get_student_id, get_db
from db.queries import get_student_profile

router = APIRouter()

@router.get("/")
async def get_trajectory(
    student_id: str = Depends(get_student_id),
    db: sqlite3.Connection = Depends(get_db),
):
    profile = get_student_profile(db, student_id)
    sigs = {}
    if profile and profile.get("personality_signals"):
        sigs = profile["personality_signals"]
        
    analytical = sigs.get("analytical_style", 50)
    motivation = sigs.get("intrinsic_motivation", 50)
    conscientiousness = sigs.get("conscientiousness", 50)
    risk = sigs.get("risk_tolerance", 50)

    # Calculate standard projection trajectories for 10-year outlook based on core traits
    trajectory = []
    for year in range(1, 11):
        # Base career projections
        trajectory.append({
            "year": year,
            "income": int(8 + (year * 1.5) * (analytical / 50.0)),
            "satisfaction": int(60 + (motivation * 0.3) - (year * 1.5)),
            "burnout": int(20 + (year * 3.5) * (1.5 - conscientiousness / 100.0)),
            "autonomy": int(4 + (year * 0.4) * (risk / 50.0))
        })

    return {"trajectory": trajectory}
