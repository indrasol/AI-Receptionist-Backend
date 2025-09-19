from fastapi import APIRouter, HTTPException, Depends
from app.schemas.lead import VapiVoicesResponse, VapiPhoneNumbersResponse
from app.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
    Get list of available phone numbers for outbound calls
    
    **Authentication Required**: Include `Authorization: Bearer <token>` header
    
    **Returns:**
    - List of available phone numbers with their properties like number, provider, country, type
    
    **Raises:**
    - None (returns predefined data)

    Example Response:
    {
        "message": "Successfully fetched 5 available phone numbers",
        "phone_numbers": [
            {
                "id": "phone_001",
                "number": "+1-555-0123",
                "provider": "Twilio",
                "country": "US",
                "country_code": "+1",
                "type": "local",
                "area_code": "555",
                "status": "active",
                "description": "US local number for general outbound calls"
            }
        ],
        "total_count": 5
    }
    """
    try:
        # Predefined list of available phone numbers
        phone_numbers = [
            {
                "id": "phone_001",
                "number": "+1-555-123-6186",
                "provider": "Twilio",
                "country": "US",
                "country_code": "+1",
                "status": "active",
                "description": "US local number for general outbound calls"
            },
            {
                "id": "phone_002", 
                "number": "+1-555-123-6186",
                "provider": "Twilio",
                "country": "US",
                "country_code": "+1",
                "status": "active",
                "description": "US local number for sales calls"
            },
            {
                "id": "phone_003",
                "number": "+1-555-123-6186",
                "provider": "Twilio", 
                "country": "US",
                "country_code": "+1",
                "status": "active",
                "description": "US toll-free number for customer support"
            },
            {
                "id": "phone_004",
                "number": "+1-555-123-6186",
                "provider": "Twilio",
                "country": "UK",
                "country_code": "+44",
                "status": "active",
                "description": "UK London number for international calls"
            },
            {
                "id": "phone_005",
                "number": "+1-555-123-6186",
                "provider": "Twilio",
                "country": "US", 
                "country_code": "+1",
                "status": "active",
                "description": "US local number for marketing campaigns"
            }
        ]
        
        logger.info(f"Successfully fetched {len(phone_numbers)} available phone numbers")
        
        return VapiPhoneNumbersResponse(
            message=f"Successfully fetched {len(phone_numbers)} available phone numbers",
            phone_numbers=phone_numbers,
            total_count=len(phone_numbers)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error fetching available phone numbers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch available phone numbers: {str(e)}")
