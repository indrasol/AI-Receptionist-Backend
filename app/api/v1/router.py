from fastapi import APIRouter
from app.api.v1 import contact

api_router = APIRouter()

# Include contact endpoint
api_router.include_router(contact.router, prefix="/contact", tags=["contact"]) 