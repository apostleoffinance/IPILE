from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.rate_limit import reset_rate_limits
from app.main import app
from app.models import (  # noqa: F401
    Account,
    AccountBalance,
    Alert,
    AllocationLine,
    AllocationRule,
    AllocationRun,
    Asset,
    AuditLog,
    Budget,
    BudgetCategory,
    Business,
    BusinessEmployee,
    BusinessTransaction,
    Category,
    FinancialScore,
    FinancialSnapshot,
    FundContribution,
    Goal,
    GoalContribution,
    Household,
    HouseholdInvite,
    HouseholdMember,
    ImportJob,
    IncomeSource,
    Investment,
    InvestmentTransaction,
    Liability,
    NetWorthSnapshot,
    Notification,
    Obligation,
    ObligationOccurrence,
    RecurringTransaction,
    Report,
    SchedulerTick,
    SessionToken,
    Simulation,
    SimulationRun,
    SinkingFund,
    SupportTicket,
    Transaction,
    User,
)

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _reset_limits() -> None:
    reset_rate_limits()


@pytest.fixture
def client() -> Iterator[TestClient]:
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def register(client: TestClient, email: str, name: str = "Owner") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "super-secret-12", "display_name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "super-secret-12"},
    )
    assert response.status_code == 200, response.text
