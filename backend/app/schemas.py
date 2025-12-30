from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Generic, TypeVar, List

T = TypeVar("T")


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
