"""
Nischay AI — FastAPI Backend
Adaptive Career Reasoning System v3.0
"""

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
import structlog

from core.config import settings
from core.logging import configure_logging
from core.exceptions import register_exception_handlers
from api.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from db.client import init_db
from api.routes import auth, chat, profile, memory, careers, trajectory, resume, health

configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("nischay_startup", version="3.0", environment=settings.ENVIRONMENT)
    yield
    logger.info("nischay_shutdown")


app = FastAPI(
    title="Nischay AI",
    description="Adaptive Career Reasoning System",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# CORS
cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.DEBUG:
    cors_kwargs["allow_origin_regex"] = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
else:
    cors_kwargs["allow_origins"] = settings.ALLOWED_ORIGINS

app.add_middleware(CORSMiddleware, **cors_kwargs)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes
app.include_router(health.router,      prefix="/api/v1",            tags=["health"])
app.include_router(auth.router,        prefix="/api/v1/auth",       tags=["auth"])
app.include_router(chat.router,        prefix="/api/v1/chat",       tags=["chat"])
app.include_router(profile.router,     prefix="/api/v1/profile",    tags=["profile"])
app.include_router(memory.router,      prefix="/api/v1/memory",     tags=["memory"])
app.include_router(careers.router,     prefix="/api/v1/careers",    tags=["careers"])
app.include_router(trajectory.router,  prefix="/api/v1/trajectory", tags=["trajectory"])
app.include_router(resume.router,      prefix="/api/v1/resume",     tags=["resume"])

# Serve static files (HTML)
@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/app")
async def read_app():
    return FileResponse("app.html")

if settings.DEBUG:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - API Docs",
            swagger_css_url="/static/docs.css",
        )
