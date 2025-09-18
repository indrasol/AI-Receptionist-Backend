"""
Pydantic schemas for chunks table
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID

# Source type enum
SourceType = Literal["website", "file", "text"]

class ChunkBase(BaseModel):
    """Base chunk schema with common fields"""
    source_type: SourceType = Field(..., description="Type of source: website, file, or text")
    source_id: str = Field(..., max_length=500, description="Identifier of the source (URL, file_id, or text_id)")
    name: str = Field(..., max_length=200, description="Short, human-readable title for the chunk")
    description: Optional[str] = Field(None, description="Description of what this chunk is used for")
    content: str = Field(..., description="The actual cleaned text content of the chunk")
    bullets: Optional[List[str]] = Field(None, description="Array of key bullet points extracted from content")
    sample_questions: Optional[List[str]] = Field(None, description="Array of sample questions this chunk can answer")
    is_attached_to_assistant: bool = Field(False, description="Toggle for UI - whether chunk is attached to AI assistant")

class ChunkCreate(ChunkBase):
    """Schema for creating a new chunk"""
    organization_id: UUID = Field(..., description="Organization that owns this chunk")

class ChunkUpdate(BaseModel):
    """Schema for updating a chunk"""
    name: Optional[str] = Field(None, max_length=200, description="Short, human-readable title for the chunk")
    description: Optional[str] = Field(None, description="Description of what this chunk is used for")
    content: Optional[str] = Field(None, description="The actual cleaned text content of the chunk")
    bullets: Optional[List[str]] = Field(None, description="Array of key bullet points extracted from content")
    sample_questions: Optional[List[str]] = Field(None, description="Array of sample questions this chunk can answer")
    is_attached_to_assistant: Optional[bool] = Field(None, description="Toggle for UI - whether chunk is attached to AI assistant")

class ChunkDB(ChunkBase):
    """Schema for chunk as stored in database"""
    id: UUID = Field(..., description="Unique identifier for the chunk")
    organization_id: UUID = Field(..., description="Organization that owns this chunk")
    created_at: datetime = Field(..., description="Timestamp when chunk was created")
    updated_at: datetime = Field(..., description="Timestamp when chunk was last updated")
    created_by_user_id: Optional[UUID] = Field(None, description="User who created this chunk")

    class Config:
        from_attributes = True

class ChunkResponse(ChunkDB):
    """Schema for chunk API response"""
    pass

class ChunkListResponse(BaseModel):
    """Schema for chunk list API response"""
    chunks: List[ChunkResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class ChunkBulkCreate(BaseModel):
    """Schema for creating multiple chunks at once"""
    chunks: List[ChunkCreate]
    source_type: SourceType = Field(..., description="Type of source for all chunks")
    source_id: str = Field(..., max_length=500, description="Source identifier for all chunks")

class ChunkSearchRequest(BaseModel):
    """Schema for searching chunks"""
    query: str = Field(..., min_length=1, description="Search query")
    source_type: Optional[SourceType] = Field(None, description="Filter by source type")
    is_attached_to_assistant: Optional[bool] = Field(None, description="Filter by attachment status")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")

class ChunkSearchResponse(BaseModel):
    """Schema for chunk search response"""
    chunks: List[ChunkResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    query: str
