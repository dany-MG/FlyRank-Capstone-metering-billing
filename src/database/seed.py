from src.database.database import SessionLocal
from src.models.models import Tenant, Plan
from sqlalchemy.exc import IntegrityError

def seed_database():
    db = SessionLocal()
    try:
        # Create plans
        free_plan = Plan(id=1, api_calls_limit=1000, ai_tokens_limit=10000)
        pro_plan = Plan(id=2, api_calls_limit=10000, ai_tokens_limit=100000)
        db.add(free_plan)
        db.add(pro_plan)
        
        
        tenant_test = Tenant(id=1, plan_id=1, stripe_customer_id="cus_V6ENwelBDFzjj2")
        db.add(tenant_test)
        db.commit()
        print("Database seeded successfully.")
    except IntegrityError:
        db.rollback()
        print("Database already seeded. Skipping.")
    finally:
        db.close()
    

if __name__ == "__main__":
    seed_database()