import pytest 
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database.database import get_db
from src.models.models import Base, Tenant, Plan

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    plan = Plan(id=1, api_calls_limit=100, ai_tokens_limit=10000)
    tenant = Tenant(id=1, plan_id=1, stripe_customer_id="cus_test_123")
    db.add(plan)
    db.add(tenant)
    db.commit()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


# ==========================
# Test Case 1: Idempotency Check
# ==========================
def test_idempotency_prevents_double_counting():
    payload = {
        "tenant_id": 1,
        "usage_type": "api_calls",
        "usage_amount": 10,
        "idempotency_key": "llave_unica_123"
    }

    # First request should succeed
    response1 = client.post("/meter/event", json=payload)
    assert response1.status_code == 200

    # Second request with the same idempotency key 
    response2 = client.post("/meter/event", json=payload)
    assert response2.status_code == 200

    usage_response = client.get("/meter/usage/1")
    assert usage_response.status_code == 200

    data = usage_response.json()
    assert data["api_calls"]["used"] == 10  # Should only count once

#==========================
# Test Case 2: Cuota Limit Enforcement
#==========================
def test_quota_limits_rejected():
    payload = {
        "tenant_id": 1,
        "usage_type": "api_calls",
        "usage_amount": 95,
        "idempotency_key": "llave_cuota_1"
    }
    response1 = client.post("/meter/event", json=payload)
    assert response1.status_code == 200

    payload["usage_amount"] = 10
    payload["idempotency_key"] = "llave_cuota_2"
    response2 = client.post("/meter/event", json=payload)

    assert response2.status_code == 429
    assert response2.json()["detail"] == "API calls limit exceeded"

#==========================
# Test Case 3: Cost Roll-up
#==========================
def test_cost_calculation():
    payload = {
        "tenant_id": 1,
        "usage_type": "ai_tokens",
        "usage_amount": 4000,
        "idempotency_key": "llave_costos_1",
        "token_breakdown": {
            "cached_input": 1000, # 1 millar * $0.05 = $0.05
            "reasoning": 2000,    # 2 millares * $0.30 = $0.60
            "output": 1000        # 1 millar * $0.15 = $0.15
        }
    }

    # Record the usage event
    post_response = client.post("/meter/event", json=payload)
    assert post_response.status_code == 200

    # Calculate the invoice
    invoice_response = client.get("/meter/invoice/1")
    assert invoice_response.status_code == 200

    invoice = invoice_response.json()

    # Calculate expected cost based on the breakdown
    assert invoice["total_due_usd"] == 0.80
    assert invoice["breakdown"]["cached_tokens_cost"] == 0.05
    assert invoice["breakdown"]["reasoning_tokens_cost"] == 0.60
    assert invoice["breakdown"]["output_tokens_cost"] == 0.15

# ==========================
# Test Case 4: Webhook Security (Stripe)
# ==========================
def test_stripe_webhook_rejects_invalid_signature():
    fake_payload = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_test_123"
            }
        }
    }
    response = client.post("/webhook/stripe", json=fake_payload)

    assert response.status_code == 400

