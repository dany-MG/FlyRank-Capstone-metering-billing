import os
import stripe
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.services.billing_services import upgrading_to_pro

router = APIRouter(prefix="/webhook", tags=["Webhook"])

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/stripe")
async def stripe_webhook(req: Request, db: Session = Depends(get_db)):
    payload = await req.body()
    sig_header = req.headers.get("stripe-signature")
    try:
        # Verify Stripe webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload")

    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    # Processing successful checkout session completed event
    if event["type"] == 'checkout.session.completed':
        session_data = event['data']['object']
        session_dict = session_data.to_dict()
        customer_id = session_dict.get('customer')

        if customer_id:
            upgrading_to_pro(db, customer_id)

    return {"status": "success"}