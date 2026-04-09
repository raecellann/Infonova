"""
TF-IDF Search Engine Implementation

This module implements a TF-IDF based search engine for document retrieval.
"""

import math
import os
import pickle
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Any, Set
import pandas as pd

from src.utils.tokenizer import tokenize
from src.utils.progress import show_progress


class TFIDFSearchEngine:
    """
    A search engine that uses TF-IDF for document retrieval.
    """
    
    def __init__(self):
        """Initialize the TF-IDF search engine."""
        self.documents: List[Dict[str, Any]] = []  # List of document metadata
        self.tfidf_vectors: List[Dict[str, float]] = []  # TF-IDF vectors for each document
        self.idf: Dict[str, float] = {}  # IDF scores for each term
        self.vocab: Set[str] = set()  # All unique terms
        self.doc_count: int = 0
    
    def compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """
        Compute term frequency for a document.
        
        Args:
            tokens: List of tokens in the document
            
        Returns:
            Dictionary mapping terms to their TF scores
        """
        tf = {}
        total_tokens = len(tokens)
        token_counts = Counter(tokens)
        
        for token, count in token_counts.items():
            # Normalized TF: count / total tokens
            tf[token] = count / total_tokens if total_tokens > 0 else 0
        
        return tf
    
    def compute_idf(self, documents_tokens: List[List[str]]) -> Dict[str, float]:
        """
        Compute IDF for all terms in the corpus.
        
        Args:
            documents_tokens: List of tokenized documents
            
        Returns:
            Dictionary mapping terms to their IDF scores
        """
        print("Computing IDF scores...")
        doc_freq = defaultdict(int)
        total_docs = len(documents_tokens)
        
        # Count document frequency for each term
        for tokens in documents_tokens:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1
        
        # Calculate IDF: log(N / df)
        idf = {}
        for token, freq in doc_freq.items():
            idf[token] = math.log(total_docs / freq) if freq > 0 else 0
        
        print(f"  ✓ Computed IDF for {len(idf):,} unique terms")
        return idf
    
    def compute_tfidf_vector(self, tokens: List[str]) -> Dict[str, float]:
        """
        Compute TF-IDF vector for a document.
        
        Args:
            tokens: List of tokens in the document
            
        Returns:
            Dictionary mapping terms to their TF-IDF scores
        """
        tf = self.compute_tf(tokens)
        tfidf = {}
        
        for token in tokens:
            if token in self.idf:
                tfidf[token] = tf.get(token, 0) * self.idf[token]
        
        return tfidf
    
    @staticmethod
    def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """
        Compute cosine similarity between two TF-IDF vectors.
        
        Args:
            vec1: First TF-IDF vector
            vec2: Second TF-IDF vector
            
        Returns:
            Cosine similarity score between the vectors
        """
        # Get common terms
        common_terms = set(vec1.keys()) & set(vec2.keys())
        
        if not common_terms:
            return 0.0
        
        # Compute dot product
        dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
        
        # Compute magnitudes
        mag1 = math.sqrt(sum(val**2 for val in vec1.values()))
        mag2 = math.sqrt(sum(val**2 for val in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def build_index(self, df: pd.DataFrame) -> None:
        """
        Build TF-IDF index from a pandas DataFrame.
        
        Args:
            df: DataFrame containing documents with 'content', 'title', 'url', 'label' columns
        """
        print("\n=== Building TF-IDF Index ===")
        
        # Reset existing data
        self.__init__()
        self.doc_count = len(df)
        show_progress_bar = self.doc_count > 100
        update_freq = max(1, self.doc_count // 100) if show_progress_bar else self.doc_count
        
        print("Tokenizing documents...")
        documents_tokens = []
        
        for i, row in df.iterrows():
            tokens = tokenize(row['content'])
            documents_tokens.append(tokens)
            self.vocab.update(tokens)
            
            # Store document metadata
            self.documents.append({
                'id': i,
                'title': row['title'],
                'content': row['content'],
                'url': row['url'],
                'label': row['label'],
                'meta_image': row.get('meta_image', '')
            })
            
            if show_progress_bar and (i % update_freq == 0 or i == self.doc_count - 1):
                show_progress(i + 1, self.doc_count, "Tokenizing")
        
        if show_progress_bar:
            print()
        
        print(f"  ✓ Tokenized {self.doc_count:,} documents")
        print(f"  ✓ Vocabulary size: {len(self.vocab):,} unique terms")
        
        # Compute IDF
        self.idf = self.compute_idf(documents_tokens)
        
        # Compute TF-IDF vectors
        print("Computing TF-IDF vectors...")
        for i, tokens in enumerate(documents_tokens):
            tfidf_vec = self.compute_tfidf_vector(tokens)
            self.tfidf_vectors.append(tfidf_vec)
            
            if show_progress_bar and (i % update_freq == 0 or i == self.doc_count - 1):
                show_progress(i + 1, self.doc_count, "Computing TF-IDF")
        
        if show_progress_bar:
            print()
        
        print(f"  ✓ Built TF-IDF index for {self.doc_count:,} documents")
    
    def search(self, query: str, top_k: int = 10, filter_label: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            filter_label: Optional label to filter results (e.g., 'RAPPLER', 'GMA')
            
        Returns:
            List of document metadata dictionaries with similarity scores
        """
        # Tokenize query
        query_tokens = tokenize(query)
        
        if not query_tokens:
            return []
        
        # Compute TF-IDF vector for query
        query_tfidf = self.compute_tfidf_vector(query_tokens)
        
        # Compute similarities with all documents
        similarities = []
        for i, doc_vec in enumerate(self.tfidf_vectors):
            # Apply label filter if specified
            if filter_label and self.documents[i]['label'] != filter_label:
                continue
            
            similarity = self.cosine_similarity(query_tfidf, doc_vec)
            if similarity > 0:  # Only include documents with non-zero similarity
                similarities.append((i, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k results with metadata
        results = []
        for doc_id, score in similarities[:top_k]:
            doc_metadata = self.documents[doc_id].copy()
            doc_metadata['similarity_score'] = score
            results.append(doc_metadata)
        
        return results
    
    def save_index(self, filepath: str) -> None:
        """
        Save the TF-IDF index to disk.
        
        Args:
            filepath: Path to save the index file
        """
        print("\nSaving TF-IDF index...")
        save_dir = os.path.dirname(filepath)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        
        index_data = {
            'documents': self.documents,
            'tfidf_vectors': self.tfidf_vectors,
            'idf': self.idf,
            'vocab': list(self.vocab),
            'doc_count': self.doc_count
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"  ✓ Saved TF-IDF index to {filepath}")
    
    def load_index(self, filepath: str) -> None:
        """
        Load a TF-IDF index from disk.
        
        Args:
            filepath: Path to the index file
        """
        print("\nLoading TF-IDF index...")
        
        with open(filepath, 'rb') as f:
            index_data = pickle.load(f)
        
        self.documents = index_data['documents']
        self.tfidf_vectors = index_data['tfidf_vectors']
        self.idf = index_data['idf']
        self.vocab = set(index_data['vocab'])
        self.doc_count = index_data['doc_count']
        
        print(f"  ✓ Loaded TF-IDF index with {self.doc_count:,} documents")
        print(f"  ✓ Vocabulary size: {len(self.vocab):,} terms")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the TF-IDF model to a dictionary for MongoDB storage.
        
        Returns:
            Dictionary containing all necessary model data
        """
        return {
            'documents': self.documents,
            'tfidf_vectors': self.tfidf_vectors,
            'idf': self.idf,
            'vocab': list(self.vocab),
            'doc_count': self.doc_count
        }
    
    def load_from_dict(self, model_data: Dict[str, Any]) -> None:
        """
        Load TF-IDF model data from a dictionary.
        
        Args:
            model_data: Dictionary containing model data from MongoDB
        """
        self.documents = model_data.get('documents', [])
        self.tfidf_vectors = model_data.get('tfidf_vectors', [])
        self.idf = model_data.get('idf', {})
        self.vocab = set(model_data.get('vocab', []))
        self.doc_count = model_data.get('doc_count', 0)
        
        print(f"  ✓ Loaded TF-IDF model with {self.doc_count:,} documents from dictionary")
        print(f"  ✓ Vocabulary size: {len(self.vocab):,} terms")
