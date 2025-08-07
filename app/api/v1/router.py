from fastapi import APIRouter
from app.api.v1 import contact, leads

api_router = APIRouter()

# Include contact endpoint
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])
# Include leads endpoint
api_router.include_router(leads.router, prefix="/leads", tags=["leads"]) 