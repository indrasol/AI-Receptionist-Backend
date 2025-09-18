from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class DocumentProcessRequest(BaseModel):
    """Request schema for document processing"""
    pass  # File will be uploaded via multipart form

class DocumentProcessResponse(BaseModel):
    """Response schema for document processing"""
    message: str
    filename: str
    file_type: str
    file_size: int
    content_length: int
    chunks_generated: int
    chunks: List[Dict[str, Any]]

class DocumentInfo(BaseModel):
    """Document information schema"""
    filename: str
    file_type: str
    file_size: int
    content_length: int
    status: str

class DocumentChunkResponse(BaseModel):
    """Response schema for document chunk generation"""
    id: Optional[str] = None
    organization_id: str
    source_type: str = "document"
    source_id: str  # filename
    name: str
    description: str
    content: str
    bullets: List[str]
    sample_questions: List[str]
    is_attached_to_assistant: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_user_id: Optional[str] = None

class DocumentUploadResponse(BaseModel):
    """Response schema for document upload and processing"""
    message: str
    document_info: DocumentInfo
    chunks_generated: int
    chunks: List[DocumentChunkResponse]
    processing_time_seconds: float
