# Phase 1: Design Document
# 1. The Problem and Non-Goals

Problem: Build a usage ingestion and billing engine that answers three core questions: How much has the customer used?, How much should they pay?, and Have they reached their plan limits? The system must be resilient to network retries without double-charging (idempotency) and integrate Stripe's API in test mode.

Explicit Non-Goal: This system will NOT handle overage billing, mid-cycle plan upgrade prorations, or PDF invoice generation. We are keeping the scope strictly limited to the core capstone requirements.

# 2. Data Model (PostgreSQL)
We will use 4 main tables to maintain strict data isolation (multi-tenant architecture):

`plans`: Defines the subscription tiers (Free, Pro) and their respective monthly quotas (api_calls_limit, ai_tokens_limit).

`tenants`: Represents the organizations/customers. It holds a foreign key to their current plan and stores their stripe_customer_id.

`subscriptions`: Tracks the current payment status (e.g., active, canceled) and the billing cycle dates.

`usage_events`: The most critical table. It acts as an append-only ledger recording every billable action. Columns include: tenant_id, type (api_call or ai_token), quantity, timestamp, and idempotency_key.

# 3. API Surface (The Contract)

`POST /meter`: Receives a billable action (e.g., 2,500 tokens used).

Behavior: Evaluates current usage against the quota limit. If allowed, it persists the event and returns 200 OK. If the quota is exceeded, it rejects the request with a `429 Too Many Requests` or `402 Payment Required` status code, including a clear explanation.

`GET /usage`: Rolls up the tenant's current usage. It calculates and returns the consumed quantities, the plan limits, and the total monetary cost applying the specific AI-token pricing rules.

`POST /webhooks/stripe`: A secure endpoint that verifies Stripe signatures and listens for checkout completion events to automatically upgrade the tenant's plan/subscription status.

4. Idempotency Strategy
The non-negotiable core requirement to prevent double-charging during network retries.

Database Level: We will enforce a composite unique constraint (Unique Index) on the usage_events table using (tenant_id, idempotency_key).

Application Flow: If a POST /meter request arrives with an idempotency_key that already exists for a given tenant, the database will reject the INSERT. Instead of throwing an unhandled 500 Internal Server Error, the API logic will catch the constraint violation and gracefully return a 200 OK with the original success response, safely and silently ignoring the duplicate event.