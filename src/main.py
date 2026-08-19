from fastapi import FastAPI
from src.api.routes import metering_route, webhook_route
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = FastAPI(
    title = "Usage Metering & Billing API",
    version = "1.0",
    description = "This API allows tenants to record their usage events and ensures that they do not exceed their allocated limits for API calls and AI tokens."
)

app.include_router(metering_route.router)
app.include_router(webhook_route.router)

@app.get("/health", tags=["Health Check"])
def health_check():
    """
    Health check endpoint to verify that the API is running.
    
    Returns a simple message indicating that the API is operational.
    """
    return {"status": "API is running"}