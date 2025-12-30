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
    Search documents using PostgreSQL full-text search.
    
    Uses the pre-computed search_vector column with a GIN index for
    efficient searching. Falls back to ILIKE for documents without
    a search_vector (legacy records).
    
    The search uses plainto_tsquery which handles natural language queries,
    automatically converting spaces to AND operators.
    """
    sanitized_query = sanitize_search_query(q)
    
    if not sanitized_query:
        return []
    
    # Use full-text search with GIN index for documents with search_vector
    # Fall back to ILIKE for legacy documents without search_vector
    # ts_headline generates a snippet with search terms highlighted
    query = text("""
        SELECT 
            id, 
            filename, 
            CASE 
                WHEN search_vector IS NOT NULL THEN
                    ts_headline(
                        'portuguese',
                        COALESCE(content, ''),
                        plainto_tsquery('portuguese', :search_term),
                        'MaxWords=35, MinWords=15, StartSel=, StopSel='
                    )
                ELSE
                    SUBSTRING(COALESCE(content, ''), 1, 200)
            END as snippet,
            CASE 
                WHEN search_vector IS NOT NULL THEN
                    ts_rank(search_vector, plainto_tsquery('portuguese', :search_term))
                ELSE
                    0.0
            END as rank
        FROM documents 
        WHERE 
            (search_vector @@ plainto_tsquery('portuguese', :search_term))
            OR 
            (search_vector IS NULL AND content ILIKE :ilike_term)
        ORDER BY rank DESC, created_at DESC
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
