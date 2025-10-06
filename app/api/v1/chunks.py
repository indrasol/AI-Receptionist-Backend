"""
API endpoints for managing chunks
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from app.schemas.chunk import (
    ChunkCreate, ChunkUpdate, ChunkResponse, ChunkListResponse,
    ChunkBulkCreate, ChunkSearchRequest, ChunkSearchResponse,
    ChunkBatchToggleRequest, ChunkBatchToggleResponse
)
from app.utils.auth import get_current_user
from app.database_operations import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chunks Management"])

@router.get("/chunks", response_model=ChunkListResponse)
async def get_chunks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(2000, ge=1, le=100, description="Number of items per page"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    receptionist_id: Optional[str] = Query(None, description="Filter by receptionist"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get chunks for the current user's organization
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (max 100)
    - **source_type**: Filter by source type (website, file, text)
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Build query
        query = supabase.table("chunks").select("*", count="exact")
        query = query.eq("organization_id", organization_id)
        query = query.eq("deleted", False)  # Exclude deleted chunks
        
        # Apply filters
        if source_type:
            query = query.eq("source_type", source_type)

        if receptionist_id:
            query = query.eq("receptionist_id", receptionist_id)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)
        
        # Order by created_at desc
        query = query.order("created_at", desc=True)
        
        result = query.execute()
        
        if not result.data:
            result.data = []
        
        total = result.count or 0
        total_pages = (total + page_size - 1) // page_size
        
        logger.info(f"Retrieved {len(result.data)} chunks for organization {organization_id}")
        
        return ChunkListResponse(
            chunks=[ChunkResponse(**chunk) for chunk in result.data],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error retrieving chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunks: {str(e)}")

@router.get("/chunks/{chunk_id}", response_model=ChunkResponse)
async def get_chunk(
    chunk_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific chunk by ID
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Get chunk
        result = supabase.table("chunks").select("*").eq("id", chunk_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return ChunkResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chunk {chunk_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chunk: {str(e)}")

@router.put("/chunks/{chunk_id}", response_model=ChunkResponse)
async def update_chunk(
    chunk_id: UUID,
    chunk_data: ChunkUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a chunk and sync with VAPI if it has a vapi_file_id
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Get existing chunk to check for vapi_file_id
        existing = supabase.table("chunks").select("*").eq("id", chunk_id).eq("organization_id", organization_id).single().execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Update chunk in database
        update_data = {k: v for k, v in chunk_data.model_dump().items() if v is not None}
        
        result = supabase.table("chunks").update(update_data).eq("id", chunk_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        updated_chunk = result.data[0]
        
        # If chunk has vapi_file_id, we need to update the file in VAPI
        vapi_file_id = existing.data.get("vapi_file_id")
        if vapi_file_id:
            try:
                from app.services.vapi_assistant import delete_file_from_vapi, upload_chunk_to_vapi, sync_assistant_prompt
                
                # Delete old file from VAPI
                await delete_file_from_vapi(vapi_file_id)
                
                # Upload new version to VAPI
                new_vapi_file_id = await upload_chunk_to_vapi(
                    str(chunk_id),
                    updated_chunk.get('name', 'Unnamed Chunk'),
                    updated_chunk.get('content', ''),
                    bullets=updated_chunk.get('bullets', []),
                    sample_questions=updated_chunk.get('sample_questions', [])
                )
                
                # Update vapi_file_id in database
                if new_vapi_file_id:
                    supabase.table("chunks").update({"vapi_file_id": new_vapi_file_id}).eq("id", chunk_id).execute()
                    updated_chunk['vapi_file_id'] = new_vapi_file_id
                    logger.info(f"Updated VAPI file for chunk {chunk_id}")
                    
                    # Sync assistant if receptionist_id exists
                    receptionist_id = updated_chunk.get('receptionist_id')
                    if receptionist_id:
                        rec_row = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).single().execute()
                        assistant_id = rec_row.data.get("assistant_id") if rec_row.data else None
                        if assistant_id:
                            await sync_assistant_prompt(assistant_id, receptionist_id)
                            
            except Exception as vapi_error:
                logger.warning(f"Failed to update VAPI file: {str(vapi_error)}")
                # Continue - database update was successful
        
        logger.info(f"Updated chunk {chunk_id}")
        return ChunkResponse(**updated_chunk)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chunk {chunk_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update chunk: {str(e)}")

@router.delete("/chunks/{chunk_id}")
async def delete_chunk(
    chunk_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete a chunk - marks it as deleted and removes from VAPI
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Get chunk to check for vapi_file_id
        existing = supabase.table("chunks").select("*").eq("id", chunk_id).eq("organization_id", organization_id).single().execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        vapi_file_id = existing.data.get("vapi_file_id")
        receptionist_id = existing.data.get("receptionist_id")
        
        # Delete file from VAPI if it exists
        if vapi_file_id:
            try:
                from app.services.vapi_assistant import delete_file_from_vapi, sync_assistant_prompt
                await delete_file_from_vapi(vapi_file_id)
                logger.info(f"Deleted VAPI file {vapi_file_id} for chunk {chunk_id}")
            except Exception as vapi_error:
                logger.warning(f"Failed to delete VAPI file: {str(vapi_error)}")
                # Continue with soft delete anyway
        
        # Soft delete: mark as deleted and clear vapi_file_id
        result = supabase.table("chunks").update({
            "deleted": True,
            "vapi_file_id": None
        }).eq("id", chunk_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        # Sync assistant to remove from knowledge base
        if receptionist_id:
            try:
                from app.services.vapi_assistant import sync_assistant_prompt
                rec_row = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).single().execute()
                assistant_id = rec_row.data.get("assistant_id") if rec_row.data else None
                if assistant_id:
                    await sync_assistant_prompt(assistant_id, receptionist_id)
                    logger.info(f"Synced assistant after deleting chunk {chunk_id}")
            except Exception as sync_error:
                logger.warning(f"Failed to sync assistant: {str(sync_error)}")
        
        logger.info(f"Soft deleted chunk {chunk_id}")
        return {"message": "Chunk deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chunk {chunk_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete chunk: {str(e)}")

@router.post("/chunks/bulk", response_model=List[ChunkResponse])
async def create_chunks_bulk(
    bulk_data: ChunkBulkCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create multiple chunks at once
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Prepare chunks data
        chunks_data = []
        for chunk in bulk_data.chunks:
            chunk_dict = chunk.model_dump()
            chunk_dict["organization_id"] = organization_id
            chunk_dict["receptionist_id"] = bulk_data.receptionist_id
            chunk_dict["created_by_user_id"] = None  # Skip user tracking for now due to foreign key constraint
            chunks_data.append(chunk_dict)
        
        # Insert chunks
        result = supabase.table("chunks").insert(chunks_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create chunks")
        
        logger.info(f"Created {len(result.data)} chunks for organization {organization_id}")
        return [ChunkResponse(**chunk) for chunk in result.data]
        
    except Exception as e:
        logger.error(f"Error creating chunks in bulk: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create chunks: {str(e)}")

@router.post("/chunks/search", response_model=ChunkSearchResponse)
async def search_chunks(
    search_request: ChunkSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Search chunks by content, name, or description
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Build search query
        query = supabase.table("chunks").select("*", count="exact")
        query = query.eq("organization_id", organization_id)
        query = query.eq("deleted", False)  # Exclude deleted chunks
        
        # Text search (PostgreSQL full-text search)
        query = query.or_(f"name.ilike.%{search_request.query}%,description.ilike.%{search_request.query}%,content.ilike.%{search_request.query}%")
        
        # Apply filters
        if search_request.source_type:
            query = query.eq("source_type", search_request.source_type)
        
        # Apply pagination
        offset = (search_request.page - 1) * search_request.page_size
        query = query.range(offset, offset + search_request.page_size - 1)
        
        # Order by created_at desc
        query = query.order("created_at", desc=True)
        
        result = query.execute()
        
        if not result.data:
            result.data = []
        
        total = result.count or 0
        total_pages = (total + search_request.page_size - 1) // search_request.page_size
        
        logger.info(f"Found {len(result.data)} chunks matching '{search_request.query}' for organization {organization_id}")
        
        return ChunkSearchResponse(
            chunks=[ChunkResponse(**chunk) for chunk in result.data],
            total=total,
            page=search_request.page,
            page_size=search_request.page_size,
            total_pages=total_pages,
            query=search_request.query
        )
        
    except Exception as e:
        logger.error(f"Error searching chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search chunks: {str(e)}")


@router.post("/chunks/batch-toggle", response_model=ChunkBatchToggleResponse)
async def batch_toggle_chunks(
    request: ChunkBatchToggleRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Batch toggle chunk attachments - attach or detach multiple chunks from VAPI assistant.
    
    Logic:
    - If is_attached=true and no vapi_file_id: Upload to VAPI and set vapi_file_id
    - If is_attached=false and has vapi_file_id: Delete from VAPI and clear vapi_file_id
    - Updates database and syncs assistant after all changes
    """
    try:
        from app.services.vapi_assistant import upload_chunk_to_vapi, delete_file_from_vapi, sync_assistant_prompt
        
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        updated_count = 0
        attached_count = 0
        detached_count = 0
        failed_chunks = []
        
        # Process each chunk
        for toggle_item in request.chunks:
            try:
                chunk_id = str(toggle_item.chunk_id)
                is_attached = toggle_item.is_attached
                
                # Get chunk from database
                chunk_result = supabase.table("chunks").select("*").eq("id", chunk_id).eq("organization_id", organization_id).eq("deleted", False).single().execute()
                
                if not chunk_result.data:
                    logger.warning(f"Chunk {chunk_id} not found or deleted")
                    failed_chunks.append(chunk_id)
                    continue
                
                chunk = chunk_result.data
                current_vapi_file_id = chunk.get("vapi_file_id")
                
                # Case 1: Attach (toggle ON) - need to upload if no vapi_file_id
                if is_attached and not current_vapi_file_id:
                    # Upload to VAPI
                    vapi_file_id = await upload_chunk_to_vapi(
                        chunk_id,
                        chunk.get('name', 'Unnamed Chunk'),
                        chunk.get('content', ''),
                        bullets=chunk.get('bullets', []),
                        sample_questions=chunk.get('sample_questions', [])
                    )
                    
                    if vapi_file_id:
                        # Update database with vapi_file_id
                        supabase.table("chunks").update({"vapi_file_id": vapi_file_id}).eq("id", chunk_id).execute()
                        attached_count += 1
                        updated_count += 1
                        logger.info(f"Attached chunk {chunk_id} to VAPI with file_id {vapi_file_id}")
                    else:
                        logger.warning(f"Failed to upload chunk {chunk_id} to VAPI")
                        failed_chunks.append(chunk_id)
                
                # Case 2: Detach (toggle OFF) - need to delete if has vapi_file_id
                elif not is_attached and current_vapi_file_id:
                    # Delete from VAPI
                    success = await delete_file_from_vapi(current_vapi_file_id)
                    
                    if success:
                        # Clear vapi_file_id in database
                        supabase.table("chunks").update({"vapi_file_id": None}).eq("id", chunk_id).execute()
                        detached_count += 1
                        updated_count += 1
                        logger.info(f"Detached chunk {chunk_id} from VAPI, removed file_id {current_vapi_file_id}")
                    else:
                        logger.warning(f"Failed to delete chunk {chunk_id} from VAPI")
                        failed_chunks.append(chunk_id)
                
                # Case 3: No action needed (already in desired state)
                else:
                    logger.info(f"Chunk {chunk_id} already in desired state (attached={is_attached})")
                    
            except Exception as chunk_error:
                logger.error(f"Error processing chunk {toggle_item.chunk_id}: {str(chunk_error)}")
                failed_chunks.append(str(toggle_item.chunk_id))
        
        # Sync assistant after all changes
        try:
            rec_row = supabase.table("receptionists").select("assistant_id").eq("id", request.receptionist_id).single().execute()
            assistant_id = rec_row.data.get("assistant_id") if rec_row.data else None
            if assistant_id:
                await sync_assistant_prompt(assistant_id, str(request.receptionist_id))
                logger.info(f"Synced assistant {assistant_id} after batch toggle")
        except Exception as sync_error:
            logger.warning(f"Failed to sync assistant: {str(sync_error)}")
        
        message = f"Batch toggle completed: {updated_count} chunks updated ({attached_count} attached, {detached_count} detached)"
        if failed_chunks:
            message += f", {len(failed_chunks)} failed"
        
        logger.info(message)
        
        return ChunkBatchToggleResponse(
            message=message,
            updated_count=updated_count,
            attached_count=attached_count,
            detached_count=detached_count,
            failed_chunks=failed_chunks
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch toggle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to batch toggle chunks: {str(e)}")
