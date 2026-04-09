import numpy as np
from collections import Counter
import math
from pymongo import MongoClient
import os, sys
from typing import List, Dict, Tuple
import pickle

# Add parent directory to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from src.utils.tokenizer import tokenize
from src.utils.progress import show_progress

class TFIDFVectorizer:
    """TF-IDF Vectorizer for document retrieval and ranking"""
    
    def __init__(self, mongodb_uri="mongodb://localhost:27017/", db_name="nlp_search_engine"):
        """Initialize TF-IDF Vectorizer with MongoDB connection"""
        self.client = MongoClient(mongodb_uri)
        self.db = self.client[db_name]
        self.vocabulary = {}
        self.idf_scores = {}
        self.doc_count = 0
        
    def build_vocabulary(self, documents: List[Dict]) -> Dict[str, int]:
        """Build vocabulary from all documents"""
        print("Building vocabulary...")
        vocab_set = set()
        
        for i, doc in enumerate(documents):
            tokens = tokenize(doc.get('content', ''))
            vocab_set.update(tokens)
            
            if i % 100 == 0:
                show_progress(i + 1, len(documents), "Building vocabulary")
        
        # Create vocabulary with index mapping
        self.vocabulary = {term: idx for idx, term in enumerate(sorted(vocab_set))}
        print(f"\n✓ Vocabulary built: {len(self.vocabulary):,} unique terms")
        return self.vocabulary
    
    def calculate_tf(self, doc_tokens: List[str]) -> Dict[str, float]:
        """Calculate Term Frequency for a document"""
        token_counts = Counter(doc_tokens)
        total_tokens = len(doc_tokens)
        
        if total_tokens == 0:
            return {}
        
        # Normalized TF = count(term) / total_tokens
        tf_scores = {
            term: count / total_tokens 
            for term, count in token_counts.items()
        }
        return tf_scores
    
    def calculate_idf(self, documents: List[Dict]) -> Dict[str, float]:
        """Calculate Inverse Document Frequency for all terms"""
        print("Calculating IDF scores...")
        doc_freq = Counter()  # How many documents contain each term
        self.doc_count = len(documents)
        
        for i, doc in enumerate(documents):
            tokens = set(tokenize(doc.get('content', '')))
            doc_freq.update(tokens)
            
            if i % 100 == 0:
                show_progress(i + 1, self.doc_count, "Calculating IDF")
        
        # IDF = log(total_docs / (1 + docs_with_term))
        self.idf_scores = {
            term: math.log(self.doc_count / (1 + freq))
            for term, freq in doc_freq.items()
        }
        
        print(f"\n✓ IDF calculated for {len(self.idf_scores):,} terms")
        return self.idf_scores
    
    def calculate_tfidf(self, doc_tokens: List[str]) -> Dict[str, float]:
        """Calculate TF-IDF scores for a document"""
        tf_scores = self.calculate_tf(doc_tokens)
        
        tfidf_scores = {}
        for term, tf in tf_scores.items():
            if term in self.idf_scores:
                tfidf_scores[term] = tf * self.idf_scores[term]
        
        return tfidf_scores
    
    def vectorize_documents(self, documents: List[Dict]) -> np.ndarray:
        """Convert all documents to TF-IDF vectors"""
        print("Vectorizing documents...")
        vectors = []
        
        for i, doc in enumerate(documents):
            tokens = tokenize(doc.get('content', ''))
            tfidf_scores = self.calculate_tfidf(tokens)
            
            # Create vector based on vocabulary
            vector = np.zeros(len(self.vocabulary))
            for term, score in tfidf_scores.items():
                if term in self.vocabulary:
                    idx = self.vocabulary[term]
                    vector[idx] = score
            
            vectors.append(vector)
            
            if i % 100 == 0:
                show_progress(i + 1, len(documents), "Vectorizing")
        
        print(f"\n✓ Vectorized {len(vectors):,} documents")
        return np.array(vectors)
    
    def index_documents(self, documents: List[Dict]):
        """Build complete TF-IDF index and store in MongoDB"""
        print("\n=== Building TF-IDF Index ===")
        
        # Build vocabulary and calculate IDF
        self.build_vocabulary(documents)
        self.calculate_idf(documents)
        
        # Clear existing indexes
        self.db.tfidf_index.delete_many({})
        self.db.inverted_index.delete_many({})
        
        print("\nIndexing documents...")
        batch_size = 1000
        tfidf_batch = []
        inverted_index = {}
        
        for i, doc in enumerate(documents):
            doc_id = doc.get('doc_id', str(doc.get('_id')))
            tokens = tokenize(doc.get('content', ''))
            
            # Calculate TF-IDF for this document
            tfidf_scores = self.calculate_tfidf(tokens)
            
            # Prepare TF-IDF index entries
            for term, score in tfidf_scores.items():
                # Find positions of term in document
                positions = [j for j, t in enumerate(tokens) if t == term]
                
                tfidf_batch.append({
                    'doc_id': doc_id,
                    'term': term,
                    'tf': self.calculate_tf(tokens).get(term, 0),
                    'tfidf_score': score,
                    'positions': positions
                })
                
                # Build inverted index
                if term not in inverted_index:
                    inverted_index[term] = {
                        'term': term,
                        'idf': self.idf_scores.get(term, 0),
                        'document_frequency': 0,
                        'postings': []
                    }
                
                inverted_index[term]['document_frequency'] += 1
                inverted_index[term]['postings'].append({
                    'doc_id': doc_id,
                    'tf': self.calculate_tf(tokens).get(term, 0),
                    'positions': positions
                })
            
            # Batch insert TF-IDF entries
            if len(tfidf_batch) >= batch_size:
                self.db.tfidf_index.insert_many(tfidf_batch)
                tfidf_batch = []
            
            if i % 100 == 0:
                show_progress(i + 1, len(documents), "Indexing")
        
        # Insert remaining TF-IDF entries
        if tfidf_batch:
            self.db.tfidf_index.insert_many(tfidf_batch)
        
        # Insert inverted index
        print("\nBuilding inverted index...")
        inverted_entries = list(inverted_index.values())
        if inverted_entries:
            self.db.inverted_index.insert_many(inverted_entries)
        
        # Create indexes for faster querying
        self.db.tfidf_index.create_index([('doc_id', 1), ('term', 1)])
        self.db.tfidf_index.create_index('term')
        self.db.tfidf_index.create_index('tfidf_score')
        self.db.inverted_index.create_index('term')
        
        print(f"\n✓ Indexed {len(documents):,} documents")
        print(f"✓ Created inverted index with {len(inverted_index):,} terms")
    
    def search(self, query: str, top_k: int = 10, category_filter: str = None) -> List[Dict]:
        """
        Search for documents using TF-IDF ranking
        Returns top-k documents with metadata
        """
        # Process query
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        
        print(f"\nSearching for: '{query}'")
        print(f"Query tokens: {query_tokens}")
        
        # Calculate query TF-IDF vector
        query_tf = self.calculate_tf(query_tokens)
        query_tfidf = {}
        
        for term in query_tokens:
            if term in self.idf_scores:
                query_tfidf[term] = query_tf[term] * self.idf_scores[term]
        
        if not query_tfidf:
            print("No matching terms found in index")
            return []
        
        # Find documents containing query terms
        doc_scores = {}
        
        for term, query_score in query_tfidf.items():
            # Get postings from inverted index
            inverted_entry = self.db.inverted_index.find_one({'term': term})
            
            if inverted_entry:
                for posting in inverted_entry['postings']:
                    doc_id = posting['doc_id']
                    
                    # Get document TF-IDF score for this term
                    tfidf_entry = self.db.tfidf_index.find_one({
                        'doc_id': doc_id,
                        'term': term
                    })
                    
                    if tfidf_entry:
                        doc_score = tfidf_entry['tfidf_score']
                        
                        # Accumulate cosine similarity score
                        if doc_id not in doc_scores:
                            doc_scores[doc_id] = 0
                        doc_scores[doc_id] += query_score * doc_score
        
        if not doc_scores:
            print("No documents found matching the query")
            return []
        
        # Sort by score and get top-k
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Fetch document metadata
        results = []
        for doc_id, score in sorted_docs:
            # Build query with optional category filter
            query_filter = {'doc_id': doc_id}
            if category_filter:
                query_filter['category'] = category_filter
            
            doc = self.db.documents.find_one(query_filter)
            
            if doc:
                # Calculate match details
                matching_terms = []
                for term in query_tokens:
                    if self.db.tfidf_index.find_one({'doc_id': doc_id, 'term': term}):
                        matching_terms.append(term)
                
                results.append({
                    'doc_id': doc_id,
                    'title': doc.get('title', 'Untitled'),
                    'content_preview': doc.get('content', '')[:200] + '...',
                    'url': doc.get('url', ''),
                    'category': doc.get('category', 'uncategorized'),
                    'score': score,
                    'matching_terms': matching_terms,
                    'metadata': doc.get('metadata', {})
                })
        
        print(f"\n✓ Found {len(results)} relevant documents")
        return results
    
    def get_similar_documents(self, doc_id: str, top_k: int = 5) -> List[Dict]:
        """Find similar documents using cosine similarity"""
        # Get the document's TF-IDF vector
        doc_terms = self.db.tfidf_index.find({'doc_id': doc_id})
        
        if not doc_terms:
            return []
        
        # Build document vector
        doc_vector = {}
        for entry in doc_terms:
            doc_vector[entry['term']] = entry['tfidf_score']
        
        # Calculate similarity with other documents
        similarities = {}
        
        for term, score in doc_vector.items():
            # Get all documents containing this term
            inverted_entry = self.db.inverted_index.find_one({'term': term})
            
            if inverted_entry:
                for posting in inverted_entry['postings']:
                    other_doc_id = posting['doc_id']
                    
                    if other_doc_id != doc_id:
                        if other_doc_id not in similarities:
                            similarities[other_doc_id] = 0
                        
                        # Get other document's score for this term
                        other_entry = self.db.tfidf_index.find_one({
                            'doc_id': other_doc_id,
                            'term': term
                        })
                        
                        if other_entry:
                            similarities[other_doc_id] += score * other_entry['tfidf_score']
        
        # Sort and get top-k similar documents
        sorted_similar = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        # Fetch document metadata
        results = []
        for similar_doc_id, similarity_score in sorted_similar:
            doc = self.db.documents.find_one({'doc_id': similar_doc_id})
            if doc:
                results.append({
                    'doc_id': similar_doc_id,
                    'title': doc.get('title', 'Untitled'),
                    'similarity_score': similarity_score,
                    'category': doc.get('category', 'uncategorized')
                })
        
        return results
    
    def save_model(self, filepath: str = "tfidf_model.pkl"):
        """Save TF-IDF model to file"""
        model_data = {
            'vocabulary': self.vocabulary,
            'idf_scores': self.idf_scores,
            'doc_count': self.doc_count
        }
        
        os.makedirs('trained_models', exist_ok=True)
        full_path = os.path.join('trained_models', filepath)
        
        with open(full_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"✓ TF-IDF model saved to {full_path}")
    
    def load_model(self, filepath: str = "tfidf_model.pkl"):
        """Load TF-IDF model from file"""
        full_path = os.path.join('trained_models', filepath)
        
        if not os.path.exists(full_path):
            print(f"Model file {full_path} not found")
            return False
        
        with open(full_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.vocabulary = model_data['vocabulary']
        self.idf_scores = model_data['idf_scores']
        self.doc_count = model_data['doc_count']
        
        print(f"✓ TF-IDF model loaded from {full_path}")
        return True


# Example usage
if __name__ == "__main__":
    # Initialize TF-IDF vectorizer
    vectorizer = TFIDFVectorizer()
    
    # Connect to MongoDB and fetch documents
    db = vectorizer.db
    
    # Fetch all documents
    documents = list(db.documents.find())
    
    if not documents:
        # Insert sample documents if collection is empty
        print("Inserting sample documents...")
        sample_docs = [
            {
                "doc_id": "DOC001",
                "title": "Introduction to Python Programming",
                "content": "Python is a high-level programming language. Python is easy to learn and widely used for web development, data science, and machine learning.",
                "category": "programming",
                "url": "https://example.com/python-intro"
            },
            {
                "doc_id": "DOC002",
                "title": "Machine Learning Basics",
                "content": "Machine learning is a subset of artificial intelligence. Machine learning algorithms learn from data. Python is popular for machine learning projects.",
                "category": "data_science",
                "url": "https://example.com/ml-basics"
            },
            {
                "doc_id": "DOC003",
                "title": "Web Development with JavaScript",
                "content": "JavaScript is essential for web development. JavaScript runs in browsers and enables interactive websites. Modern web development uses JavaScript frameworks.",
                "category": "web_development",
                "url": "https://example.com/js-web"
            }
        ]
        db.documents.insert_many(sample_docs)
        documents = sample_docs
    
    print(f"Found {len(documents)} documents in database")
    
    # Build TF-IDF index
    vectorizer.index_documents(documents)
    
    # Save the model
    vectorizer.save_model()
    
    # Test search functionality
    print("\n" + "="*50)
    print("TESTING SEARCH FUNCTIONALITY")
    print("="*50)
    
    # Test queries
    test_queries = [
        "python machine learning",
        "web development",
        "javascript",
        "artificial intelligence"
    ]
    
    for query in test_queries:
        results = vectorizer.search(query, top_k=3)
        
        print(f"\nQuery: '{query}'")
        print("-" * 30)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result['title']}")
                print(f"   Score: {result['score']:.4f}")
                print(f"   Category: {result['category']}")
                print(f"   Matching terms: {', '.join(result['matching_terms'])}")
                print(f"   Preview: {result['content_preview'][:100]}...")
        else:
            print("   No results found")
    
    # Test similar documents
    print("\n" + "="*50)
    print("TESTING SIMILAR DOCUMENTS")
    print("="*50)
    
    if documents:
        test_doc_id = documents[0].get('doc_id')
        print(f"\nFinding documents similar to: {documents[0].get('title')}")
        similar_docs = vectorizer.get_similar_documents(test_doc_id, top_k=2)
        
        if similar_docs:
            for doc in similar_docs:
                print(f"  - {doc['title']} (similarity: {doc['similarity_score']:.4f})")
        else:
            print("  No similar documents found")