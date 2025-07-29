import pytest
import sys
import os
import datetime
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.db.base import Base
from app.api.deps import get_db
from app.core import security
from app.models.user import User
from app.models.token import Token

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    user = User(osu_user_id=12345, username="testuser")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user_with_token(db_session: Session, test_user: User) -> User:
    token = Token(
        owner_id=test_user.id,
        access_token="valid_access_token",
        refresh_token="valid_refresh_token",
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    )
    db_session.add(token)
    db_session.commit()
    db_session.refresh(test_user)
    return test_user


@pytest.fixture(scope="function")
def authenticated_client(db_session: Session, test_user_with_token: User):  # type: ignore
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    session_jwt = security.create_session_token(
        data={"sub": str(test_user_with_token.id)}
    )

    client = TestClient(app)
    client.headers = {"Authorization": f"Bearer {session_jwt}"}

    yield client  # type: ignore
    app.dependency_overrides.clear()
