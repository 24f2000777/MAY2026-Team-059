from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.attachments import router as attachments_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.complaints import router as complaint_router
from app.api.feedback import router as feedback_router
from app.api.notifications import router as notification_router
from app.api.dashboard import router as dashboard_router
from app.api.ml import router as ml_router
from app.core.database import AsyncSessionLocal
from app.core.redis import check_redis_connection
from app.core.exception_handlers import register_exception_handlers
from app.schemas.common import SuccessResponse
from app.services.routing_service import seed_departments


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan.

    Runs once when the application starts and
    once again when it shuts down.
    """

    # Startup
    await check_redis_connection()
    async with AsyncSessionLocal() as db:
        await seed_departments(db)
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

from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Serves uploaded complaint attachments back out (dev-only local
# filesystem storage, see app/utils/storage.py). Directory must exist
# before StaticFiles mounts it, it won't until the first upload
# otherwise.
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount(f"/{settings.UPLOAD_DIR}", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(admin_router)
app.include_router(attachments_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(complaint_router)
app.include_router(feedback_router)
app.include_router(notification_router)
app.include_router(dashboard_router)
app.include_router(ml_router)


@app.get(
    "/",
    response_model=SuccessResponse[None],
    tags=["Root"],
)
async def root():
    return SuccessResponse[None](
        message="Welcome to NAGRIK AI API",
    )


@app.get(
    "/health",
    response_model=SuccessResponse[dict],
    tags=["Health"],
)
async def health_check():
    return SuccessResponse[dict](
        message="Service is healthy.",
        data={"status": "ok"},
    )