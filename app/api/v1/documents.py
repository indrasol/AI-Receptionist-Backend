import logging
import time
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from app.schemas.document import DocumentUploadResponse, DocumentInfo, DocumentChunkResponse, TextInputRequest
from app.services.document_service import DocumentProcessingService
from app.services.openai_service import OpenAIService
from app.utils.auth import get_current_user
from app.database import get_supabase_client
from app.schemas.auth import UserResponse as User
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Response model for text processing
class TextProcessingResponse(BaseModel):
    message: str
    chunks_generated: int
    chunks: List[Dict[str, Any]]
    processing_time_seconds: float

@router.post("/process-document", response_model=DocumentUploadResponse)
async def process_document(
    file: UploadFile = File(..., description="Document file to process (PDF, DOCX, TXT, CSV)"),
    receptionist_id: str = Form(None, description="Optional receptionist ID to associate chunks with"),
    current_user: User = Depends(get_current_user)
):
    """
    Process a document file and generate chunks using OpenAI
    
    **Supported file types:**
    - PDF (.pdf)
    - Word documents (.docx)
    - Text files (.txt)
    - CSV files (.csv)
    
    **Process:**
    1. Upload document file
    2. Extract text content from document
    3. Use OpenAI to generate structured chunks
    4. Save chunks to database
    5. Return processing results
    
    **Response includes:**
    - Document information (filename, type, size)
    - Number of chunks generated
    - Generated chunks with content, bullets, and sample questions
    - Processing time
    """
    start_time = time.time()
    
    try:
        # Extract user information from the dictionary
        user_email = current_user.get('email', 'unknown')
        user_id = current_user.get('user_id', 'unknown')
        
        # Debug: Log the current_user structure
        logger.info(f"Current user structure: {current_user}")
        
        # Extract organization_id using the same pattern as other endpoints
        organization_id = current_user.get("organization", {}).get("id")
        logger.info(f"Organization ID from organization.id: {organization_id}")
        
        if not organization_id:
            logger.error(f"No organization_id found in user data: {current_user}")
            raise HTTPException(status_code=400, detail="User organization not found")
        
        logger.info(f"Starting document processing for {file.filename} by user {user_email} for receptionist {receptionist_id}")
        
        # Initialize services
        document_service = DocumentProcessingService()
        openai_service = OpenAIService()
        supabase = get_supabase_client()
        
        # Process document and extract text
        document_result = await document_service.process_document(file)
        
        # Prepare data for OpenAI processing
        scraped_data = {
            "scraped_content": [{
                "url": f"document://{document_result['filename']}",
                "title": document_result['filename'],
                "content": document_result['content'],
                "headings": [],  # Documents don't have headings like web pages
                "status_code": 200
            }]
        }
        
        # Generate chunks using OpenAI
        try:
            chunks = await openai_service.generate_chunks_from_scraped_data(
                scraped_data=scraped_data,
                organization_id=organization_id
            )
        except Exception as openai_error:
            logger.error(f"OpenAI processing failed: {str(openai_error)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to process document content with AI: {str(openai_error)}"
            )
        
        if not chunks:
            raise HTTPException(status_code=500, detail="No chunks were generated from document")
        
        # Update chunks with document-specific information
        for chunk in chunks:
            chunk["source_type"] = "file"  # Use "file" instead of "document" to match schema
            chunk["source_id"] = document_result['filename']
            chunk["created_by_user_id"] = None  # Skip user tracking for now due to foreign key constraint
            chunk["receptionist_id"] = receptionist_id if receptionist_id else None
        
        # Save chunks to database
        try:
            result = supabase.table("chunks").insert(chunks).execute()
            saved_chunks = result.data if result.data else []
            logger.info(f"Successfully saved {len(chunks)} chunks to database")
        except Exception as e:
            logger.error(f"Failed to save chunks to database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save chunks to database: {str(e)}")
        
        # Upload chunks to VAPI as files and update vapi_file_id
        from app.services.vapi_assistant import upload_chunk_to_vapi, sync_assistant_prompt
        for saved_chunk in saved_chunks:
            try:
                chunk_id = saved_chunk.get('id')
                chunk_name = saved_chunk.get('name', 'Unnamed Chunk')
                chunk_content = saved_chunk.get('content', '')
                bullets = saved_chunk.get('bullets', [])
                sample_questions = saved_chunk.get('sample_questions', [])
                
                # Upload to VAPI with complete information
                vapi_file_id = await upload_chunk_to_vapi(
                    chunk_id, 
                    chunk_name, 
                    chunk_content,
                    bullets=bullets,
                    sample_questions=sample_questions
                )
                
                # Update chunk with vapi_file_id
                if vapi_file_id:
                    supabase.table("chunks").update({"vapi_file_id": vapi_file_id}).eq("id", chunk_id).execute()
                    logger.info(f"Updated chunk {chunk_id} with VAPI file ID: {vapi_file_id}")
            except Exception as upload_error:
                logger.warning(f"Failed to upload chunk {chunk_id} to VAPI: {str(upload_error)}")
                # Continue with other chunks
        
        # Sync assistant with updated knowledge base file IDs
        if receptionist_id:
            try:
                rec_row = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).single().execute()
                assistant_id = rec_row.data.get("assistant_id") if rec_row.data else None
                if assistant_id:
                    await sync_assistant_prompt(assistant_id, receptionist_id)
                    logger.info(f"Successfully synced VAPI assistant {assistant_id} with new document knowledge")
            except Exception as sync_error:
                logger.warning(f"Failed to sync VAPI assistant: {str(sync_error)}")
                # Don't fail the request if sync fails - chunks are already saved
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Prepare response
        document_info = DocumentInfo(
            filename=document_result['filename'],
            file_type=document_result['file_type'],
            file_size=document_result['file_size'],
            content_length=document_result['content_length'],
            status=document_result['status']
        )
        
        chunk_responses = [
            DocumentChunkResponse(
                id=chunk.get('id'),
                organization_id=chunk['organization_id'],
                source_type=chunk['source_type'],
                source_id=chunk['source_id'],
                name=chunk['name'],
                description=chunk['description'],
                content=chunk['content'],
                bullets=chunk['bullets'],
                sample_questions=chunk['sample_questions'],
                created_at=chunk.get('created_at'),
                updated_at=chunk.get('updated_at'),
                created_by_user_id=chunk['created_by_user_id']
            )
            for chunk in chunks
        ]
        
        response = DocumentUploadResponse(
            message=f"Successfully processed document and generated {len(chunks)} chunks",
            document_info=document_info,
            chunks_generated=len(chunks),
            chunks=chunk_responses,
            processing_time_seconds=round(processing_time, 2)
        )
        
        logger.info(f"Document processing completed for {file.filename} in {processing_time:.2f} seconds")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

@router.get("/supported-formats")
async def get_supported_formats():
    """
    Get list of supported document formats
    """
    return {
        "supported_formats": [
            {
                "extension": ".pdf",
                "mime_type": "application/pdf",
                "description": "Portable Document Format"
            },
            {
                "extension": ".docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "description": "Microsoft Word Document (2007+)"
            },
            {
                "extension": ".txt",
                "mime_type": "text/plain",
                "description": "Plain Text File"
            },
            {
                "extension": ".csv",
                "mime_type": "text/csv",
                "description": "Comma-Separated Values"
            }
        ],
        "max_file_size": "10MB",
        "note": "Legacy .doc files are not supported. Please convert to .docx format."
    }

    """
    Test endpoint for document processing without authentication
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting test document processing for {file.filename}")
        
        # Initialize services
        document_service = DocumentProcessingService()
        openai_service = OpenAIService()
        
        # Process document and extract text
        document_result = await document_service.process_document(file)
        
        # Prepare data for OpenAI processing
        scraped_data = {
            "scraped_content": [{
                "url": f"document://{document_result['filename']}",
                "title": document_result['filename'],
                "content": document_result['content'],
                "headings": [],  # Documents don't have headings like web pages
                "status_code": 200
            }]
        }
        
        # Generate chunks using OpenAI
        chunks = await openai_service.generate_chunks_from_scraped_data(
            scraped_data=scraped_data,
            organization_id="test-org-id"
        )
        
        if not chunks:
            raise HTTPException(status_code=500, detail="Failed to generate chunks from document")
        
        # Update chunks with document-specific information
        for chunk in chunks:
            chunk["source_type"] = "document"
            chunk["source_id"] = document_result['filename']
            chunk["created_by_user_id"] = None  # Skip user tracking for now due to foreign key constraint
            chunk["receptionist_id"] = None # pass through later
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Prepare response
        document_info = DocumentInfo(
            filename=document_result['filename'],
            file_type=document_result['file_type'],
            file_size=document_result['file_size'],
            content_length=document_result['content_length'],
            status=document_result['status']
        )
        
        chunk_responses = [
            DocumentChunkResponse(
                id=chunk.get('id'),
                organization_id=chunk['organization_id'],
                source_type=chunk['source_type'],
                source_id=chunk['source_id'],
                name=chunk['name'],
                description=chunk['description'],
                content=chunk['content'],
                bullets=chunk['bullets'],
                sample_questions=chunk['sample_questions'],
                created_at=chunk.get('created_at'),
                updated_at=chunk.get('updated_at'),
                created_by_user_id=chunk['created_by_user_id']
            )
            for chunk in chunks
        ]
        
        response = DocumentUploadResponse(
            message=f"Successfully processed document and generated {len(chunks)} chunks",
            document_info=document_info,
            chunks_generated=len(chunks),
            chunks=chunk_responses,
            processing_time_seconds=round(processing_time, 2)
        )
        
        logger.info(f"Test document processing completed for {file.filename} in {processing_time:.2f} seconds")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test document processing {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

@router.post("/process-text", response_model=TextProcessingResponse)
async def process_text(
    request: TextInputRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Process text input and generate chunks using OpenAI.
    
    This endpoint takes raw text input and uses OpenAI to generate structured chunks
    that can be used for AI assistant training.
    
    Args:
        request: TextInputRequest containing the text, name, and description
        current_user: Authenticated user information
        
    Returns:
        TextProcessingResponse with generated chunks and processing statistics
    """
    start_time = time.time()
    
    try:
        # Extract user information from the dictionary
        user_email = current_user.get('email', 'unknown')
        user_id = current_user.get('user_id', 'unknown')
        
        # Extract organization_id using the same pattern as other endpoints
        organization_id = current_user.get("organization", {}).get("id")
        logger.info(f"Organization ID from organization.id: {organization_id}")
        
        if not organization_id:
            logger.error(f"No organization_id found in user data: {current_user}")
            raise HTTPException(status_code=400, detail="User organization not found")
        
        logger.info(f"Starting text processing for '{request.name}' by user {user_email}")
        
        # Initialize OpenAI service
        openai_service = OpenAIService()
        
        # Create scraped data structure for OpenAI processing
        scraped_data = {
            "scraped_content": [{
                "url": f"text://{request.name}",
                "title": request.name,
                "content": request.text,
                "meta_description": request.description,
                "headings": [],
                "links": [],
                "images": [],
                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                "status_code": 200,
                "error": None,
                "quality_analysis": {
                    "quality_score": 100,
                    "quality_status": "excellent",
                    "issues": [],
                    "recommendations": [],
                    "content_length": len(request.text),
                    "has_title": True,
                    "has_headings": False,
                    "has_links": False,
                    "scraping_method": "text_input"
                }
            }]
        }
        
        # Generate chunks using OpenAI
        chunks = await openai_service.generate_chunks_from_scraped_data(
            scraped_data=scraped_data,
            organization_id=organization_id
        )
        
        if not chunks:
            raise HTTPException(status_code=500, detail="Failed to generate chunks from text")
        
        # Update chunks with text-specific information
        for chunk in chunks:
            chunk["source_type"] = "text"  # Use "text" for direct text input
            chunk["source_id"] = f"text://{request.name}"
            chunk["created_by_user_id"] = None  # Skip user tracking for now due to foreign key constraint
            chunk["receptionist_id"] = request.receptionist_id if hasattr(request, "receptionist_id") else None
        
        # Save chunks to database
        try:
            supabase = get_supabase_client()
            result = supabase.table("chunks").insert(chunks).execute()
            saved_chunks = result.data if result.data else []
            logger.info(f"Successfully saved {len(chunks)} chunks to database")
        except Exception as e:
            logger.error(f"Failed to save chunks to database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save chunks to database: {str(e)}")
        
        # Upload chunks to VAPI as files and update vapi_file_id
        from app.services.vapi_assistant import upload_chunk_to_vapi, sync_assistant_prompt
        for saved_chunk in saved_chunks:
            try:
                chunk_id = saved_chunk.get('id')
                chunk_name = saved_chunk.get('name', 'Unnamed Chunk')
                chunk_content = saved_chunk.get('content', '')
                bullets = saved_chunk.get('bullets', [])
                sample_questions = saved_chunk.get('sample_questions', [])
                
                # Upload to VAPI with complete information
                vapi_file_id = await upload_chunk_to_vapi(
                    chunk_id, 
                    chunk_name, 
                    chunk_content,
                    bullets=bullets,
                    sample_questions=sample_questions
                )
                
                # Update chunk with vapi_file_id
                if vapi_file_id:
                    supabase.table("chunks").update({"vapi_file_id": vapi_file_id}).eq("id", chunk_id).execute()
                    logger.info(f"Updated chunk {chunk_id} with VAPI file ID: {vapi_file_id}")
            except Exception as upload_error:
                logger.warning(f"Failed to upload chunk {chunk_id} to VAPI: {str(upload_error)}")
                # Continue with other chunks
        
        # Sync assistant with updated knowledge base file IDs
        receptionist_id = request.receptionist_id if hasattr(request, "receptionist_id") else None
        if receptionist_id:
            try:
                rec_row = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).single().execute()
                assistant_id = rec_row.data.get("assistant_id") if rec_row.data else None
                if assistant_id:
                    await sync_assistant_prompt(assistant_id, receptionist_id)
                    logger.info(f"Successfully synced VAPI assistant {assistant_id} with new text knowledge")
            except Exception as sync_error:
                logger.warning(f"Failed to sync VAPI assistant: {str(sync_error)}")
                # Don't fail the request if sync fails - chunks are already saved
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        response = TextProcessingResponse(
            message=f"Successfully processed text and generated {len(chunks)} chunks",
            chunks_generated=len(chunks),
            chunks=chunks,
            processing_time_seconds=round(processing_time, 2)
        )
        
        logger.info(f"Text processing completed for '{request.name}' in {processing_time:.2f} seconds")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in text processing for '{request.name}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process text: {str(e)}"
        )

@router.post("/process-text-simple", response_model=TextProcessingResponse)
async def process_text_simple(
    request: TextInputRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Process text input and store it directly without AI processing.
    
    This is a simpler, faster alternative that just stores the text as-is
    without generating structured chunks or sample questions.
    
    Args:
        request: TextInputRequest containing the text, name, and description
        current_user: Authenticated user information
        
    Returns:
        TextProcessingResponse with simple chunk
    """
    start_time = time.time()
    
    try:
        # Extract user information from the dictionary
        user_email = current_user.get('email', 'unknown')
        user_id = current_user.get('user_id', 'unknown')
        
        # Extract organization_id using the same pattern as other endpoints
        organization_id = current_user.get("organization", {}).get("id")
        logger.info(f"Organization ID from organization.id: {organization_id}")
        
        if not organization_id:
            logger.error(f"No organization_id found in user data: {current_user}")
            raise HTTPException(status_code=400, detail="User organization not found")
        
        logger.info(f"Starting simple text processing for '{request.name}' by user {user_email}")
        
        # Create a simple chunk directly from the input
        chunk = {
            "organization_id": organization_id,
            "source_type": "text",
            "source_id": f"text://{request.name}",
            "name": request.name,
            "description": request.description,
            "content": request.text,
            "bullets": [],  # No AI-generated bullets
            "sample_questions": [],  # No AI-generated questions
            "created_by_user_id": None,  # Skip user tracking for now due to foreign key constraint
            "receptionist_id": request.receptionist_id if hasattr(request, "receptionist_id") else None
        }
        
        # Save chunk to database
        try:
            supabase = get_supabase_client()
            result = supabase.table("chunks").insert([chunk]).execute()
            saved_chunks = result.data if result.data else []
            logger.info(f"Successfully saved simple text chunk to database")
        except Exception as e:
            logger.error(f"Failed to save chunk to database: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save chunk to database: {str(e)}")
        
        # Upload chunk to VAPI as file and update vapi_file_id
        from app.services.vapi_assistant import upload_chunk_to_vapi, sync_assistant_prompt
        for saved_chunk in saved_chunks:
            try:
                chunk_id = saved_chunk.get('id')
                chunk_name = saved_chunk.get('name', 'Unnamed Chunk')
                chunk_content = saved_chunk.get('content', '')
                bullets = saved_chunk.get('bullets', [])
                sample_questions = saved_chunk.get('sample_questions', [])
                
                # Upload to VAPI with complete information
                vapi_file_id = await upload_chunk_to_vapi(
                    chunk_id, 
                    chunk_name, 
                    chunk_content,
                    bullets=bullets,
                    sample_questions=sample_questions
                )
                
                # Update chunk with vapi_file_id
                if vapi_file_id:
                    supabase.table("chunks").update({"vapi_file_id": vapi_file_id}).eq("id", chunk_id).execute()
                    logger.info(f"Updated chunk {chunk_id} with VAPI file ID: {vapi_file_id}")
            except Exception as upload_error:
                logger.warning(f"Failed to upload chunk {chunk_id} to VAPI: {str(upload_error)}")
                # Continue with other chunks
        
        # Sync assistant with updated knowledge base file IDs
        receptionist_id = request.receptionist_id if hasattr(request, "receptionist_id") else None
        if receptionist_id:
            try:
                rec_row = supabase.table("receptionists").select("assistant_id").eq("id", receptionist_id).single().execute()
                assistant_id = rec_row.data.get("assistant_id") if rec_row.data else None
                if assistant_id:
                    await sync_assistant_prompt(assistant_id, receptionist_id)
                    logger.info(f"Successfully synced VAPI assistant {assistant_id} with new simple text knowledge")
            except Exception as sync_error:
                logger.warning(f"Failed to sync VAPI assistant: {str(sync_error)}")
                # Don't fail the request if sync fails - chunks are already saved
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        response = TextProcessingResponse(
            message=f"Successfully processed text and created 1 chunk",
            chunks_generated=1,
            chunks=[chunk],
            processing_time_seconds=round(processing_time, 2)
        )
        
        logger.info(f"Simple text processing completed for '{request.name}' in {processing_time:.2f} seconds")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in simple text processing for '{request.name}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process text: {str(e)}"
        )
