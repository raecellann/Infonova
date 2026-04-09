from fastapi import APIRouter, Request, HTTPException, Depends, Query   
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import os
import sys
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from controllers.ngramController import NgramController

ngramRouter = APIRouter()

# Initialize the controller with the data directory
data_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    'data'
)

# Initialize the controller
ngram_controller = NgramController(data_path=data_dir)

# Dependency to check if model is initialized
async def get_ngram_controller():
    if not ngram_controller.initialized:
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "message": "N-gram model is not initialized. Please try again later.",
                "error": "ModelNotInitialized"
            }
        )
    return ngram_controller

# @router.post("/auto-suggest")
@ngramRouter.get("/auto-suggest")
async def auto_suggest(
    q: str = Query(..., description="Input q for auto-suggestions"),
    top_k: int = Query(5, description="Number of suggestions to return", ge=1, le=10)
):
    """
    Get auto-suggestions for the given input q using n-gram model.
    
    Parameters:
    - q: The input q to generate suggestions for
    - top_k: Number of suggestions to return (1-10, default: 5)
    
    Returns:
    - success: Boolean indicating if the request was successful
    - message: Status message
    - suggestions: List of suggested words
    """
    try:
        if not q or not q.strip():
            return {
                "success": False,
                "message": "Input q cannot be empty",
                "suggestions": []
            }
            
        # Get suggestions from controller
        response = ngram_controller.get_suggestions(q, top_k)
        
        # Ensure we have a valid response
        if not isinstance(response, dict) or 'suggestions' not in response:
            return {
                "success": False,
                "message": "Unexpected response format from suggestion service",
                "suggestions": []
            }
            
        return response
        
    except Exception as e:
        print(f"Error in auto_suggest endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "message": f"Error processing request: {str(e)}",
            "suggestions": []
        }
