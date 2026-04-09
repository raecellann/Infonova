"""
Integrated Search Engine

This module provides an integrated search engine that combines TF-IDF retrieval
with Naive Bayes classification for enhanced search functionality.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import pickle
import os

from .tfidf_search_engine import TFIDFSearchEngine


class IntegratedSearchEngine:
    """
    An integrated search engine that combines TF-IDF retrieval with Naive Bayes classification.
    """
    
    def __init__(self, tfidf_index_path: str, nb_model_path: str):
        """
        Initialize the integrated search engine.
        
        Args:
            tfidf_index_path: Path to the TF-IDF index file
            nb_model_path: Path to the Naive Bayes model file
        """
        self.tfidf_engine = TFIDFSearchEngine()
        self.nb_classifier = None
        
        # Load TF-IDF index
        print("Loading TF-IDF index...")
        self.tfidf_engine.load_index(tfidf_index_path)
        
        # Load Naive Bayes model
        print("\nLoading Naive Bayes classifier...")
        self.load_nb_model(nb_model_path)
    
    def load_nb_model(self, filepath: str) -> None:
        """
        Load a trained Naive Bayes model from disk.
        
        Args:
            filepath: Path to the model file
        """
        with open(filepath, 'rb') as f:
            self.nb_classifier = pickle.load(f)
        print("  ✓ Loaded Naive Bayes classifier")
    
    def predict_class(self, text: str) -> str:
        """
        Predict the class of a text using the loaded Naive Bayes model.
        
        Args:
            text: Input text to classify
            
        Returns:
            Predicted class label
        """
        if not self.nb_classifier:
            raise ValueError("Naive Bayes classifier not loaded")
        
        # Use the classifier's predict method if available
        if hasattr(self.nb_classifier, 'predict'):
            return self.nb_classifier.predict([text])[0]
        
        # Fallback to direct prediction if predict method is not available
        return self.nb_classifier.classify(text)
    
    def search(self, query: str, top_k: int = 10, 
              filter_by_source: Optional[str] = None, 
              classify_query: bool = False) -> Dict[str, Any]:
        """
        Advanced search with optional classification.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            filter_by_source: Optional source label to filter by
            classify_query: If True, classify the query and filter results
            
        Returns:
            Dictionary containing search results and metadata
        """
        results = {
            'query': query,
            'results': [],
            'query_metadata': {}
        }
        
        # Classify query if requested
        if classify_query and self.nb_classifier:
            predicted_class = self.predict_class(query)
            results['query_metadata']['predicted_class'] = predicted_class
            
            # If no source filter is specified, use the predicted class
            if filter_by_source is None:
                filter_by_source = predicted_class
        
        # Perform TF-IDF search
        search_results = self.tfidf_engine.search(
            query, 
            top_k=top_k, 
            filter_label=filter_by_source
        )
        
        results['results'] = search_results
        results['total_results'] = len(search_results)
        
        return results
    
    @staticmethod
    def display_results(results: Dict[str, Any]) -> None:
        """
        Pretty print search results.
        
        Args:
            results: Search results from the search method
        """
        query = results['query']
        query_metadata = results.get('query_metadata', {})
        search_results = results.get('results', [])
        
        print(f"\n=== Search Results for: '{query}' ===")
        
        # Display query metadata if available
        if query_metadata:
            print("\nQuery Metadata:")
            for key, value in query_metadata.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Display search results
        print(f"\nFound {len(search_results)} results:")
        for i, doc in enumerate(search_results, 1):
            print(f"\n{i}. {doc.get('title', 'Untitled')}")
            print(f"   Source: {doc.get('label', 'Unknown')}")
            print(f"   URL: {doc.get('url', 'N/A')}")
            print(f"   Similarity: {doc.get('similarity_score', 0):.4f}")
        
        print("\n=== End of Results ===")
