import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Document, ProcessingStatus
from app.schemas import DocumentResponse, DocumentDetail
from app.services.pdf_processor import extract_text_from_pdf
from app.config import settings

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


@router.post("/documents")
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
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
        content = await file.read()
        f.write(content)

    file_size = len(content)
    text_content, page_count = await extract_text_from_pdf(file_path)

    document = Document(
        filename=file.filename,
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


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document))
    documents = result.scalars().all()

    response = []
    for doc in documents:
        status_result = await db.execute(
            select(ProcessingStatus).where(ProcessingStatus.document_id == doc.id)
        )
        status = status_result.scalar_one_or_none()
        response.append(
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                page_count=doc.page_count,
                status=status.status if status else "unknown",
                created_at=doc.created_at,
            )
        )

    return response


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
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    status_result = await db.execute(
        select(ProcessingStatus).where(ProcessingStatus.document_id == document.id)
    )
    status = status_result.scalar_one_or_none()
    if status:
        await db.delete(status)

    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted"}
