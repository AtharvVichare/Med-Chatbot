from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.core.logger import setup_logging, logger
from backend.app.db.session import SessionLocal
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.patients import router as patients_router
from backend.app.api.v1.medical import router as medical_router
from backend.app.api.v1.disease_prediction import router as disease_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.assistant import router as assistant_router
from backend.app.api.v1.future_insights import router as insights_router
from backend.app.api.v1.beds import router as beds_router
from backend.app.api.v1.inventory import router as inventory_router
from backend.app.api.v1.directory import router as directory_router
from backend.app.api.v1.doctor_verification import router as doctor_verification_router
from backend.app.api.v1.billing import router as billing_router
from backend.app.api.v1.agents import router as agents_router
from backend.app.api.v1.conversational_bi import router as conversational_bi_router
from backend.app.api.v1.family import router as family_router
from backend.app.api.v1.clinical_workspace import router as doctor_workspace_router
from backend.app.api.v1.nursing_workspace import router as nurse_workspace_router

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Aarogya-Drishti 2.0 AI-Native Hospital Management System & Longitudinal EHR"
)

# CORS Middleware - configurable origins with safe defaults
allowed_origins_list = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
if not allowed_origins_list:
    allowed_origins_list = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Exception Handling
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the system administrator."}
    )

# Health & Readiness Endpoints
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

@app.get("/ready", tags=["System"])
def readiness_check():
    try:
        db: Session = SessionLocal()
        # Verify active PostgreSQL database connectivity
        result = db.execute(text("SELECT 1")).scalar()
        dialect = db.bind.dialect.name
        db.close()
        if result == 1:
            return {
                "status": "ready",
                "database": "connected",
                "dialect": dialect
            }
        raise Exception("Database check returned non-1")
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "detail": "Failed to connect to primary database"
            }
        )

# Register API v1 Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(patients_router, prefix=settings.API_V1_STR)
app.include_router(medical_router, prefix=settings.API_V1_STR)
app.include_router(disease_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(assistant_router, prefix=settings.API_V1_STR)
app.include_router(insights_router, prefix=settings.API_V1_STR)
app.include_router(beds_router, prefix=settings.API_V1_STR)
app.include_router(inventory_router, prefix=settings.API_V1_STR)
app.include_router(directory_router, prefix=settings.API_V1_STR)
app.include_router(doctor_verification_router, prefix=settings.API_V1_STR)
app.include_router(billing_router, prefix=settings.API_V1_STR)
app.include_router(agents_router, prefix=settings.API_V1_STR)
app.include_router(conversational_bi_router, prefix=settings.API_V1_STR)
app.include_router(family_router, prefix=settings.API_V1_STR)
app.include_router(doctor_workspace_router, prefix=settings.API_V1_STR)
app.include_router(nurse_workspace_router, prefix=settings.API_V1_STR)

