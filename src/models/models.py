from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    api_calls_limit = Column(Integer, nullable=False)
    ai_tokens_limit = Column(Integer, nullable=False)

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    stripe_customer_id = Column(String, nullable=False, unique=True, index=True)
    
    plan = relationship("Plan")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), unique=True, nullable=False)
    status = Column(String, nullable=False)
    current_period_end = Column(DateTime, nullable=False)

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    usage_type = Column(String, nullable=False)  # 'api_calls' or 'ai_tokens'
    usage_amount = Column(Integer, nullable=False)
    idempotency_key = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    cached_tokens = Column(Integer, default=0)
    reasoning_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint('tenant_id', 'idempotency_key', name='uix_tenant_idempotency'),
    )
    