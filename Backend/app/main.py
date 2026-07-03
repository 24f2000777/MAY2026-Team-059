from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.complaints import router as complaint_router
from app.api.notifications import router as notification_router
from app.core.redis import check_redis_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan.

    Runs once when the application starts and
    once again when it shuts down.
    """

    # Startup
    check_redis_connection()
    """
    # connect_to_vector_db()
    # start_scheduler()
    # initialize_ml_model()
    """
    yield

    # Shutdown
    # (Nothing to clean up for now)
    """
    close_vector_db()
    stop_scheduler()
    """


app = FastAPI(
    title="NAGRIK AI",
    version="1.0.0",
    description="AI Powered Civic Complaint Management System",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(complaint_router)
app.include_router(notification_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to NAGRIK AI API"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok"
    }