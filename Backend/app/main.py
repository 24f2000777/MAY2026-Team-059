from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.complaints import router as complaint_router
from app.api.notifications import router as notification_router
from app.core.redis import check_redis_connection

app = FastAPI(
    title="NAGRIK AI",
    version="1.0.0",
    description="AI Powered Civic Complaint Management System",
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
    
@app.on_event("startup")
async def startup_event():
    check_redis_connection()