"""
API endpoints for managing chunks
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID

from app.schemas.chunk import (
    ChunkCreate, ChunkUpdate, ChunkResponse, ChunkListResponse,
    ChunkBulkCreate, ChunkSearchRequest, ChunkSearchResponse
)
from app.utils.auth import get_current_user
from app.database_operations import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chunks Management"])

@router.get("/chunks", response_model=ChunkListResponse)
async def get_chunks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    is_attached_to_assistant: Optional[bool] = Query(None, description="Filter by attachment status"),
    receptionist_id: Optional[str] = Query(None, description="Filter by receptionist"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get chunks for the current user's organization
    
    - **page**: Page number (starts from 1)
    - **page_size**: Number of items per page (max 100)
    - **source_type**: Filter by source type (website, file, text)
    - **is_attached_to_assistant**: Filter by attachment status
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
        
        # Apply filters
        if source_type:
            query = query.eq("source_type", source_type)
        if is_attached_to_assistant is not None:
            query = query.eq("is_attached_to_assistant", is_attached_to_assistant)

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
    Update a chunk
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Update chunk
        update_data = {k: v for k, v in chunk_data.model_dump().items() if v is not None}
        
        result = supabase.table("chunks").update(update_data).eq("id", chunk_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        logger.info(f"Updated chunk {chunk_id}")
        return ChunkResponse(**result.data[0])
        
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
    Delete a chunk
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Delete chunk
        result = supabase.table("chunks").delete().eq("id", chunk_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        logger.info(f"Deleted chunk {chunk_id}")
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
            chunk_dict["created_by_user_id"] = current_user.get("id")
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
        
        # Text search (PostgreSQL full-text search)
        query = query.or_(f"name.ilike.%{search_request.query}%,description.ilike.%{search_request.query}%,content.ilike.%{search_request.query}%")
        
        # Apply filters
        if search_request.source_type:
            query = query.eq("source_type", search_request.source_type)
        if search_request.is_attached_to_assistant is not None:
            query = query.eq("is_attached_to_assistant", search_request.is_attached_to_assistant)
        
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

@router.put("/chunks/{chunk_id}/toggle-attachment")
async def toggle_chunk_attachment(
    chunk_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """
    Toggle the is_attached_to_assistant status of a chunk
    """
    try:
        supabase = get_supabase_client()
        
        # Get user's organization
        organization_id = current_user.get("organization", {}).get("id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="User has no organization")
        
        # Get current chunk
        result = supabase.table("chunks").select("is_attached_to_assistant").eq("id", chunk_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        current_status = result.data[0]["is_attached_to_assistant"]
        new_status = not current_status
        
        # Update chunk
        result = supabase.table("chunks").update({"is_attached_to_assistant": new_status}).eq("id", chunk_id).eq("organization_id", organization_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        logger.info(f"Toggled chunk {chunk_id} attachment status to {new_status}")
        return {"message": f"Chunk attachment status updated to {new_status}", "is_attached_to_assistant": new_status}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling chunk {chunk_id} attachment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle chunk attachment: {str(e)}")
