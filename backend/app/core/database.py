import json
from decimal import Decimal
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Normalize postgres:// to postgresql:// for SQLAlchemy 1.4+ / 2.0+ compatibility
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

def _custom_json_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Engine setup
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    json_serializer=lambda obj: json.dumps(obj, default=_custom_json_serializer),
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# SEC-RLS: Ensure transaction-scoped identity is preserved across intermediate commits
@event.listens_for(Session, "after_begin")
def reapply_transaction_identity(session, transaction, connection):
    if connection.dialect.name == "postgresql":
        uid = session.info.get("current_user_id", "")
        role = session.info.get("current_user_role", "")
        try:
            connection.execute(
                text("SELECT set_config('app.current_user_id', :uid, true)"),
                {"uid": str(uid or "")}
            )
            connection.execute(
                text("SELECT set_config('app.current_user_role', :role, true)"),
                {"role": str(role or "")}
            )
        except Exception as e:
            logger.warning(f"Could not re-apply PostgreSQL RLS session variables: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
