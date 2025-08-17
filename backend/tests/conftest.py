import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..app import app, dependencies
from ..app.db import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

class FakeLLM:
    def __init__(self, reply: str = "pong"):
        self.reply = reply

    def invoke(self, prompt: str) -> str:
        return self.reply


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _override_dependencies():
    app.dependency_overrides[dependencies.get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def llm(monkeypatch):
    fake = FakeLLM("hello")
    from ..app.services.chat_service import ChatService
    monkeypatch.setattr(ChatService, "__init__", lambda self, *a, **kw: None)
    monkeypatch.setattr(ChatService, "_llm", fake)
    monkeypatch.setattr(ChatService, "_cache", type("Dummy", (), {"get": lambda *_, **__: None, "set": lambda *_, **__: None})())
    return fake
