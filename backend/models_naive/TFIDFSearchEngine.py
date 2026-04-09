import math
import pickle
import os
import numpy as np
from collections import defaultdict, Counter
import pandas as pd
import sys

# Get the parent directory for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from src.utils.tokenizer import tokenize
from src.utils.progress import show_progress

class TFIDFSearchEngine:
    def __init__(self):
        self.documents = []  # List of document metadata
        self.tfidf_vectors = []  # TF-IDF vectors for each document
        self.idf = {}  # IDF scores for each term
        self.vocab = set()  # All unique terms
        self.doc_count = 0
        
    def compute_tf(self, tokens):
        """Compute term frequency for a document"""
        tf = {}
        total_tokens = len(tokens)
        token_counts = Counter(tokens)
        
        for token, count in token_counts.items():
            # Normalized TF: count / total tokens
            tf[token] = count / total_tokens if total_tokens > 0 else 0
        
        return tf
    
    def compute_idf(self, documents_tokens):
        """Compute IDF for all terms in the corpus"""
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
            idf[token] = math.log(total_docs / freq)
        
        print(f"  ✓ Computed IDF for {len(idf):,} unique terms")
        return idf
    
    def compute_tfidf_vector(self, tokens):
        """Compute TF-IDF vector for a document"""
        tf = self.compute_tf(tokens)
        tfidf = {}
        
        for token in tokens:
            if token in self.idf:
                tfidf[token] = tf.get(token, 0) * self.idf[token]
        
        return tfidf
    
    def cosine_similarity(self, vec1, vec2):
        """Compute cosine similarity between two TF-IDF vectors"""
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
    
    def build_index(self, df):
        """Build TF-IDF index from DataFrame with metadata"""
        print("\n=== Building TF-IDF Index ===")
        
        # Extract documents and metadata
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
    
    def search(self, query, top_k=10, filter_label=None):
        """
        Search for documents similar to query
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            filter_label: Optional label to filter results (e.g., 'RAPPLER', 'GMA')
        
        Returns:
            List of tuples: (document_metadata, similarity_score)
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
    
    def save_index(self, filepath):
        """Save the TF-IDF index to disk"""
        print(f"\nSaving TF-IDF index...")
        save_dir = 'trained_models'
        os.makedirs(save_dir, exist_ok=True)
        full_path = os.path.join(save_dir, filepath)
        
        index_data = {
            'documents': self.documents,
            'tfidf_vectors': self.tfidf_vectors,
            'idf': self.idf,
            'vocab': self.vocab,
            'doc_count': self.doc_count
        }
        
        with open(full_path, 'wb') as f:
            pickle.dump(index_data, f)
        
        file_size = os.path.getsize(full_path) / (1024 * 1024)
        print(f"  ✓ Index saved to {full_path} ({file_size:.2f} MB)")
    
    def load_index(self, filepath):
        """Load the TF-IDF index from disk"""
        load_dir = 'trained_models'
        full_path = os.path.join(load_dir, filepath)
        
        if not os.path.exists(full_path):
            print(f"Index file {full_path} not found")
            return False
        
        with open(full_path, 'rb') as f:
            index_data = pickle.load(f)
        
        self.documents = index_data['documents']
        self.tfidf_vectors = index_data['tfidf_vectors']
        self.idf = index_data['idf']
        self.vocab = index_data['vocab']
        self.doc_count = index_data['doc_count']
        
        print(f"  ✓ Index loaded from {full_path}")
        print(f"  ✓ Loaded {self.doc_count:,} documents with {len(self.vocab):,} unique terms")
        return True


class IntegratedSearchEngine:
    """
    Integrated search engine combining TF-IDF retrieval and Naive Bayes classification
    """
    def __init__(self, tfidf_index_path, nb_model_path):
        self.tfidf_engine = TFIDFSearchEngine()
        self.nb_classifier = None
        
        # Load TF-IDF index
        print("Loading TF-IDF index...")
        self.tfidf_engine.load_index(tfidf_index_path)
        
        # Load Naive Bayes model
        print("\nLoading Naive Bayes classifier...")
        self.load_nb_model(nb_model_path)
    
    def load_nb_model(self, filepath):
        """Load Naive Bayes model"""
        load_dir = 'trained_models'
        full_path = os.path.join(load_dir, filepath)
        
        if not os.path.exists(full_path):
            print(f"Model file {full_path} not found")
            return
        
        with open(full_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.nb_classifier = {
            'class_counts': model_data['class_counts'],
            'class_word_counts': model_data['class_word_counts'],
            'vocab_size': model_data['vocab_size']
        }
        
        print(f"  ✓ Classifier loaded from {full_path}")
        print(f"  ✓ Classes: {list(model_data['class_counts'].keys())}")
    
    def predict_class(self, text):
        """Predict document class using Naive Bayes"""
        from bag_of_words import predict
        
        result = predict(
            text,
            self.nb_classifier['class_counts'],
            self.nb_classifier['class_word_counts'],
            self.nb_classifier['vocab_size'],
            is_log=False
        )
        return result
    
    def search(self, query, top_k=10, filter_by_source=None, classify_query=False):
        """
        Advanced search with optional classification
        
        Args:
            query: Search query string
            top_k: Number of results to return
            filter_by_source: Optional source label filter
            classify_query: If True, classify the query and filter results
        
        Returns:
            dict with results and metadata
        """
        results = {
            'query': query,
            'total_results': 0,
            'documents': [],
            'query_classification': None
        }
        
        # Optional: Classify the query
        if classify_query and self.nb_classifier:
            query_class = self.predict_class(query)
            results['query_classification'] = query_class
            
            # Use predicted class as filter if confidence is high
            if query_class['confidence'] > 0.6:
                filter_by_source = query_class['prediction']
                print(f"Query classified as '{filter_by_source}' "
                      f"({query_class['confidence']:.1%} confidence)")
        
        # Perform TF-IDF search
        search_results = self.tfidf_engine.search(
            query,
            top_k=top_k,
            filter_label=filter_by_source
        )
        
        results['total_results'] = len(search_results)
        results['documents'] = search_results
        
        return results
    
    def display_results(self, results):
        """Pretty print search results"""
        print(f"\n{'='*80}")
        print(f"SEARCH RESULTS FOR: '{results['query']}'")
        print(f"{'='*80}")
        
        if results['query_classification']:
            qc = results['query_classification']
            print(f"\nQuery Classification: {qc['prediction']} "
                  f"(confidence: {qc['confidence']:.1%})")
            print(f"Probabilities: {', '.join(f'{k}: {v:.1%}' for k, v in qc['probabilities'].items())}")
        
        print(f"\nFound {results['total_results']} relevant documents:\n")
        
        for i, doc in enumerate(results['documents'], 1):
            print(f"{i}. [{doc['label']}] {doc['title']}")
            print(f"   Similarity: {doc['similarity_score']:.4f}")
            print(f"   URL: {doc['url']}")
            print(f"   Preview: {doc['content'][:150]}...")
            print()


if __name__ == "__main__":
    # Example 1: Build TF-IDF index from scratch
    BUILD_INDEX = True  # Set to True to rebuild index
    
    if BUILD_INDEX:
        print("=== Building TF-IDF Index ===")
        df = pd.read_pickle("data/datasets.pkl")
        
        # Clean data
        df['content'] = df['content'].fillna('')
        df['title'] = df['title'].fillna('Untitled')
        df['url'] = df['url'].fillna('')
        df['label'] = df['label'].fillna('unknown')
        
        print(f"\nDataset info:")
        print(f"Total documents: {len(df):,}")
        print(f"Labels: {df['label'].value_counts().to_dict()}")
        
        # Build and save index
        tfidf_engine = TFIDFSearchEngine()
        tfidf_engine.build_index(df)
        tfidf_engine.save_index("tfidf_index_v1.pkl")
    
    # Example 2: Load and use integrated search engine
    print("\n=== Integrated Search Engine Demo ===")
    
    search_engine = IntegratedSearchEngine(
        tfidf_index_path="tfidf_index_v1.pkl",
        nb_model_path="bow_naive_bayes_model_v2.pkl"
    )
    
    # Test searches
    test_queries = [
        "Typhoon nando",
        "COVID-19 vaccine update",
        "election results",
        "basketball championship"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Searching: '{query}'")
        print(f"{'='*80}")
        
        # Search with query classification
        results = search_engine.search(
            query,
            top_k=10,
            classify_query=True
        )
        
        search_engine.display_results(results)
        
        print("\n" + "-"*80)
        input("Press Enter for next search...")