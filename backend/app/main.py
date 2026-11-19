from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.database import engine, Base
from backend.app.core.env_validator import validate_environment
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
    # SEC-04: Validate configuration and fail safely if production invariants violated
    validate_environment()
    
    # Ensure database schema is initialized
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
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/api/v1/openapi.json" if settings.DEBUG else None,
)

# SEC-06: Strict CORS Configuration
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
allow_creds = True
if "*" in cors_origins:
    if settings.ENVIRONMENT == "production":
        # Disallow wildcard origin with credentials in production
        cors_origins = ["https://heatledger.app", "https://app.heatledger.org"]
    else:
        allow_creds = False # Browsers reject credentials=True with wildcard origin

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_creds,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    expose_headers=["Content-Disposition", "X-Report-Integrity-SHA256", "X-Process-Time-Sec"],
)

# SEC-06: Production Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    # Never leak internal tracebacks in response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. This incident has been logged for review."},
    )

# Include v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(profiles_router, prefix="/api/v1")
app.include_router(shifts_router, prefix="/api/v1")
app.include_router(breaks_router, prefix="/api/v1")
app.include_router(location_router, prefix="/api/v1")
app.include_router(climate_router, prefix="/api/v1")
app.include_router(earnings_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(shares_router, prefix="/api/v1")
app.include_router(organisations_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
def public_health_check():
    return {
        "status": "UP",
        "service": "HeatLedger API",
        "environment": settings.ENVIRONMENT,
    }
