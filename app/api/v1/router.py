from fastapi import APIRouter
from app.api.v1 import contact, leads, auth, inbound, scraper, chunks, documents, receptionist

api_router = APIRouter()

# Include contact endpoint
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])
# Include leads endpoint
api_router.include_router(leads.router, prefix="/outbound", tags=["Outbound Management"])
# Include authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# Include inbound calls endpoints
api_router.include_router(inbound.router, prefix="/inbound", tags=["Inbound Calls Management"])
# Include web scraping endpoints
api_router.include_router(scraper.router, prefix="/scraper", tags=["Web Scraping"])
# Include chunks endpoints
api_router.include_router(chunks.router, prefix="/chunks", tags=["Chunks Management"])
# Include document processing endpoints
api_router.include_router(documents.router, prefix="/documents", tags=["Document Processing"])
# Include receptionist creation endpoints
api_router.include_router(receptionist.router, prefix="/create_receptionist", tags=["Receptionist Creation"])
# Include receptionist management endpoints
api_router.include_router(receptionist.router, prefix="/receptionists", tags=["Receptionist Management"]) 