from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.database import engine, Base
import backend.app.models # register all SQLAlchemy entities

# Routers
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.profiles import router as profiles_router
from backend.app.api.v1.shifts import router as shifts_router
from backend.app.api.v1.breaks import router as breaks_router
from backend.app.api.v1.location import router as location_router
from backend.app.api.v1.climate import router as climate_router
from backend.app.api.v1.earnings import router as earnings_router
from backend.app.api.v1.evidence import router as evidence_router
from backend.app.api.v1.shares import router as shares_router
from backend.app.api.v1.organisations import router as organisations_router
from backend.app.api.v1.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HeatLedger Backend Starting Up...")
    # Ensure database tables exist (fallback if migrations not executed)
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema verified.")
    yield
    logger.info("HeatLedger Backend Shutting Down...")

app = FastAPI(
    title="HeatLedger API",
    description=(
        "Worker-owned climate exposure and earnings evidence platform. "
        "Your work. Your conditions. Your evidence."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to verified frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. This event has been securely audited."},
    )

# Versioned API Router inclusion
API_V1_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(profiles_router, prefix=API_V1_PREFIX)
app.include_router(shifts_router, prefix=API_V1_PREFIX)
app.include_router(breaks_router, prefix=API_V1_PREFIX)
app.include_router(location_router, prefix=API_V1_PREFIX)
app.include_router(climate_router, prefix=API_V1_PREFIX)
app.include_router(earnings_router, prefix=API_V1_PREFIX)
app.include_router(evidence_router, prefix=API_V1_PREFIX)
app.include_router(shares_router, prefix=API_V1_PREFIX)
app.include_router(organisations_router, prefix=API_V1_PREFIX)
app.include_router(admin_router, prefix=API_V1_PREFIX)

@app.get("/")
def root_info():
    return {
        "platform": "HeatLedger",
        "tagline": "Your work. Your conditions. Your evidence.",
        "version": "1.0.0",
        "jurisdiction": "Hyderabad, Telangana, India",
        "docs_url": "/docs",
        "api_v1": "/api/v1",
    }
