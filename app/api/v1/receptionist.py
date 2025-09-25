from fastapi import APIRouter, HTTPException, Depends
from app.schemas.lead import VapiVoicesResponse, VapiPhoneNumbersResponse
from app.schemas.phone_number import PhoneNumberResponse
from app.utils.auth import get_current_user
from app.database import get_supabase_client
from app.services.vapi_phone_sync_service import VapiPhoneSyncService
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import os
import httpx
from app.services.vapi_assistant import build_assistant_payload
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for VAPI phone sync
class VapiPhoneSyncResponse(BaseModel):
    """Response model for VAPI phone sync results"""
    success: bool
    message: str
    total_processed: int
    inserted: int
    updated: int
    skipped: int
    errors: List[str] = []


@router.get("/get_assistants", response_model=VapiVoicesResponse)
async def get_assistants(current_user: dict = Depends(get_current_user)):
    """
    Get list of available voice agents with their properties
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Returns:**
    - List of voice agents with properties like name, age, gender, accent, tone, personality
    
    **Raises:**
    - None (returns predefined data)

    Example Response:
    {
    "message": "Successfully fetched 10 voice agents",
    "voices": [
        {
            "display_name": "Alex",
            "age": "22",
            "gender": "male",
            "ethnicity": "white",
            "tone": "deeper tone",
            "personality": [
                "calming",
                "professional"
            ],
            "description": "22 year old white male with deeper tone, calming and professional"
        },
        {
            "display_name": "Maya",
            "age": "24",
            "gender": "male",
            "ethnicity": "white",
            "tone": "clear",
            "personality": [
                "energetic",
                "professional"
            ],
            "description": "24 year old white male, clear, energetic and professional"
        }
    ],
    "total_count": 10
    }
    """
    try:
        # Predefined list of voice agents with their properties
        voice_agents = [
            {
                "display_name": "Alex",
                "age": "22",
                "gender": "male",
                "ethnicity": "white",
                "tone": "deeper tone",
                "personality": ["calming", "professional"],
                "description": "22 year old white male with deeper tone, calming and professional"
            },
            {
                "display_name": "Maya",
                "age": "24",
                "gender": "male",
                "ethnicity": "white",
                "tone": "clear",
                "personality": ["energetic", "professional"],
                "description": "24 year old white male, clear, energetic and professional"
            },
            {
                "display_name": "Jordan",
                "age": "26",
                "gender": "female",
                "tone": "energetic",
                "personality": ["quippy", "lighthearted", "cheeky", "amused"],
                "description": "26 year old female, energetic, quippy, lighthearted, cheeky and amused"
            },
            {
                "display_name": "Priya",
                "age": "30",
                "gender": "female",
                "ethnicity": "indian",
                "personality": ["professional", "charming"],
                "description": "30 year old Indian female, professional and charming"
            },
            {
                "display_name": "Emma",
                "age": "23",
                "gender": "female",
                "ethnicity": "american",
                "description": "23 year old American female"
            },
            {
                "display_name": "Grace",
                "age": "25",
                "gender": "female",
                "ethnicity": "american",
                "accent": "southern accent",
                "description": "25 years old American female with southern accent"
            },
            {
                "display_name": "Sophie",
                "age": "26",
                "gender": "female",
                "ethnicity": "british",
                "accent": "british accent",
                "description": "26 year old British female with british accent"
            },
            {
                "display_name": "Lily",
                "age": "24",
                "gender": "female",
                "ethnicity": "australian",
                "accent": "australian accent",
                "description": "24 year old Australian female with australian accent"
            },
            {
                "display_name": "Zoe",
                "age": "28",
                "gender": "female",
                "ethnicity": "canadian",
                "accent": "canadian accent",
                "description": "28 year old Canadian female with canadian accent"
            },
            {
                "display_name": "Aria",
                "age": "27",
                "gender": "female",
                "ethnicity": "american",
                "description": "27 year old American female"
            }
        ]
        
        logger.info(f"Successfully fetched {len(voice_agents)} voice agents")
        
        return VapiVoicesResponse(
            message=f"Successfully fetched {len(voice_agents)} voice agents",
            assistants=voice_agents,
            total_count=len(voice_agents)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error fetching voice agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch voice agents: {str(e)}")


@router.get("/get_available_phoneNumber", response_model=VapiPhoneNumbersResponse)
async def get_available_phone_number(current_user: dict = Depends(get_current_user)):
    """
    Get list of available phone numbers that are not assigned to any assistant or workflow
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Returns:**
    - List of unassigned phone numbers that can be used for new assistants/workflows
    - Only returns numbers where assistant_id AND workflow_id are NULL
    
    **Raises:**
    - 400: If user has no organization
    - 500: If database query fails

    Example Response:
    {
        "message": "Successfully fetched 3 available phone numbers",
        "phone_numbers": [
            {
                "id": "ca76d992-58d8-4812-b43b-873fabf9a10c",
                "number": "+14242919395",
                "provider": "vapi",
                "status": "active",
                "name": null,
                "assistant_id": null,
                "provider_resource_id": "1efa2dca-42d8-4efe-9f3b-0b044b71f042",
                "twilio_account_sid": null,
                "workflow_id": null,
                "created_at": "2025-09-19T18:18:56.781Z",
                "updated_at": "2025-09-19T18:20:57.099Z"
            }
        ],
        "total_count": 3
    }
    """
    try:
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Query phone numbers from database - only return numbers not assigned to assistant or workflow
        response = supabase.table("phone_numbers").select("*").eq("status", "active").is_("assistant_id", None).is_("workflow_id", None).order("created_at", desc=False).execute()
        
        if not response.data:
            logger.warning(f"No available (unassigned) phone numbers found for organization {organization_id}")
            return VapiPhoneNumbersResponse(
                message="No available phone numbers found. All numbers are assigned to assistants or workflows.",
                phone_numbers=[],
                total_count=0
            )
        
        # Convert database records to API format
        phone_numbers = []
        for record in response.data:
            phone_number = {
                "id": record["vapi_id"],
                "number": record["number"],
                "provider": record["provider"],
                "status": record["status"],
                "name": record.get("name"),
                "assistant_id": record.get("assistant_id"),
                "provider_resource_id": record.get("provider_resource_id"),
                "twilio_account_sid": record.get("twilio_account_sid"),
                "workflow_id": record.get("workflow_id"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at")
            }
            phone_numbers.append(phone_number)
        
        logger.info(f"Successfully fetched {len(phone_numbers)} phone numbers for organization {organization_id}")
        
        return VapiPhoneNumbersResponse(
            message=f"Successfully fetched {len(phone_numbers)} available phone numbers",
            phone_numbers=phone_numbers,
            total_count=len(phone_numbers)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching phone numbers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch phone numbers: {str(e)}")


@router.post("/sync_vapi_phone_numbers", response_model=VapiPhoneSyncResponse)
async def sync_vapi_phone_numbers(current_user: dict = Depends(get_current_user)):
    """
    Sync phone numbers from VAPI API to our database
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **No Request Body Required**: This endpoint fetches phone numbers directly from VAPI API
    
    **Returns:**
    - Sync statistics including inserted, updated, and skipped counts
    
    **Raises:**
    - 400: If user has no organization or VAPI client not configured
    - 500: If VAPI API call or sync operation fails

    **Process:**
    1. Calls VAPI API using client.phone_numbers.list()
    2. Fetches all phone numbers for your VAPI account
    3. Syncs them to your organization's database
    4. Returns detailed sync statistics
    
    **Example Response:**
    {
        "success": true,
        "message": "Sync completed: 5 inserted, 3 updated, 0 skipped",
        "total_processed": 8,
        "inserted": 5,
        "updated": 3,
        "skipped": 0,
        "errors": []
    }
    """
    try:
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        user_id = current_user.get("sub")
        
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="User ID not found")
        
        logger.info(f"Starting VAPI phone number sync from API for organization {organization_id} by user {user_id}")
        
        # Initialize sync service
        sync_service = VapiPhoneSyncService()
        
        # Fetch from VAPI and sync to database
        sync_result = await sync_service.sync_phone_numbers_from_vapi(
            user_id=user_id,
            organization_id=organization_id
        )
        
        # Return response
        return VapiPhoneSyncResponse(
            success=sync_result["success"],
            message=sync_result.get("message", "Sync completed"),
            total_processed=sync_result["total_processed"],
            inserted=sync_result["inserted"],
            updated=sync_result["updated"],
            skipped=sync_result["skipped"],
            errors=sync_result.get("errors", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error syncing VAPI phone numbers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to sync phone numbers: {str(e)}")


async def _delete_vapi_assistant(assistant_id: str, vapi_key: str):
    """Best-effort delete of a Vapi assistant"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.delete(
                f"https://api.vapi.ai/assistant/{assistant_id}",
                headers={"Authorization": f"Bearer {vapi_key}"},
            )
    except Exception as e:  # nosec
        logger.warning(f"Failed to cleanup Vapi assistant {assistant_id}: {e}")


class ReceptionistCreateRequest(BaseModel):
    """Request payload for creating a new receptionist"""
    name: str
    description: Optional[str] = None
    assistant_voice: Optional[str] = None
    phone_number: Optional[str] = None

class ReceptionistResponse(BaseModel):
    """Response model after creating receptionist"""
    id: str
    org_id: str
    name: str
    description: Optional[str] = None
    assistant_voice: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ReceptionistListItem(BaseModel):
    id: str
    org_id: str
    name: str
    description: Optional[str] = None
    assistant_voice: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ReceptionistListResponse(BaseModel):
    message: str
    receptionists: List[ReceptionistListItem]
    total_count: int

VOICE_ID_MAP = {
    "Alex": "Cole",
    "Maya": "Harry",
    "Jordan": "Spencer",
    "Priya": "Neha",
    "Emma": "Kylie",
    "Grace": "Savannah",
    "Sophie": "Paige",
    "Arjun": "Rohan",
    "Luna": "Hana",
    "Max": "Elliot",
}

@router.post("/", response_model=ReceptionistResponse)
async def create_receptionist(
    payload: ReceptionistCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new receptionist for the current user's organization.

    **Authentication Required**: Include `Authorization: Bearer <token>` header

    **Body Parameters:**
    - `name` (str, required): Receptionist name
    - `description` (str, optional): Description of duties
    - `assistant_name` (str, optional): Selected assistant identifier
    - `phone_number` (str, optional): Selected phone number (e.164)

    **Returns:** Newly created receptionist record
    """
    try:
        # Ensure user has organization context
        org_id = current_user.get("organization", {}).get("id")
        print(f"org_id: {org_id}")
        if not org_id:
            raise HTTPException(status_code=400, detail="User does not belong to any organization")

        # 1. Create assistant in Vapi
        vapi_key = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
        if not vapi_key:
            raise HTTPException(status_code=500, detail="VAPI_KEY not configured in environment")

        org_name = current_user.get("organization", {}).get("name")
        if not org_name or org_name == "CSA":
            try:
                supabase_tmp = get_supabase_client()
                org_lookup = supabase_tmp.table("organizations").select("name").eq("id", org_id).single().execute()
                if org_lookup.data:
                    org_name = org_lookup.data["name"]
            except Exception:
                org_name = "Organization"

        voice_id = VOICE_ID_MAP.get(payload.assistant_voice, "spencer")

        assistant_payload = build_assistant_payload(org_name, payload.name, voice_id)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                vapi_res = await client.post(
                    "https://api.vapi.ai/assistant",
                    headers={
                        "Authorization": f"Bearer {vapi_key}",
                        "Content-Type": "application/json",
                    },
                    json=assistant_payload,
                )
            if vapi_res.status_code >= 400:
                logger.error(f"Vapi error {vapi_res.status_code}: {vapi_res.text}")
                raise HTTPException(status_code=500, detail="Failed to create assistant in Vapi")

            assistant_data = vapi_res.json()
            assistant_id = assistant_data.get("id")
        except Exception as e:
            logger.error(f"Error calling Vapi: {e}")
            raise HTTPException(status_code=500, detail="Failed to create assistant in Vapi")

        supabase = get_supabase_client()

        insert_data = {
            "org_id": org_id,
            "name": payload.name,
            "description": payload.description,
            "assistant_voice": payload.assistant_voice,
            "phone_number": payload.phone_number,
            "assistant_id": assistant_id,
        }

        try:
            res = supabase.table("receptionists").insert(insert_data).execute()
            if not res.data:
                raise ValueError("Failed to create receptionist record")
        except Exception as db_err:
            # Cleanup assistant in Vapi then propagate
            await _delete_vapi_assistant(assistant_id, vapi_key)
            logger.error(f"DB insert failed, cleaned Vapi assistant {assistant_id}: {db_err}")
            raise HTTPException(status_code=500, detail="Failed to create receptionist in database") from db_err

        # Link phone number -> assistant in Vapi and DB
        if payload.phone_number:
            phone_row = supabase.table("phone_numbers").select("id,vapi_id").eq("number", payload.phone_number).single().execute()
            if phone_row.data and phone_row.data.get("vapi_id"):
                vapi_phone_id = phone_row.data["vapi_id"]

                async def _link_phone():
                    await asyncio.sleep(3)
                    async with httpx.AsyncClient(timeout=30) as client:
                        await client.patch(
                            f"https://api.vapi.ai/phone-number/{vapi_phone_id}",
                            headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
                            json={"assistantId": assistant_id},
                        )
                    supabase.table("phone_numbers").update({"assistant_id": assistant_id}).eq("id", phone_row.data["id"]).execute()

                asyncio.create_task(_link_phone())

        return ReceptionistResponse(**res.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating receptionist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create receptionist: {str(e)}")

@router.get("/get_receptionists", response_model=ReceptionistListResponse)
async def get_receptionists(current_user: dict = Depends(get_current_user)):
    """Return all receptionists for the user's organization."""
    try:
        org_id = current_user.get("organization", {}).get("id")
        print(f"org_id12334: {org_id}")
        if not org_id:
            raise HTTPException(status_code=400, detail="User does not belong to any organization")

        supabase = get_supabase_client()
        res = (
            supabase.table("receptionists")
            .select("*")
            .eq("org_id", org_id)
            .eq("is_deleted", False)
            .order("created_at", desc=False)
            .execute()
        )

        receptionists = res.data or []
        return ReceptionistListResponse(
            message=f"Successfully fetched {len(receptionists)} receptionists",
            receptionists=receptionists,
            total_count=len(receptionists),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching receptionists: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch receptionists: {str(e)}")

class ReceptionistUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    assistant_voice: Optional[str] = None
    phone_number: Optional[str] = None


@router.patch("/{receptionist_id}", response_model=ReceptionistResponse)
async def update_receptionist(receptionist_id: str, payload: ReceptionistUpdateRequest, current_user: dict = Depends(get_current_user)):
    org_id = current_user.get("organization", {}).get("id")
    if not org_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    supabase = get_supabase_client()
    # fetch row
    rec_res = supabase.table("receptionists").select("*").eq("id", receptionist_id).eq("org_id", org_id).single().execute()
    if not rec_res.data:
        raise HTTPException(status_code=404, detail="Receptionist not found")

    rec = rec_res.data
    assistant_id = rec.get("assistant_id")

    # Build new assistant payload & patch Vapi
    vapi_key = os.getenv("AI_RECEPTION_VAPI_AUTH_TOKEN")
    voice_id = VOICE_ID_MAP.get(payload.assistant_voice or rec.get("assistant_voice"), "spencer")
    assistant_payload = build_assistant_payload(current_user["organization"]["name"], payload.name or rec["name"], voice_id)

    async with httpx.AsyncClient(timeout=30) as client:
        vapi_resp = await client.patch(
            f"https://api.vapi.ai/assistant/{assistant_id}",
            headers={"Authorization": f"Bearer {vapi_key}", "Content-Type": "application/json"},
            json=assistant_payload,
        )
    if vapi_resp.status_code >= 400:
        raise HTTPException(status_code=500, detail="Failed to update assistant in Vapi")

    # build update dict for DB
    update_dict = {k: v for k, v in {
        "name": payload.name,
        "description": payload.description,
        "assistant_voice": payload.assistant_voice,
        "phone_number": payload.phone_number,
    }.items() if v is not None}

    if update_dict:
        supabase.table("receptionists").update(update_dict).eq("id", receptionist_id).execute()

    final_row = supabase.table("receptionists").select("*").eq("id", receptionist_id).single().execute().data
    return ReceptionistResponse(**final_row)

class MessageResponse(BaseModel):
    message: str

@router.delete("/{receptionist_id}", response_model=MessageResponse)
async def delete_receptionist(receptionist_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a receptionist belonging to the user's organization."""
    try:
        org_id = current_user.get("organization", {}).get("id")
        if not org_id:
            raise HTTPException(status_code=400, detail="User does not belong to any organization")

        supabase = get_supabase_client()
        res = (
            supabase.table("receptionists")
            .update({"is_deleted": True})
            .eq("id", receptionist_id)
            .eq("org_id", org_id)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Receptionist not found or not allowed")

        return MessageResponse(message="Receptionist deleted")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting receptionist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete receptionist: {str(e)}")
