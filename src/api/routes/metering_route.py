from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.services.billing_services import record_usage_event
from src.models.schemas import MeterEventInput, MeterEventOutput

router = APIRouter(prefix="/meter", tags="[Metering]")

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

    