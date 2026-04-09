"""
Flask API for NLP Search Engine
Provides REST endpoints for search, autocomplete, and document management
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from datetime import datetime

# Add parent directory to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import the search engine
from src.models.searchEngine import SearchEngine

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize search engine
search_engine = SearchEngine()

@app.route('/')
def home():
    """API home endpoint"""
    return jsonify({
        'message': 'NLP Search Engine API',
        'version': '1.0.0',
        'endpoints': {
            'search': '/api/search',
            'autocomplete': '/api/autocomplete',
            'document': '/api/document/<doc_id>',
            'similar': '/api/similar/<doc_id>',
            'analytics': '/api/analytics',
            'health': '/api/health'
        }
    })

@app.route('/api/search', methods=['GET', 'POST'])
def search():
    """
    Main search endpoint
    
    Query parameters or JSON body:
    - query: search query string (required)
    - top_k: number of results to return (default: 10)
    - category: filter by category (optional)
    - use_classification: whether to use query classification (default: true)
    """
    # Get parameters from query string or JSON body
    if request.method == 'GET':
        query = request.args.get('query', '')
        top_k = int(request.args.get('top_k', 10))
        category = request.args.get('category', None)
        use_classification = request.args.get('use_classification', 'true').lower() == 'true'
    else:  # POST
        data = request.get_json()
        query = data.get('query', '')
        top_k = data.get('top_k', 10)
        category = data.get('category', None)
        use_classification = data.get('use_classification', True)
    
    # Validate query
    if not query:
        return jsonify({
            'error': 'Query parameter is required',
            'status': 'error'
        }), 400
    
    try:
        # Perform search
        results = search_engine.search(
            query=query,
            top_k=top_k,
            use_classification=use_classification,
            category_filter=category
        )
        
        # Add status
        results['status'] = 'success'
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'query': query
        }), 500

@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    """
    Autocomplete suggestions endpoint
    
    Query parameters:
    - prefix: partial query string (required)
    - limit: maximum suggestions to return (default: 5)
    """
    prefix = request.args.get('prefix', '')
    limit = int(request.args.get('limit', 5))
    
    if len(prefix) < 2:
        return jsonify({
            'suggestions': [],
            'message': 'Prefix must be at least 2 characters',
            'status': 'success'
        })
    
    try:
        suggestions = search_engine.get_autocomplete_suggestions(prefix, limit)
        
        return jsonify({
            'prefix': prefix,
            'suggestions': suggestions,
            'count': len(suggestions),
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'prefix': prefix
        }), 500

@app.route('/api/document/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """
    Get full document by ID
    
    Path parameters:
    - doc_id: document identifier
    """
    try:
        document = search_engine.get_document_by_id(doc_id)
        
        if document:
            # Remove MongoDB internal _id for JSON serialization
            if '_id' in document:
                document['_id'] = str(document['_id'])
            
            return jsonify({
                'document': document,
                'status': 'success'
            })
        else:
            return jsonify({
                'error': 'Document not found',
                'status': 'error',
                'doc_id': doc_id
            }), 404
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'doc_id': doc_id
        }), 500

@app.route('/api/similar/<doc_id>', methods=['GET'])
def get_similar_documents(doc_id):
    """
    Get similar documents
    
    Path parameters:
    - doc_id: document identifier
    
    Query parameters:
    - limit: maximum similar documents to return (default: 5)
    """
    limit = int(request.args.get('limit', 5))
    
    try:
        similar_docs = search_engine.get_similar_documents(doc_id, limit)
        
        return jsonify({
            'doc_id': doc_id,
            'similar_documents': similar_docs,
            'count': len(similar_docs),
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error',
            'doc_id': doc_id
        }), 500

@app.route('/api/document', methods=['POST'])
def add_document():
    """
    Add a new document to the search engine
    
    JSON body:
    - title: document title (required)
    - content: document content (required)
    - category: document category (optional)
    - url: document URL (optional)
    - metadata: additional metadata (optional)
    """
    data = request.get_json()
    
    # Validate required fields
    if not data.get('title') or not data.get('content'):
        return jsonify({
            'error': 'Title and content are required',
            'status': 'error'
        }), 400
    
    try:
        # Prepare document
        document = {
            'title': data['title'],
            'content': data['content'],
            'category': data.get('category', 'uncategorized'),
            'url': data.get('url', ''),
            'metadata': data.get('metadata', {}),
            'created_at': datetime.now().isoformat()
        }
        
        # Add document
        success = search_engine.add_document(document)
        
        if success:
            return jsonify({
                'message': 'Document added successfully',
                'doc_id': document.get('doc_id'),
                'status': 'success'
            }), 201
        else:
            return jsonify({
                'error': 'Failed to add document',
                'status': 'error'
            }), 500
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """
    Get search analytics
    
    Query parameters:
    - limit: maximum results per category (default: 10)
    """
    limit = int(request.args.get('limit', 10))
    
    try:
        analytics = search_engine.get_search_analytics(limit)
        
        return jsonify({
            'analytics': analytics,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/click', methods=['POST'])
def log_click():
    """
    Log when a user clicks on a search result (for analytics)
    
    JSON body:
    - query: the search query
    - doc_id: the clicked document ID
    """
    data = request.get_json()
    
    query = data.get('query')
    doc_id = data.get('doc_id')
    
    if not query or not doc_id:
        return jsonify({
            'error': 'Query and doc_id are required',
            'status': 'error'
        }), 400
    
    try:
        search_engine.update_clicked_result(query, doc_id)
        
        return jsonify({
            'message': 'Click logged successfully',
            'status': 'success'
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        search_engine.db.list_collection_names()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500

if __name__ == '__main__':
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"""
    ╔══════════════════════════════════════╗
    ║     NLP Search Engine API Server     ║
    ╚══════════════════════════════════════╝
    
    Starting server on http://localhost:{port}
    Debug mode: {debug}
    
    Available endpoints:
    - GET  /                        Home
    - GET  /api/search              Search documents
    - GET  /api/autocomplete        Get suggestions
    - GET  /api/document/<id>       Get document
    - GET  /api/similar/<id>        Find similar docs
    - POST /api/document            Add document
    - GET  /api/analytics           View analytics
    - POST /api/click               Log click
    - GET  /api/health              Health check
    
    Press CTRL+C to stop the server
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)