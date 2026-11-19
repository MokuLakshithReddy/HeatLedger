import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.core.security import get_password_hash, create_access_token
from backend.app.models.entities import User, WorkerProfile, Organisation, OrganisationMember, utc_now

TEST_DB_URL = "sqlite:///./test_heatledger.db"

engine_test = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)
    if os.path.exists("./test_heatledger.db"):
        try:
            os.remove("./test_heatledger.db")
        except Exception:
            pass

@pytest.fixture
def db_session():
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def worker_user(db_session):
    user = User(
        email="test.worker@heatledger.local",
        phone="+919999900001",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Test Worker Raju",
        role="worker",
        preferred_language="en",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = WorkerProfile(
        user_id=user.id,
        primary_platforms=["Swiggy", "Zomato"],
        city="Hyderabad",
        consented_location_tracking=True,
    )
    db_session.add(profile)
    db_session.commit()
    return user

@pytest.fixture
def worker_b_user(db_session):
    user = User(
        email="test.worker_b@heatledger.local",
        phone="+919999900002",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Worker B Suresh",
        role="worker",
        preferred_language="en",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def org_user_and_org(db_session):
    org = Organisation(
        name="Test Worker Union",
        slug="test-union",
        contact_email="union@test.org",
        org_type="union",
        is_approved=True,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    user = User(
        email="advocate@test-union.org",
        phone="+919999900003",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Advocate Lakshmi",
        role="organisation_admin",
        preferred_language="en",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    member = OrganisationMember(
        organisation_id=org.id,
        user_id=user.id,
        role="admin",
        is_active=True,
    )
    db_session.add(member)
    db_session.commit()
    return user, org

@pytest.fixture
def admin_user(db_session):
    admin = db_session.query(User).filter(User.email == "admin@heatledger.local").first()
    if not admin:
        admin = User(
            id="admin-system-test-id",
            email="admin@heatledger.local",
            phone="+919000000000",
            hashed_password=get_password_hash("AdminPass123!"),
            full_name="System Administrator",
            role="system_admin",
            preferred_language="en",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    return admin

@pytest.fixture
def worker_auth_headers(worker_user):
    token = create_access_token({"sub": worker_user.id, "role": worker_user.role, "email": worker_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def worker_b_auth_headers(worker_b_user):
    token = create_access_token({"sub": worker_b_user.id, "role": worker_b_user.role, "email": worker_b_user.email})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def org_auth_headers(org_user_and_org):
    user, org = org_user_and_org
    token = create_access_token({"sub": user.id, "role": user.role, "email": user.email})
    return {"Authorization": f"Bearer {token}"}
