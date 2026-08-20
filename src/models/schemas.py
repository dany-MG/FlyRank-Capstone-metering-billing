from typing import Optional
from pydantic import BaseModel, Field

class TokenBreakdown(BaseModel):
    cached_input: int = Field(..., description="The number of cached input tokens used.")
    reasoning : int = Field(..., description="The number of reasoning tokens used.")
    output : int = Field(..., description="The number of output tokens used.")

class MeterEventInput(BaseModel):
    tenant_id: int = Field(..., description ="The unique identifier of the tenant.")
    usage_type : str = Field(..., pattern= "^(api_calls|ai_tokens)$", description="The type of usage event. Must be either 'api_calls' or 'ai_tokens'.")
    usage_amount : int = Field(..., gt=0, description="The quantity of the usage event. Must be a positive integer.")
    idempotency_key : str = Field(..., description="A unique key to ensure idempotency of the request.")
    token_breakdown : Optional[TokenBreakdown] = None

class MeterEventOutput(BaseModel):
    status : str
    message : str
    event_id : Optional[int] = None

class UsageDetail(BaseModel):
    used: int
    limit: int

class AITokenUsageDetail(BaseModel):
    used: int
    limit: int
    cached_used: int
    reasoning_used: int
    output_used: int

class UsageSummary(BaseModel):
    tenant_id: int
    plan_id: int
    api_calls: UsageDetail
    ai_tokens: AITokenUsageDetail

