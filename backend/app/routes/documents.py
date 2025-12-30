import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Document, ProcessingStatus
from app.schemas import DocumentResponse, DocumentDetail, DocumentListResponse
from app.services.pdf_processor import extract_text_from_pdf
from app.config import settings

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# File validation constants
ALLOWED_CONTENT_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}
PDF_MAGIC_BYTES = b"%PDF"  # PDF files start with this signature
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

router = APIRouter()


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to prevent path traversal attacks.
    
    - Extracts only the base name (removes directory components)
    - Removes null bytes and other dangerous characters
    - Replaces unsafe characters with underscores
    - Adds a UUID prefix to prevent filename collisions
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Extract only the base filename (removes any path components like ../)
    safe_name = os.path.basename(filename)
    
    # Remove null bytes which can be used to bypass checks
    safe_name = safe_name.replace('\x00', '')
    
    # Remove or replace potentially dangerous characters
    # Keep only alphanumeric, dots, underscores, hyphens
    safe_name = re.sub(r'[^\w.\-]', '_', safe_name)
    
    # Ensure the filename is not empty after sanitization
    if not safe_name or safe_name in ('.', '..'):
        raise ValueError("Invalid filename after sanitization")
    
    # Add UUID prefix to prevent filename collisions
    unique_prefix = uuid.uuid4().hex[:8]
    safe_name = f"{unique_prefix}_{safe_name}"
    
    return safe_name


def validate_file_path(base_dir: str, file_path: str) -> bool:
    """
    Validates that the resolved file path is within the allowed base directory.
    Prevents path traversal by checking the real path.
    """
    # Resolve to absolute paths
    base_dir_resolved = os.path.realpath(base_dir)
    file_path_resolved = os.path.realpath(file_path)
    
    # Check that the file path starts with the base directory
    return file_path_resolved.startswith(base_dir_resolved + os.sep)


async def validate_pdf_file(file: UploadFile) -> bytes:
    """
    Validates that the uploaded file is a valid PDF.
    
    Performs multi-layer validation:
    1. Filename validation - must have a filename
    2. Extension check - filename must end with .pdf
    3. Content-Type check - must be application/pdf
    4. File size check - must not exceed maximum allowed size
    5. Empty file check - must have content
    6. Magic bytes check - file must start with %PDF signature
    
    Returns the file content if valid.
    Raises HTTPException if any validation fails.
    """
    # 1. Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required."
        )
    
    # 2. Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '{ext}'. Only PDF files (.pdf) are allowed."
        )
    
    # 3. Validate Content-Type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type '{file.content_type}'. Only PDF files (application/pdf) are allowed."
        )
    
    # 4. Read file content for size and magic bytes validation
    content = await file.read()
    
    # 5. Validate file size
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        max_size_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size // (1024 * 1024)} MB). Maximum allowed size is {max_size_mb} MB."
        )
    
    # 6. Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty. Please upload a valid PDF file."
        )
    
    # 7. Validate PDF magic bytes (signature)
    # PDF files must start with "%PDF" (bytes: 0x25 0x50 0x44 0x46)
    if not content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file. The file content does not match PDF format signature."
        )
    
    return content


@router.post("/documents")
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
    # Validate that the file is a valid PDF and get its content
    # This performs extension, content-type, size, and magic bytes validation
    content = await validate_pdf_file(file)
    file_size = len(content)
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Sanitize filename to prevent path traversal attacks
    try:
        safe_filename = sanitize_filename(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)
    
    # Double-check that the final path is within the upload directory
    if not validate_file_path(settings.UPLOAD_DIR, file_path):
        raise HTTPException(status_code=400, detail="Invalid file path")

    with open(file_path, "wb") as f:
        f.write(content)
    text_content, page_count = await extract_text_from_pdf(file_path)

    document = Document(
        filename=file.filename,
        file_path=file_path,
        content=text_content,
        file_size=file_size,
        page_count=page_count,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    processing_status = ProcessingStatus(
        document_id=document.id,
        status="completed",
        processed_at=datetime.utcnow(),
    )
    db.add(processing_status)
    await db.commit()

    return {"id": document.id, "filename": document.filename}


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    List documents with pagination.
    
    - **page**: Page number starting from 1
    - **page_size**: Number of items per page (max 100)
    """
    # Count total documents
    count_result = await db.execute(select(func.count(Document.id)))
    total = count_result.scalar_one()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Use selectinload to eager load processing_status in a single query
    # This avoids the N+1 query problem
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.processing_status))
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    documents = result.scalars().all()

    items = [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            page_count=doc.page_count,
            status=doc.processing_status.status if doc.processing_status else "unknown",
            created_at=doc.created_at,
        )
        for doc in documents
    ]
    
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/documents/{document_id}")
async def get_document(document_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    status_result = await db.execute(
        select(ProcessingStatus).where(ProcessingStatus.document_id == document.id)
    )
    status = status_result.scalar_one_or_none()

    return DocumentDetail(
        id=document.id,
        filename=document.filename,
        content=document.content,
        file_size=document.file_size,
        page_count=document.page_count,
        status=status.status if status else "unknown",
        created_at=document.created_at,
    )


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: AsyncSession = Depends(get_db)):
    """
    Deletes a document and its associated physical file.
    
    This endpoint:
    1. Removes the ProcessingStatus record (if exists)
    2. Removes the Document record from the database
    3. Deletes the physical PDF file from disk
    
    The physical file deletion is done after the database commit to ensure
    data consistency. If the file doesn't exist, the deletion is silently ignored.
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Store file_path before deleting the document record
    file_path = document.file_path

    status_result = await db.execute(
        select(ProcessingStatus).where(ProcessingStatus.document_id == document.id)
    )
    status = status_result.scalar_one_or_none()
    if status:
        await db.delete(status)

    await db.delete(document)
    await db.commit()

    # Delete the physical file after successful database commit
    # This order ensures we don't leave orphaned DB records if file deletion fails
    if file_path:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except OSError:
            # Log the error but don't fail the request since DB deletion succeeded
            # In production, this should be logged for monitoring
            pass

    return {"message": "Document deleted"}
