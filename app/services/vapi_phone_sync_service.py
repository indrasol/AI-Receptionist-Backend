import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.database import get_supabase_client
from app.config.settings import VAPI_AUTH_TOKEN
import requests
import json

logger = logging.getLogger(__name__)

class VapiPhoneSyncService:
    """Service for syncing phone numbers from VAPI to our database"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.vapi_base_url = "https://api.vapi.ai"
        self.vapi_headers = {
            "Authorization": f"Bearer {VAPI_AUTH_TOKEN}",
            "Content-Type": "application/json"
        } if VAPI_AUTH_TOKEN else None
    
    async def fetch_phone_numbers_from_vapi(self) -> List[Dict[str, Any]]:
        """
        Fetch phone numbers from VAPI API using HTTP requests
        
        Returns:
            List of phone numbers from VAPI
            
        Raises:
            Exception: If VAPI token is not configured or API call fails
        """
        try:
            if not self.vapi_headers:
                raise Exception("VAPI token not configured. Please check AI_RECEPTION_VAPI_AUTH_TOKEN")
            
            logger.info("Fetching phone numbers from VAPI API")
            
            # Make HTTP request to VAPI API
            url = f"{self.vapi_base_url}/phone-number"
            response = requests.get(url, headers=self.vapi_headers, timeout=30)
            
            # Check if request was successful
            if response.status_code != 200:
                error_msg = f"VAPI API request failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Parse JSON response
            try:
                phone_numbers_data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse VAPI API response as JSON: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Handle different response formats
            if isinstance(phone_numbers_data, list):
                phone_numbers = phone_numbers_data
            elif isinstance(phone_numbers_data, dict) and 'data' in phone_numbers_data:
                phone_numbers = phone_numbers_data['data']
            elif isinstance(phone_numbers_data, dict):
                # If it's a single phone number object, wrap it in a list
                phone_numbers = [phone_numbers_data]
            else:
                phone_numbers = []
            
            logger.info(f"Successfully fetched {len(phone_numbers)} phone numbers from VAPI")
            return phone_numbers
            
        except requests.exceptions.RequestException as e:
            error_msg = f"HTTP request to VAPI API failed: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to fetch phone numbers from VAPI: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def sync_phone_numbers_from_vapi(
        self, 
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Fetch phone numbers from VAPI API and sync to database
        
        Args:
            user_id: ID of the user performing the sync
            organization_id: Organization ID to associate with phone numbers
            
        Returns:
            Dict with sync statistics
        """
        try:
            # Fetch phone numbers from VAPI
            vapi_phone_numbers = await self.fetch_phone_numbers_from_vapi()
            
            # Sync to database
            return await self.sync_phone_numbers(vapi_phone_numbers, user_id, organization_id)
            
        except Exception as e:
            error_msg = f"Failed to sync phone numbers from VAPI: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "total_processed": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "errors": [error_msg]
            }
    
    async def sync_phone_numbers(
        self, 
        vapi_phone_numbers: List[Dict[str, Any]], 
        user_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Sync phone numbers from VAPI response to our database
        
        Args:
            vapi_phone_numbers: List of phone numbers from VAPI
            user_id: ID of the user performing the sync
            organization_id: Organization ID to associate with phone numbers
            
        Returns:
            Dict with sync statistics
        """
        try:
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            errors = []
            
            for vapi_phone in vapi_phone_numbers:
                try:
                    # Map VAPI response to our database structure
                    phone_data = self._map_vapi_to_db_format(vapi_phone, user_id, organization_id)
                    
                    # Check if phone number already exists by vapi_id
                    existing_response = self.supabase.table("phone_numbers").select("id, vapi_id").eq("vapi_id", phone_data["vapi_id"]).execute()
                    
                    if existing_response.data:
                        # Update existing record
                        update_data = {k: v for k, v in phone_data.items() if k not in ["id", "created_at", "created_by_user_id"]}
                        update_response = self.supabase.table("phone_numbers").update(update_data).eq("vapi_id", phone_data["vapi_id"]).execute()
                        
                        if update_response.data:
                            updated_count += 1
                            logger.info(f"Updated phone number {phone_data['number']} (VAPI ID: {phone_data['vapi_id']})")
                        else:
                            errors.append(f"Failed to update phone number {phone_data['number']}")
                    else:
                        # Insert new record
                        insert_response = self.supabase.table("phone_numbers").insert(phone_data).execute()
                        
                        if insert_response.data:
                            inserted_count += 1
                            logger.info(f"Inserted phone number {phone_data['number']} (VAPI ID: {phone_data['vapi_id']})")
                        else:
                            errors.append(f"Failed to insert phone number {phone_data['number']}")
                            
                except Exception as e:
                    error_msg = f"Error processing phone number {vapi_phone.get('number', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    skipped_count += 1
            
            # Return sync statistics
            result = {
                "success": True,
                "total_processed": len(vapi_phone_numbers),
                "inserted": inserted_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": errors,
                "message": f"Sync completed: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped"
            }
            
            logger.info(f"Phone number sync completed: {result['message']}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to sync phone numbers: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "total_processed": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "errors": [error_msg]
            }
    
    def _map_vapi_to_db_format(self, vapi_phone: Dict[str, Any], user_id: str, organization_id: str) -> Dict[str, Any]:
        """
        Map VAPI phone number response to our database format
        
        Args:
            vapi_phone: Single phone number from VAPI response
            user_id: User performing the sync
            organization_id: Organization ID
            
        Returns:
            Dict formatted for our database
        """
        # Just store the timestamps as strings - no parsing needed
        
        return {
            "vapi_id": vapi_phone["id"],
            "org_id": vapi_phone["orgId"],
            "number": vapi_phone["number"],
            "created_at": vapi_phone.get("createdAt"),
            "updated_at": vapi_phone.get("updatedAt"),
            "provider": vapi_phone["provider"],
            "status": vapi_phone.get("status", "active"),
            "provider_resource_id": vapi_phone.get("providerResourceId"),
            "assistant_id": vapi_phone.get("assistantId"),
            "twilio_account_sid": vapi_phone.get("twilioAccountSid"),
            "name": vapi_phone.get("name"),
            "workflow_id": vapi_phone.get("workflowId")
        }
    
    async def get_synced_phone_numbers(self, organization_id: str) -> List[Dict[str, Any]]:
        """
        Get all synced phone numbers for an organization
        
        Args:
            organization_id: Organization ID
            
        Returns:
            List of phone numbers from database
        """
        try:
            response = self.supabase.table("phone_numbers").select(
                "id, vapi_id, number, provider, status, name, assistant_id, "
                "provider_resource_id, twilio_account_sid, workflow_id, "
                "vapi_created_at, vapi_updated_at, created_at, updated_at"
            ).eq("organization_id", organization_id).eq("status", "active").order("vapi_created_at", desc=True).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Failed to get synced phone numbers: {str(e)}")
            return []
