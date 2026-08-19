from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.services.billing_services import record_usage_event, get_usage_summary
from src.models.schemas import MeterEventInput, MeterEventOutput, UsageSummary

router = APIRouter(prefix="/meter", tags=["Metering"])

@router.post("/event", response_model = MeterEventOutput)
def meter_usage(event: MeterEventInput, db: Session = Depends(get_db)):
    """
    Record a usage event for a tenant. This endpoint ensures that the usage event is recorded only once per unique idempotency key.
    
    - **tenant_id**: The unique identifier of the tenant.
    - **usage_type**: The type of usage event. Must be either 'api_calls' or 'ai_tokens'.
    - **usage_amount**: The quantity of the usage event. Must be a positive integer.
    - **idempotency_key**: A unique key to ensure idempotency of the request.
    
    Returns a success message with the event ID if the event is recorded successfully, or an error message if the idempotency key has already been used.
    """
    return record_usage_event(db, event)

@router.get("/usage/{tenant_id}", response_model = UsageSummary)
def get_usage(tenant_id: int, db:Session = Depends(get_db)):
    """
    Retrieve the current usage summary for a specific tenant.
    
    - **tenant_id**: The unique identifier of the tenant.
    
    Returns the total API calls and AI tokens used by the tenant, along with their respective limits based on the tenant's plan.
    """
    return get_usage_summary(db, tenant_id)