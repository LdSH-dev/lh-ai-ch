from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SearchResult

router = APIRouter()


def sanitize_search_query(query: str) -> str:
    """
    Sanitizes the search query for use with PostgreSQL full-text search.
    
    Removes special characters that could break the tsquery parser,
    keeping only alphanumeric characters, spaces, and accented letters.
    """
    # Remove characters that are special in tsquery syntax
    # Keep letters (including accented), numbers, and spaces
    sanitized = "".join(
        char if char.isalnum() or char.isspace() else " "
        for char in query
    )
    # Collapse multiple spaces into one and strip
    return " ".join(sanitized.split())


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search documents by content, filename, and tags.
    
    Search strategy:
    1. Full-text search on content (using search_vector if available)
    2. ILIKE search on filename
    3. ILIKE search on associated tag names
    
    Results are ranked by relevance and deduplicated.
    """
    sanitized_query = sanitize_search_query(q)
    
    if not sanitized_query:
        return []
    
    # Search across content, filename, and tags using UNION to combine results
    # Each source gets a different base rank to prioritize matches
    query = text("""
        WITH search_results AS (
            -- Search by full-text vector (highest priority when available)
            SELECT DISTINCT
                d.id,
                d.filename,
                SUBSTRING(COALESCE(d.content, ''), 1, 200) as snippet,
                CASE 
                    WHEN d.search_vector IS NOT NULL THEN
                        ts_rank(d.search_vector, plainto_tsquery('portuguese', :search_term)) + 1.0
                    ELSE 0.5
                END as rank,
                d.created_at
            FROM documents d
            WHERE 
                d.search_vector @@ plainto_tsquery('portuguese', :search_term)
            
            UNION
            
            -- Search by content ILIKE (fallback for documents without search_vector)
            SELECT DISTINCT
                d.id,
                d.filename,
                SUBSTRING(COALESCE(d.content, ''), 1, 200) as snippet,
                0.5 as rank,
                d.created_at
            FROM documents d
            WHERE 
                d.content ILIKE :ilike_term
            
            UNION
            
            -- Search by filename (high priority)
            SELECT DISTINCT
                d.id,
                d.filename,
                SUBSTRING(COALESCE(d.content, ''), 1, 200) as snippet,
                2.0 as rank,
                d.created_at
            FROM documents d
            WHERE 
                d.filename ILIKE :ilike_term
            
            UNION
            
            -- Search by tag names
            SELECT DISTINCT
                d.id,
                d.filename,
                SUBSTRING(COALESCE(d.content, ''), 1, 200) as snippet,
                1.5 as rank,
                d.created_at
            FROM documents d
            INNER JOIN document_tags dt ON d.id = dt.document_id
            INNER JOIN tags t ON dt.tag_id = t.id
            WHERE 
                t.name ILIKE :ilike_term
        )
        SELECT 
            id,
            filename,
            snippet,
            MAX(rank) as rank
        FROM search_results
        GROUP BY id, filename, snippet
        ORDER BY rank DESC, MAX(created_at) DESC
        LIMIT 100
    """)
    
    result = await db.execute(
        query,
        {
            "search_term": sanitized_query,
            "ilike_term": f"%{sanitized_query}%",
        }
    )
    rows = result.fetchall()

    results = []
    for row in rows:
        snippet = row[2] or ""
        # Add ellipsis if snippet was truncated
        if len(snippet) >= 200 and not snippet.endswith("..."):
            snippet = snippet + "..."
        results.append(
            SearchResult(
                id=row[0],
                filename=row[1],
                snippet=snippet,
            )
        )

    return results
