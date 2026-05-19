from fastapi import APIRouter, Depends
import sqlite3
from api.dependencies import get_student_id, get_db
from db.queries import get_student_profile

router = APIRouter()

@router.get("/")
async def get_careers(
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

    # Dynamic career matching calculations based on extracted cognitive profile
    careers = [
        {
            "name": "B.Tech Computer Science & Engineering",
            "fit": int((analytical * 0.65) + (conscientiousness * 0.35))
        },
        {
            "name": "Product Management & Tech Entrepreneurship",
            "fit": int((risk * 0.55) + (motivation * 0.45))
        },
        {
            "name": "Bachelor of Design (B.Des)",
            "fit": int((motivation * 0.70) + (analytical * 0.30))
        },
        {
            "name": "B.Com + Chartered Accountancy (CA)",
            "fit": int((conscientiousness * 0.70) + ((100 - risk) * 0.30))
        }
    ]

    # Sort in descending order of compatibility match
    careers.sort(key=lambda x: x["fit"], reverse=True)

    return {"careers": careers}
