from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Generic, TypeVar, List

T = TypeVar("T")


# ========== Tag Schemas ==========

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Tag name")


class TagCreate(TagBase):
    """Schema for creating a new tag."""
    pass


class TagResponse(TagBase):
    """Schema for tag response."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """Response containing a list of all tags."""
    items: List[TagResponse]
    total: int


# ========== Document Schemas ==========

class DocumentBase(BaseModel):
    filename: str


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    status: str
    created_at: datetime
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True


class DocumentDetail(DocumentResponse):
    content: Optional[str] = None


class SearchResult(BaseModel):
    id: int
    filename: str
    snippet: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentListResponse(PaginatedResponse[DocumentResponse]):
    """Paginated response for document listing."""
    pass


# ========== Document-Tag Association Schemas ==========

class DocumentTagUpdate(BaseModel):
    """Schema for adding/removing tags from a document."""
    tag_ids: List[int] = Field(..., description="List of tag IDs to associate with the document")
