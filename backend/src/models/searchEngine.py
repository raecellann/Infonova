"""
Search Engine Integration Module
Combines Naive Bayes Classification with TF-IDF Document Retrieval
"""

import os
import sys
from typing import List, Dict, Optional
from pymongo import MongoClient
import time

# Add parent directory to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import your existing modules
from backend.models.bow_naive_bayes import load_model, predict
from src.models.tfidf import TFIDFVectorizer
from src.utils.tokenizer import tokenize

class SearchEngine:
    """Main search engine combining classification and TF-IDF retrieval"""
    
    def __init__(self, mongodb_uri="mongodb://localhost:27017/", db_name="nlp_search_engine"):
        """Initialize search engine with all components"""
        print("Initializing Search Engine...")
        
        # MongoDB connection
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        
        # Initialize TF-IDF vectorizer
        self.tfidf_vectorizer = TFIDFVectorizer(mongodb_uri, db_name)
        
        # Load classification model
        self.classifier_model = self.load_classifier()
        
        # Load or build TF-IDF index
        self.initialize_tfidf_index()
        
        print("✓ Search Engine initialized successfully")
    
    def load_classifier(self):
        """Load the Naive Bayes classifier"""
        print("Loading classifier...")
        model_path = "bow_naive_bayes_model_v1.pkl"
        
        try:
            class_counts, class_word_counts, vocab_size = load_model(model_path)
            print("✓ Classifier loaded successfully")
            return {
                'class_counts': class_counts,
                'class_word_counts': class_word_counts,
                'vocab_size': vocab_size
            }
        except Exception as e:
            print(f"⚠ Warning: Could not load classifier: {e}")
            return None
    
    def initialize_tfidf_index(self):
        """Initialize or load TF-IDF index"""
        print("Initializing TF-IDF index...")
        
        # Try to load existing model
        if self.tfidf_vectorizer.load_model("tfidf_model.pkl"):
            print("✓ TF-IDF model loaded from file")
        else:
            print("Building TF-IDF index from documents...")
            documents = list(self.db.documents.find())
            
            if documents:
                self.tfidf_vectorizer.index_documents(documents)
                self.tfidf_vectorizer.save_model("tfidf_model.pkl")
            else:
                print("⚠ No documents found in database")
    
    def classify_query(self, query: str) -> Dict:
        """Classify the intent/category of a search query"""
        if not self.classifier_model:
            return {'category': None, 'confidence': 0}
        
        result = predict(
            query,
            self.classifier_model['class_counts'],
            self.classifier_model['class_word_counts'],
            self.classifier_model['vocab_size'],
            is_log=False
        )
        
        return {
            'category': result['prediction'],
            'confidence': result['confidence'],
            'ambiguous': result.get('ambiguous', False)
        }
    
    def search(self, 
              query: str, 
              top_k: int = 10,
              use_classification: bool = True,
              category_filter: Optional[str] = None) -> Dict:
        """
        Main search function combining all components
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            use_classification: Whether to use query classification for filtering
            category_filter: Manual category filter (overrides classification)
        
        Returns:
            Dictionary containing search results and metadata
        """
        start_time = time.time()
        
        # Initialize response
        response = {
            'query': query,
            'timestamp': time.time(),
            'results': [],
            'metadata': {}
        }
        
        # Classify query if needed
        if use_classification and not category_filter and self.classifier_model:
            classification_result = self.classify_query(query)
            response['metadata']['query_classification'] = classification_result
            
            # Use classification for filtering if confidence is high
            if classification_result['confidence'] > 0.7 and not classification_result['ambiguous']:
                category_filter = classification_result['category']
                response['metadata']['auto_filter'] = True
        
        # Perform TF-IDF search
        try:
            results = self.tfidf_vectorizer.search(query, top_k, category_filter)
            response['results'] = results
            response['metadata']['results_count'] = len(results)
            
            # Log search query for analytics
            self.log_search_query(query, len(results))
            
        except Exception as e:
            print(f"Error during search: {e}")
            response['error'] = str(e)
        
        # Calculate search time
        search_time = time.time() - start_time
        response['metadata']['search_time'] = f"{search_time:.3f}s"
        
        return response
    
    def get_autocomplete_suggestions(self, prefix: str, max_suggestions: int = 5) -> List[str]:
        """Get autocomplete suggestions from n-grams collection"""
        if len(prefix) < 2:
            return []
        
        # Query n-grams collection for matching prefixes
        pipeline = [
            {'$match': {'ngram': {'$regex': f'^{prefix}', '$options': 'i'}}},
            {'$sort': {'frequency': -1}},
            {'$limit': max_suggestions},
            {'$project': {'ngram': 1, 'frequency': 1}}
        ]
        
        suggestions = list(self.db.ngrams.aggregate(pipeline))
        return [s['ngram'] for s in suggestions]
    
    def log_search_query(self, query: str, results_count: int):
        """Log search query for analytics"""
        self.db.search_queries.insert_one({
            'query': query,
            'timestamp': time.time(),
            'results_count': results_count,
            'clicked_results': [],  # To be updated when user clicks
            'user_session': 'session_' + str(time.time())
        })
    
    def update_clicked_result(self, query: str, doc_id: str):
        """Update clicked results for a query (for analytics)"""
        self.db.search_queries.update_one(
            {'query': query},
            {'$push': {'clicked_results': doc_id}},
            sort=[('timestamp', -1)]  # Update most recent query
        )
    
    def add_document(self, doc: Dict) -> bool:
        """Add a new document and update indexes"""
        try:
            # Insert document
            doc['doc_id'] = doc.get('doc_id', f"DOC_{time.time()}")
            self.db.documents.insert_one(doc)
            
            # Process document
            tokens = tokenize(doc.get('content', ''))
            
            # Store processed document
            self.db.processed_documents.insert_one({
                'doc_id': doc['doc_id'],
                'tokens': tokens,
                'cleaned_text': ' '.join(tokens),
                'processed_at': time.time()
            })
            
            # Update TF-IDF index (incrementally)
            # In production, you might want to rebuild periodically
            print(f"Document {doc['doc_id']} added successfully")
            return True
            
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def get_document_by_id(self, doc_id: str) -> Dict:
        """Retrieve full document by ID"""
        return self.db.documents.find_one({'doc_id': doc_id})
    
    def get_similar_documents(self, doc_id: str, top_k: int = 5) -> List[Dict]:
        """Get similar documents using TF-IDF similarity"""
        return self.tfidf_vectorizer.get_similar_documents(doc_id, top_k)
    
    def get_search_analytics(self, limit: int = 100) -> Dict:
        """Get search analytics data"""
        # Most popular queries
        pipeline = [
            {'$group': {
                '_id': '$query',
                'count': {'$sum': 1},
                'avg_results': {'$avg': '$results_count'}
            }},
            {'$sort': {'count': -1}},
            {'$limit': limit}
        ]
        
        popular_queries = list(self.db.search_queries.aggregate(pipeline))
        
        # Queries with no results
        no_results = list(self.db.search_queries.find(
            {'results_count': 0},
            {'query': 1}
        ).limit(limit))
        
        return {
            'popular_queries': popular_queries,
            'queries_with_no_results': no_results,
            'total_searches': self.db.search_queries.count_documents({})
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize search engine
    search_engine = SearchEngine()
    
    print("\n" + "="*60)
    print("SEARCH ENGINE TESTING")
    print("="*60)
    
    # Test queries
    test_queries = [
        "python programming tutorial",
        "machine learning algorithms",
        "web development javascript",
        "data science python",
        "artificial intelligence"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: '{query}'")
        print('='*60)
        
        # Perform search
        results = search_engine.search(query, top_k=3)
        
        # Display results
        if 'metadata' in results:
            print(f"\nMetadata:")
            print(f"  Search time: {results['metadata'].get('search_time', 'N/A')}")
            
            if 'query_classification' in results['metadata']:
                classification = results['metadata']['query_classification']
                print(f"  Query category: {classification['category']} ({classification['confidence']:.1%} confidence)")
            
            print(f"  Results found: {results['metadata'].get('results_count', 0)}")
        
        if results['results']:
            print(f"\nTop Results:")
            for i, result in enumerate(results['results'], 1):
                print(f"\n  {i}. {result['title']}")
                print(f"     Score: {result['score']:.4f}")
                print(f"     Category: {result['category']}")
                print(f"     Matching terms: {', '.join(result['matching_terms'])}")
                print(f"     URL: {result.get('url', 'N/A')}")
                print(f"     Preview: {result['content_preview'][:100]}...")
        else:
            print("\n  No results found")
    
    # Test autocomplete
    print(f"\n{'='*60}")
    print("AUTOCOMPLETE TESTING")
    print('='*60)
    
    test_prefixes = ["mach", "pyth", "web", "java"]
    for prefix in test_prefixes:
        suggestions = search_engine.get_autocomplete_suggestions(prefix)
        print(f"\n'{prefix}' → {suggestions if suggestions else 'No suggestions'}")
    
    # Show analytics
    print(f"\n{'='*60}")
    print("SEARCH ANALYTICS")
    print('='*60)
    
    analytics = search_engine.get_search_analytics(limit=5)
    
    print(f"\nTotal searches: {analytics['total_searches']}")
    
    if analytics['popular_queries']:
        print("\nMost popular queries:")
        for query_data in analytics['popular_queries'][:5]:
            print(f"  - '{query_data['_id']}' ({query_data['count']} searches, avg {query_data['avg_results']:.1f} results)")
    
    if analytics['queries_with_no_results']:
        print("\nQueries with no results:")
        for query_data in analytics['queries_with_no_results'][:5]:
            print(f"  - '{query_data.get('query', 'N/A')}'")
    
    print(f"\n{'='*60}")
    print("✓ Search engine testing complete!")
    print('='*60)