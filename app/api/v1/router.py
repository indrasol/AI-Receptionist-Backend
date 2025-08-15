from fastapi import APIRouter
from app.api.v1 import contact, leads, auth

api_router = APIRouter()

# Include contact endpoint
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])
# Include leads endpoint
api_router.include_router(leads.router, prefix="/outbound", tags=["Outbound Management"])
# Include authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"]) 