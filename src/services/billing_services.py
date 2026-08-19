from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from fastapi import HTTPException, status
from src.models.models import Tenant, UsageEvent
from src.models.schemas import MeterEventInput, MeterEventOutput

def record_usage_event(db: Session, event: MeterEventInput) -> MeterEventOutput:
    # Check if the tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == event.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    current_usage = db.query(func.sum(UsageEvent.usage_amount)).filter(
        UsageEvent.tenant_id  == event.tenant_id,
        UsageEvent.usage_type == event.usage_type
    ).scalar() or 0

    if event.usage_type == "api_calls" and (current_usage + event.usage_amount > tenant.plan.api_calls_limit):
        raise HTTPException(status_code = status.HTTP_429_TOO_MANY_REQUESTS, detail="API calls limit exceeded")

    elif event.usage_type == "ai_tokens" and (current_usage + event.usage_amount) > tenant.plan.ai_tokens_limit:
        raise HTTPException(status_code = status.HTTP_402_PAYMENT_REQUIRED, detail="AI tokens limit exceeded")
    
    else:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail="Invalid usage type")

    new_event = UsageEvent(
        tenant_id = event.tenant_id,
        usage_type = event.usage_type,
        usage_amount = event.usage_amount,
        idempotency_key = event.idempotency_key
    )
    db.add(new_event)

    try:
        db.commit()
        db.refresh(new_event)
        return MeterEventOutput(
            status = "success",
            message = "Usage event recorded successfully",
            event_id = new_event.id
        )
    except IntegrityError:
        db.rollback()
        return MeterEventOutput(
            status = "error",
            message = "Duplicate idempotency key. This event has already been recorded.",
            event_id = None
        )

