"""Production Configuration & Environment Validator
Enforces strict security checks before the application starts up.
In production, unsafe defaults cause immediate, safe process termination.
"""
import os
from typing import List
from backend.app.core.config import settings
from backend.app.core.logging import logger

DISALLOWED_PRODUCTION_SECRETS = [
    "dev-insecure-secret-key-change-in-production-min-32-chars",
    "secret",
    "changeme",
    "admin123",
    "1234567890",
    "HeatLedgerSecretKey2026!",
]

def validate_environment() -> None:
    """Validates configuration parameters and fails safely if production invariants are violated."""
    is_prod = settings.ENVIRONMENT.lower() == "production"

    if is_prod:
        errors: List[str] = []

        # 1. Secret Key validation
        secret = settings.APP_SECRET_KEY
        if len(secret) < 32:
            errors.append("APP_SECRET_KEY must be at least 32 characters in production.")
        if any(disallowed in secret.lower() for disallowed in DISALLOWED_PRODUCTION_SECRETS):
            errors.append("APP_SECRET_KEY contains known insecure development default phrase.")

        # 2. Debug & Demo Mode
        if settings.DEBUG:
            errors.append("DEBUG mode must be set to False in production.")
        if settings.DEMO_MODE:
            errors.append("DEMO_MODE must be set to False in production.")

        # 3. Database URL
        db_url = settings.DATABASE_URL.lower()
        if db_url.startswith("sqlite"):
            errors.append("SQLite is not supported for production deployment. Configure PostgreSQL with PostGIS.")

        # 4. Storage configuration
        if settings.STORAGE_BACKEND == "s3" and not (settings.S3_ACCESS_KEY_ID or os.environ.get("AWS_ACCESS_KEY_ID")):
            errors.append("S3 storage backend configured but AWS credentials not found.")

        # 5. Algorithm safety
        if settings.ALGORITHM not in ["HS256", "RS256", "ES256"]:
            errors.append(f"Disallowed or insecure JWT ALGORITHM '{settings.ALGORITHM}'. Must be HS256, RS256, or ES256.")

        if errors:
            error_message = (
                "\n" + "=" * 80 + "\n"
                "CRITICAL PRODUCTION CONFIGURATION ERROR - STARTUP ABORTED:\n"
                + "\n".join(f" - [!] {err}" for err in errors) + "\n"
                + "=" * 80 + "\n"
            )
            logger.critical(error_message)
            raise RuntimeError(error_message)
        else:
            logger.info("Production configuration validation passed: All security invariants satisfied.")
    else:
        # Development / Testing warnings
        if settings.APP_SECRET_KEY in DISALLOWED_PRODUCTION_SECRETS:
            logger.warning("[DEV NOTICE] Using default development secret key. Do NOT use in production!")
        if settings.DEMO_MODE:
            logger.info("[DEV NOTICE] DEMO_MODE is enabled (Hyderabad sample fixtures active).")
