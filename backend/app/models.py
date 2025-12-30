from sqlalchemy import Column, Index, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR
from datetime import datetime

from app.database import Base


# Association table for many-to-many relationship between documents and tags
document_tags = Table(
    "document_tags",
    Base.metadata,
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """Tag model for categorizing documents with custom labels."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Many-to-many relationship with documents
    documents = relationship(
        "Document",
        secondary=document_tags,
        back_populates="tags",
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=True)  # Path to physical file on disk
    content = Column(Text)
    # Pre-computed tsvector for full-text search (populated on insert/update)
    search_vector = Column(TSVECTOR, nullable=True)
    file_size = Column(Integer)
    page_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # GIN index for fast full-text search queries
    __table_args__ = (
        Index(
            "ix_documents_search_vector",
            search_vector,
            postgresql_using="gin",
        ),
    )

    processing_status = relationship(
        "ProcessingStatus",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Many-to-many relationship with tags
    tags = relationship(
        "Tag",
        secondary=document_tags,
        back_populates="documents",
    )


class ProcessingStatus(Base):
    __tablename__ = "processing_statuses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(50), default="completed")
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="processing_status")
