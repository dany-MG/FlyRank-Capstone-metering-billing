from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from fastapi import HTTPException, status
from src.models.models import Tenant, UsageEvent
from src.models.schemas import MeterEventInput, MeterEventOutput
from src.core.pricing import PRICES

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
    
    breakdown = event.token_breakdown

    new_event = UsageEvent(
        tenant_id = event.tenant_id,
        usage_type = event.usage_type,
        usage_amount = event.usage_amount,
        idempotency_key = event.idempotency_key,
        cached_tokens = event.token_breakdown.cached_input if breakdown else 0,
        reasoning_tokens = event.token_breakdown.reasoning if breakdown else 0,
        output_tokens = event.token_breakdown.output if breakdown else 0
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
        existing_event = db.query(UsageEvent).filter(
            UsageEvent.idempotency_key == event.idempotency_key
        ).first()
        return MeterEventOutput(
            status = "error",
            message = "Duplicate idempotency key. This event has already been recorded.",
            event_id = existing_event.id if existing_event else None
        )


def get_usage_summary(db: Session, tenant_id: int) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    
    api_calls_used = db.query(func.sum(UsageEvent.usage_amount)).filter(
        UsageEvent.tenant_id == tenant_id,
        UsageEvent.usage_type == "api_calls"
    ).scalar() or 0

    ai_tokens_used = db.query(func.sum(UsageEvent.usage_amount)).filter(
        UsageEvent.tenant_id == tenant_id,
        UsageEvent.usage_type == "ai_tokens"
    ).scalar() or 0

    cached_used = db.query(func.sum(UsageEvent.cached_tokens)).filter(UsageEvent.tenant_id == tenant_id).scalar() or 0
    reasoning_used = db.query(func.sum(UsageEvent.reasoning_tokens)).filter(UsageEvent.tenant_id == tenant_id).scalar() or 0
    output_used = db.query(func.sum(UsageEvent.output_tokens)).filter(UsageEvent.tenant_id == tenant_id).scalar() or 0

    return {
        "tenant_id": tenant.id,
        "plan_id": tenant.plan_id,
        "api_calls": {
            "used": api_calls_used,
            "limit": tenant.plan.api_calls_limit
        },
        "ai_tokens": {
            "used": ai_tokens_used,
            "limit": tenant.plan.ai_tokens_limit,
            "cached_used": cached_used,
            "reasoning_used": reasoning_used,
            "output_used": output_used
        }
    }

def upgrading_to_pro(db: Session, stipe_customer_id: str):
    tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == stipe_customer_id).first()
    if not tenant:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if tenant:
        tenant.plan_id = 2  # Assuming plan_id 2 corresponds to the Pro plan
        db.commit()
        return True
    return False

def calculate_monthly_pricing(db: Session, tenant_id: int) -> dict:
    api_calls = db.query(func.sum(UsageEvent.usage_amount)).filter(
        UsageEvent.tenant_id == tenant_id,
        UsageEvent.usage_type == "api_calls"
    ).scalar() or 0

    cached_tokens = db.query(func.sum(UsageEvent.cached_tokens)).filter(
        UsageEvent.tenant_id == tenant_id
    ).scalar() or 0
    
    reasoning_tokens = db.query(func.sum(UsageEvent.reasoning_tokens)).filter(
        UsageEvent.tenant_id == tenant_id
    ).scalar() or 0
    
    output_tokens = db.query(func.sum(UsageEvent.output_tokens)).filter(
        UsageEvent.tenant_id == tenant_id
    ).scalar() or 0

    cost_api = (api_calls / 1000) * PRICES["api_calls"]
    cost_cached = (cached_tokens / 1000) * PRICES["ai_input_cached"]
    cost_reasoning = (reasoning_tokens / 1000) * PRICES["ai_reasoning"]
    cost_output = (output_tokens / 1000) * PRICES["ai_output"]
    total_cost = cost_api + cost_cached + cost_reasoning + cost_output

    return {
        "tenant_id": tenant_id,
        "breakdown": {
            "api_calls_cost": round(cost_api, 4),
            "cached_tokens_cost": round(cost_cached, 4),
            "reasoning_tokens_cost": round(cost_reasoning, 4),
            "output_tokens_cost": round(cost_output, 4)
        },
        "total_due_usd" : round(total_cost, 4)
    }
