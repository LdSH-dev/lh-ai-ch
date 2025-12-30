"""
Routes for managing document tags.

Provides CRUD operations for tags and endpoints for managing
document-tag associations.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Tag, Document
from app.schemas import TagCreate, TagResponse, TagListResponse

router = APIRouter()


@router.get("/tags", response_model=TagListResponse)
async def list_tags(db: AsyncSession = Depends(get_db)):
    """
    List all available tags ordered by name.
    """
    result = await db.execute(
        select(Tag).order_by(Tag.name)
    )
    tags = result.scalars().all()
    
    return TagListResponse(
        items=[TagResponse.model_validate(tag) for tag in tags],
        total=len(tags)
    )


@router.post("/tags", response_model=TagResponse, status_code=201)
async def create_tag(tag_data: TagCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new tag.
    
    Tag names must be unique (case-insensitive comparison).
    """
    # Normalize tag name (strip whitespace)
    tag_name = tag_data.name.strip()
    
    if not tag_name:
        raise HTTPException(status_code=400, detail="Tag name cannot be empty")
    
    # Check if tag already exists (case-insensitive)
    existing = await db.execute(
        select(Tag).where(func.lower(Tag.name) == func.lower(tag_name))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tag already exists")
    
    tag = Tag(name=tag_name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    
    return TagResponse.model_validate(tag)


@router.get("/tags/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific tag by ID.
    """
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    return TagResponse.model_validate(tag)


@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete a tag.
    
    This will also remove the tag from all documents that have it.
    """
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    await db.delete(tag)
    await db.commit()
    
    return {"message": "Tag deleted"}


@router.post("/documents/{document_id}/tags/{tag_id}")
async def add_tag_to_document(
    document_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a tag to a document.
    """
    # Fetch document with its tags
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Fetch tag
    tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = tag_result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Check if tag is already associated
    if tag in document.tags:
        raise HTTPException(status_code=409, detail="Tag already added to document")
    
    document.tags.append(tag)
    await db.commit()
    
    return {"message": "Tag added to document"}


@router.delete("/documents/{document_id}/tags/{tag_id}")
async def remove_tag_from_document(
    document_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a tag from a document.
    """
    # Fetch document with its tags
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Fetch tag
    tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = tag_result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    # Check if tag is associated
    if tag not in document.tags:
        raise HTTPException(status_code=404, detail="Tag not found on document")
    
    document.tags.remove(tag)
    await db.commit()
    
    return {"message": "Tag removed from document"}


@router.get("/documents/{document_id}/tags", response_model=TagListResponse)
async def get_document_tags(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tags for a specific document.
    """
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.tags))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return TagListResponse(
        items=[TagResponse.model_validate(tag) for tag in document.tags],
        total=len(document.tags)
    )

