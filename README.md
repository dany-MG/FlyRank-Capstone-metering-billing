=======================================================================
# FLYRANK CAPSTONE: METERING & BILLING API

## 1. PROJECT DESCRIPTION
-----------------------------------------------------------------------
This project is a robust and scalable Metering & Billing API. It is 
designed to ingest usage events (such as API calls and AI tokens), 
enforce quota limits per Tenant, and calculate detailed costs at the 
end of the month. 

It includes a secure integration with Stripe webhooks to automate 
upgrades to higher-tier plans in real time.

Key features:
- Fault tolerance: Idempotency engine to prevent double counting.
- Logical quotas: Automatic rejection of requests over the limit (HTTP 429 / 402).
- Cost calculation: Precise financial breakdown based on AI token types.
- Secure payments: Cryptographic verification of Stripe signatures.


## 2. ARCHITECTURE DIAGRAM
-----------------------------------------------------------------------
The following shows the data flow between components:
`
                             +-----------------------+
                             |                       |
   [ POST /meter/event ] --->|    FASTAPI SERVER     |---> [ INSERT / UPDATE ]
                             |   (Logic & Quotas)    |           |
                             +-----------+-----------+           v
                                         ^              +-------------------+
                                         |              |                   |
   [ POST /webhooks/stripe] -------------+              |  POSTGRESQL (DB)  |
   (Verified Signature)                                 |                   |
                                                        +-------------------+
                             +-----------------------+           ^
                             |                       |           |
     [ Successful Payment ] >|     STRIPE CLOUD      |           |
                             |   (Billing Engine)    |           |
                             +-----------------------+           |
                                                                 |
   [ GET /invoice/{id} ] ----------------------------------------+
   (Mathematical roll-up)
`

## 3. SETUP INSTRUCTIONS
-----------------------------------------------------------------------
Follow these steps to set up the development environment locally:

STEP 1: Environment Variables
Create a file named `.env` in the root of the project and add the
following variables:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/metering_db
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here
```
STEP 2: Start the Database
Ensure you have Docker installed and running.
```bash
$ docker compose up -d
```

STEP 3: Virtual Environment and Installation
```bash
$ python -m venv .venv
$ source .venv/bin/activate  # (On Windows use: .venv\Scripts\activate)
$ pip install -r requirements.txt
```

STEP 4: Seed Initial Data
This will create the tables and add a Free plan and a test tenant.
```bash
$ python -m src.database.seed
```

STEP 5: Run the Server
```bash
$ uvicorn src.main:app --reload
```
The server will be available at `http://127.0.0.1:8000`
Swagger documentation at `http://127.0.0.1:8000/docs`


4. AUTOMATED TESTING
-----------------------------------------------------------------------
The project includes a test suite to validate idempotency, quota 
boundaries, financial calculations, and cryptographic security.

To run all tests, use the following command:
```bash
$ pytest test/test_billing.py -v
```

Test coverage:
- test_idempotency_prevents_double_counting: PASSED (100%)
- test_quota_limits_rejected: PASSED (100%)
- test_cost_calculation: PASSED (100%)
- test_stripe_webhook_rejects_invalid_signature: PASSED (100%)

=======================================================================