import logging
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

from backend.app.core.config import settings
from backend.app.core.database import Base
import backend.app.models

logger = logging.getLogger("alembic.env")

# this is the Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    if not settings.MIGRATION_DATABASE_URL and settings.DATABASE_URL.startswith(("postgres://", "postgresql://")):
        logger.warning(
            "SECURITY/ARCHITECTURE WARNING: MIGRATION_DATABASE_URL is not set. Falling back to runtime DATABASE_URL. "
            "In production, Alembic migrations must execute under a dedicated schema-owner database role (e.g. heatledger_owner), "
            "while the FastAPI runtime executes as a restricted NOBYPASSRLS application role (e.g. heatledger_app_user)."
        )
    url = settings.MIGRATION_DATABASE_URL or settings.DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connect_args = {}
    if get_url().startswith("sqlite"):
        connect_args["check_same_thread"] = False

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
