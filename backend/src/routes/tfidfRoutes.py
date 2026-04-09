from fastapi import APIRouter, Query, HTTPException, status
from typing import Optional
import os
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from controllers.tfidfController import tfidf_controller

# Create router
tfidf_router = APIRouter(
    tags=["TF-IDF SEARCH"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


@tfidf_router.get("/search", status_code=status.HTTP_200_OK)
async def search(
    query: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    source: Optional[str] = Query(None, description="Filter results by source (e.g., GMA, RAPPLER)"),
    min_score: float = Query(0.05, ge=0, le=1, description="Minimum similarity score (0-1)")
):
    """
    Search for documents using TF-IDF similarity with pagination.
    - **query**: The search query string
    - **limit**: Maximum number of results to return
    - **offset**: Number of results to skip
    - **source**: Optional filter to only return results from a specific source
    - **min_score**: Minimum similarity score (0-1) for results
    """
    try:
        # Fetch ALL matching results (no top_k limit for pagination)
        # Apply pagination after getting all results
        all_results = tfidf_controller.search(
            query=query,
            top_k=200,  # can be adjusted to 1000 to get more results
            filter_label=source,
            min_score=min_score
        )
        
        # Total available results
        total_available = len(all_results)
        
        # Apply offset and limit for this page
        start_idx = offset
        end_idx = offset + limit
        paginated_results = all_results[start_idx:end_idx]
        
        # Check if there are more results
        has_more = end_idx < total_available
        
        print(f"Search results - Query: '{query}', Total: {total_available}, Offset: {offset}, Limit: {limit}, Returning: {len(paginated_results)}, HasMore: {has_more}")
        
        return {
            "status": "success",
            "query": query,
            "results": paginated_results,
            "count": len(paginated_results),
            "total": total_available,
            "has_more": has_more,
            "offset": offset,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@tfidf_router.get("/status", status_code=status.HTTP_200_OK)
async def get_status():
    """
    Get the status of the TF-IDF search service.
    
    Returns information about the loaded model and its status.
    """
    return {
        "status": "ready" if tfidf_controller.initialized else "initializing",
        "model_loaded": tfidf_controller.initialized,
        "model_path": tfidf_controller.model_path,
        "doc_count": getattr(tfidf_controller.tfidf_engine, 'doc_count', 0) if tfidf_controller.initialized else 0,
        "vocab_size": len(getattr(tfidf_controller.tfidf_engine, 'vocab', set())) if tfidf_controller.initialized else 0
    }
