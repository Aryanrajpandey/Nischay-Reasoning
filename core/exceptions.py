from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


class NischayException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class IntelligenceEngineError(NischayException):
    pass


class AgentError(NischayException):
    pass


class NischayMemoryError(NischayException):
    """Renamed from MemoryError to avoid shadowing Python's built-in MemoryError."""
    pass


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(NischayException)
    async def nischay_exception_handler(request: Request, exc: NischayException):
        logger.warning("nischay_exception", message=exc.message, path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "type": type(exc).__name__},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred.", "type": "InternalError"},
        )
