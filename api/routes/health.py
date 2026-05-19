from fastapi import APIRouter
from core.config import settings
from db.client import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint with DB connectivity verification."""
    db_ok = False
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
            db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "version": "3.0.0",
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "unreachable",
    }
