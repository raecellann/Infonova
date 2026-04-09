from fastapi import HTTPException, status
import os
import sys
import pickle
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
from pymongo.collection import Collection

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from models.tfidf import TFIDFSearchEngine, IntegratedSearchEngine
from models.bow_naive_bayes import load_model, predict
from src.core.mongodb_connect import create_connection


class TFIDFController:
    """
    Controller for handling TF-IDF search operations.
    """
    
    def __init__(self, data_path: Optional[str] = None, force_retrain: bool = False):
        """
        Initialize the TF-IDF search controller with integrated Naive Bayes and MongoDB.
        
        Args:
            data_path: Path to the dataset or directory containing the dataset
            force_retrain: If True, force retraining the model even if a saved version exists
        """
        self.initialized = False
        self.model_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'trained_models'
        )
        self.model_path = os.path.join(self.model_dir, 'tfidf_model.pkl')
        self.nb_model_path = os.path.join(self.model_dir, 'bow_naive_bayes_model_v1.pkl')
        
        # Ensure models directory exists
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Set default data path if not provided
        if data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_path = os.path.join(base_dir, 'data')
        self.data_path = data_path
        
        # MongoDB setup
        self.db_name = 'nlp_finals'
        self.collection_name = 'tfidf_models'
        self.mongo_client = None
        self.db = None
        self.collection = None
        # self._connect_to_mongodb()
        
        # Try to load or train models
        try:
            # Load TF-IDF model
            tfidf_loaded = self._load_tfidf_model(force_retrain)
            
            if tfidf_loaded:
                # Load Naive Bayes model if TF-IDF loaded successfully
                self._load_naive_bayes_model()
                self.initialized = True
                print("✅ TF-IDF controller initialized successfully")
            else:
                # If loading failed, try to train a new model
                print("No valid model found, training a new one...")
                
        except Exception as e:
            print(f"❌ Error during initialization: {e}")
            print("Attempting to train a new model...")
            try:
                self._train_model()
            except Exception as train_error:
                print(f"❌ Failed to train model: {train_error}")
            self.initialized = False

    def _connect_to_mongodb(self) -> None:
        """Connect to MongoDB and set up the collection."""
        try:
            print("\n" + "="*50)
            print("MongoDB Connection Debug")
            print("="*50)
            
            # Connect to MongoDB
            print(f"Connecting to MongoDB with URI: {os.getenv('URI', 'Not set')}")
            self.mongo_client = create_connection()
            print("✓ Connected to MongoDB server")
            
            # List all databases (for debugging)
            try:
                db_list = self.mongo_client.list_database_names()
                print(f"Available databases: {db_list}")
            except Exception as e:
                print(f"❌ Error listing databases: {e}")
            
            # Access the database and collection
            self.db = self.mongo_client[self.db_name]
            self.collection = self.db[self.collection_name]
            print(f"✓ Accessed collection: {self.db_name}.{self.collection_name}")
            
            # Check if collection exists and has documents
            try:
                count = self.collection.count_documents({})
                print(f"✓ Collection contains {count} documents")
                
                # List all model_ids for debugging
                model_ids = self.collection.distinct("model_id")
                print(f"Found model IDs in collection: {model_ids}")
                
            except Exception as e:
                print(f"❌ Error checking collection: {e}")
            
            # Create indexes if they don't exist
            try:
                # Drop existing URL index if it exists
                try:
                    self.collection.drop_index("url_1")
                    print("Dropped existing URL index")
                except Exception as e:
                    if "not found" in str(e).lower():
                        print("No existing URL index to drop")
                    else:
                        print(f"❌ Error dropping URL index: {e}")
                
                # Create non-unique index on URL
                self.collection.create_index([("url", 1)], unique=False, sparse=True)
                print("Created non-unique sparse index on URL field")
                
                # Create other indexes
                self.collection.create_index([("label", 1)])
                self.collection.create_index([("title", "text"), ("content", "text")])
                print("✓ Created all indexes")
                
            except Exception as e:
                print(f"❌ Error creating indexes: {e}")
                raise
            
            print(f"✅ Successfully connected to MongoDB collection: {self.db_name}.{self.collection_name}")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"\n❌❌❌ CRITICAL ERROR: Failed to connect to MongoDB: {e}")
            print("Please check your MongoDB connection settings and ensure the server is running.")
            print("="*50 + "\n")
            raise
            null_url_count = self.collection.count_documents({"url": {"$in": [None, ""]}})
            
            # Create indexes based on whether we have null URLs or not
            if null_url_count > 0:
                print(f"⚠️  Found {null_url_count} documents with null/empty URLs. Creating non-unique URL index.")
                # Create non-unique index on URL
                self.collection.create_index([("url", 1)], unique=False)
            else:
                # Create unique index on URL if no null/empty URLs are found
                try:
                    self.collection.create_index([("url", 1)], unique=True)
                except pymongo.errors.OperationFailure as e:
                    if "E11000 duplicate key error" in str(e):
                        print("⚠️  Duplicate key error while creating unique URL index. Creating non-unique index instead.")
                        self.collection.create_index([("url", 1)], unique=False)
                    else:
                        raise
            
            # Create other indexes
            self.collection.create_index([("label", 1)])
            self.collection.create_index([("title", "text"), ("content", "text")])
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            raise

    def _load_tfidf_model(self, force_retrain: bool = False) -> bool:
        """Load TF-IDF model from file or MongoDB."""
        print("\n" + "="*50)
        print("TF-IDF Model Loading Process")
        print("="*50)
        
        # Get model_id from environment or use default
        model_id = os.getenv('TFIDF_INDEX', 'tfidf_model')
        
        try:
            # First try to load from MongoDB if available and not forced to retrain
            if not force_retrain and self.collection is not None:
                print(f"\n[1/2] Attempting to load model from MongoDB (ID: {model_id})...")
                try:
                    # First, get the total number of chunks without sorting
                    total_chunks = self.collection.count_documents({"model_id": model_id})
                    
                    if total_chunks == 0:
                        print("  ℹ️  No model chunks found in MongoDB")
                        raise ValueError("No model chunks found")
                    
                    print(f"  ℹ️  Found model with {total_chunks} chunks in MongoDB")
                    
                    # First, get the total_chunks from the first document
                    first_chunk = self.collection.find_one(
                        {"model_id": model_id},
                        {"total_chunks": 1, "_id": 0}
                    )
                    
                    if not first_chunk or 'total_chunks' not in first_chunk:
                        print("  ❌ Could not determine total chunks from database")
                        raise ValueError("Invalid model data in database")
                        
                    total_expected_chunks = first_chunk['total_chunks']
                    print(f"  ℹ️  Expecting {total_expected_chunks} chunks in total")
                    
                    # Fetch chunks one by one using their exact chunk numbers
                    chunks = []
                    for chunk_num in range(total_expected_chunks):
                        chunk = self.collection.find_one(
                            {"model_id": model_id, "chunk_num": chunk_num},
                            {"chunk_num": 1, "data": 1, "total_chunks": 1, "_id": 0}
                        )
                        if chunk:
                            chunks.append(chunk)
                            print(f"  ✓ Loaded chunk {chunk_num + 1}/{total_expected_chunks}", end='\r')
                        else:
                            print(f"\n  ❌ Missing chunk {chunk_num}")
                            raise ValueError(f"Missing chunk {chunk_num} in database")
                    
                    print("\n  ✓ All chunks loaded successfully")
                    
                    # Verify we have all chunks
                    if len(chunks) != total_expected_chunks:
                        print(f"  ❌ Incomplete model: found {len(chunks)} of {total_expected_chunks} chunks")
                        raise ValueError("Incomplete model chunks in database")
                    
                    # Reassemble the chunks in order
                    chunks.sort(key=lambda x: x['chunk_num'])
                    combined = b''.join(chunk['data'] for chunk in chunks)
                    
                    # Create a temporary file to load the model
                    temp_path = os.path.join(self.model_dir, 'temp_loaded_model.pkl')
                    try:
                        with open(temp_path, 'wb') as f:
                            f.write(combined)
                        
                        # Load the model from the temporary file
                        self.tfidf_engine = TFIDFSearchEngine()
                        self.tfidf_engine.load_index(temp_path)
                        
                        if hasattr(self.tfidf_engine, 'doc_count') and self.tfidf_engine.doc_count > 0:
                            print(f"  ✓ Successfully loaded TF-IDF model with {self.tfidf_engine.doc_count} documents")
                            print(f"  🎯 SOURCE: MongoDB (collection: {self.db_name}.{self.collection_name})")
                            print("\n" + "="*50 + "\n")
                            return True
                            
                        print("  ❌ Loaded model has no documents")
                        return False
                        
                    except Exception as e:
                        print(f"  ❌ Error loading model from chunks: {e}")
                        if os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                        raise
                    finally:
                        # Clean up the temporary file
                        if 'temp_path' in locals() and os.path.exists(temp_path):
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                
                except Exception as e:
                    print(f"  ❌ Error loading from MongoDB: {e}")
                    if 'chunks' in locals() and chunks:
                        print(f"  ℹ️  Found chunks: {[c['chunk_num'] for c in chunks]}")
                    return False
            
            # Fall back to file-based loading if MongoDB load fails or is not available
            print("\n[2/2] Falling back to file-based loading...")
            try:
                model_files = [f for f in os.listdir(self.model_dir) 
                             if f.startswith('tfidf_') and f.endswith('.pkl')]
                              
                if not model_files:
                    print(f"  ❌ No model files found in directory: {self.model_dir}")
                    return False
                
                # Sort by modification time (newest first)
                model_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.model_dir, x)), 
                               reverse=True)
                model_path = os.path.join(self.model_dir, model_files[0])
                
                print(f"  ✓ Found model file: {model_path}")
                
                # Initialize and load the model
                self.tfidf_engine = TFIDFSearchEngine()
                self.tfidf_engine.load_index(model_path)
                
                if hasattr(self.tfidf_engine, 'doc_count') and self.tfidf_engine.doc_count > 0:
                    print(f"  ✓ Successfully loaded TF-IDF model with {self.tfidf_engine.doc_count} documents")
                    print(f"  ✓ SOURCE: Local file ({model_path})")
                    
                    # Save the loaded model to MongoDB for future use
                    if self.collection is not None:
                        print("  💾 Saving model to MongoDB for future use...")
                        if self._save_model_to_mongodb():
                            print("  ✓ Successfully saved model to MongoDB")
                        else:
                            print("  ❌ Failed to save model to MongoDB")
                    
                    print("\n" + "="*50 + "\n")
                    return True
                    
                print("  ❌ Loaded model has no documents or invalid format")
                    
            except Exception as e:
                print(f"  ❌ Error loading from file: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n❌ No valid model could be loaded from any source")
            print("\n" + "="*50 + "\n")
            return False
            
        except Exception as e:
            print(f"\n❌ Unexpected error in _load_tfidf_model: {e}")
            import traceback
            traceback.print_exc()
            print("\n" + "="*50 + "\n")
            return False

    def _chunk_data(self, data, chunk_size=1024*1024):
        """Split data into chunks of specified size."""
        serialized = pickle.dumps(data)
        for i in range(0, len(serialized), chunk_size):
            yield {
                'chunk': serialized[i:i + chunk_size],
                'chunk_num': i // chunk_size,
                'total_chunks': (len(serialized) + chunk_size - 1) // chunk_size
            }
            
    def _save_model_to_mongodb(self) -> bool:
        """Save the current TF-IDF model to MongoDB in chunks."""
        if not hasattr(self, 'tfidf_engine') or self.collection is None:
            print("❌ Cannot save model: TF-IDF engine not initialized or no MongoDB connection")
            return False
            
        try:
            # First, save the model to a temporary file
            temp_path = os.path.join(self.model_dir, 'temp_tfidf_model.pkl')
            self.tfidf_engine.save_index(temp_path)
            
            # Read the binary data from the file
            with open(temp_path, 'rb') as f:
                model_data = f.read()
                
            # Clean up the temporary file
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Get model_id from environment or use default
            model_id = os.getenv('TFIDF_INDEX', 'tfidf_model')
            print(f"  💾 Saving model with ID: {model_id}")
            
            # Delete any existing model chunks (without allow_disk_use)
            delete_result = self.collection.delete_many({"model_id": model_id})
            print(f"  ♻️  Deleted {delete_result.deleted_count} old model chunks")
            
            # Save each chunk as a separate document
            chunk_size = 15 * 1024 * 1024  # 15MB chunks (under MongoDB's 16MB limit)
            total_chunks = (len(model_data) + chunk_size - 1) // chunk_size
            
            for i in range(total_chunks):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size
                chunk = model_data[start_idx:end_idx]
                
                chunk_doc = {
                    "model_id": model_id,  # Using the model_id from environment
                    "chunk_num": i,
                    "total_chunks": total_chunks,
                    "data": chunk,
                    "last_updated": datetime.utcnow()
                }
                self.collection.insert_one(chunk_doc)
            
            print(f"✓ TF-IDF model saved to MongoDB in {total_chunks} chunks")
            return True
                
        except Exception as e:
            print(f"❌ Error saving TF-IDF model to MongoDB: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _load_naive_bayes_model(self) -> None:
        """Load the Naive Bayes model."""
        try:
            if os.path.exists(self.nb_model_path):
                print("Loading Naive Bayes model...")
                self.nb_model = load_model(os.path.basename(self.nb_model_path))
                if self.nb_model and len(self.nb_model) == 3:
                    print("✓ Naive Bayes model loaded successfully")
                    self.use_nb = True
                    return
            
            print("⚠ Warning: Naive Bayes model not found or invalid. Only TF-IDF will be used.")
            self.use_nb = False
            
        except Exception as e:
            print(f"Error loading Naive Bayes model: {e}")
            self.use_nb = False

    def _train_model(self) -> None:
        """Train the TF-IDF model with available data and save to MongoDB."""
        try:
            print("Training TF-IDF model...")
            self.initialized = False  # Reset initialized flag before training
            
            # Look for dataset files
            dataset_files = []
            if os.path.isdir(self.data_path):
                dataset_files = [f for f in os.listdir(self.data_path) if f.endswith(('.csv', '.pkl'))]
            elif os.path.isfile(self.data_path):
                dataset_files = [os.path.basename(self.data_path)]
            
            if not dataset_files:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No dataset files found for training"
                )
            
            # Try to load and train with each dataset file
            trained = False
            for dataset_file in dataset_files:
                try:
                    file_path = os.path.join(self.data_path, dataset_file)
                    print(f"Attempting to train with: {dataset_file}")
                    
                    if dataset_file.endswith('.csv'):
                        df = pd.read_csv(file_path)
                    elif dataset_file.endswith('.pkl'):
                        df = pd.read_pickle(file_path)
                    else:
                        continue
                    
                    # Check required columns
                    required_columns = ['title', 'content']
                    if not all(col in df.columns for col in required_columns):
                        print(f"Skipping {dataset_file}: missing required columns")
                        continue
                    
                    # Train the model
                    documents = []
                    for _, row in df.iterrows():
                        doc = {
                            'title': row.get('title', ''),
                            'content': row.get('content', ''),
                            'url': row.get('url', ''),
                            'label': row.get('label', 'UNKNOWN'),
                            'meta_image': row.get('meta_image', '')
                        }
                        documents.append(doc)
                    
                    self.tfidf_engine.train(documents)
                    trained = True
                    print(f"✓ Successfully trained TF-IDF model with {len(documents)} documents from {dataset_file}")
                    break
                    
                except Exception as e:
                    print(f"Error training with {dataset_file}: {e}")
                    continue
            
            if not trained:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not train model with any available dataset"
                )
                
            # Save the trained model
            model_filename = f"tfidf_model_v{len(self.tfidf_engine.documents)}.pkl"
            model_path = os.path.join(self.model_dir, model_filename)
            self.tfidf_engine.save_index(model_path)
            print(f"✓ Model saved to: {model_path}")
            
            self.initialized = True
            
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Error training model: {str(e)}"
            print(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )

    def search(self, 
               query: str, 
               top_k: int = 10, 
               min_score: float = 0.1,
               use_naive_bayes: bool = True,
               filter_label: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform search using TF-IDF and optionally Naive Bayes.
        
        Args:
            query: Search query string
            top_k: Number of top results to return
            min_score: Minimum similarity score threshold (0.0 to 1.0)
            use_naive_bayes: Whether to use Naive Bayes for re-ranking
            filter_label: Optional label to filter results by source (e.g., 'GMA', 'RAPPLER')
            
        Returns:
            List of search results with complete document information including:
            - id: Document ID
            - title: Article title
            - content: Main content
            - url: Source URL
            - label: Source label (e.g., 'GMA', 'RAPPLER')
            - meta_image: URL of the article's main image
            - published_date: Publication date
            - author: Article author (if available)
            - similarity_score: Relevance score (0.0 to 1.0)
            - nb_probability: Naive Bayes probability (if used)
        """
        try:
            if not self.initialized:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Search engine not initialized"
                )
            
            if not query or not query.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Query cannot be empty"
                )
            
            print(f"Searching for: '{query}' (top_k: {top_k}, min_score: {min_score})")
            
            # First try to get results from MongoDB if available
            tfidf_results = []
            
            # If we have a direct search method in the engine, use it
            if hasattr(self.tfidf_engine, 'search'):
                tfidf_results = self.tfidf_engine.search(query, top_k=top_k * 2)
            # Otherwise, try to search in MongoDB
            elif self.collection is not None:
                try:
                    # Text search with highlighting in MongoDB
                    search_query = {
                        "$text": {"$search": query}
                    }
                    
                    # Add source filter if specified
                    if filter_label:
                        search_query["label"] = filter_label.upper()
                    
                    # Projection to include all relevant fields
                    projection = {
                        "title": 1,
                        "content": 1,
                        "url": 1,
                        "label": 1,
                        "meta_image": 1,
                        "published_date": 1,
                        "author": 1,
                        "score": {"$meta": "textScore"}
                    }
                    
                    cursor = self.collection.find(
                        search_query,
                        projection
                    ).sort([("score", {"$meta": "textScore"})]).limit(top_k * 2)
                    
                    tfidf_results = [{
                        'id': str(doc.get('_id', '')),  # Convert ObjectId to string
                        'title': doc.get('title', ''),
                        'content': doc.get('content', ''),
                        'url': doc.get('url', ''),
                        'label': doc.get('label', 'UNKNOWN'),
                        'meta_image': doc.get('meta_image', ''),
                        'published_date': doc.get('published_date', ''),
                        'author': doc.get('author', ''),
                        'similarity_score': float(doc.get('score', 0.0))  # Ensure it's a float
                    } for doc in cursor]
                    
                    print(f"Found {len(tfidf_results)} results from MongoDB")
                    
                except Exception as e:
                    print(f"Error searching in MongoDB: {e}")
                    # Fall back to empty results if MongoDB search fails
                    tfidf_results = []
            
            if not tfidf_results:
                print("No results found in both TF-IDF engine and MongoDB")
                return []
            
            # Apply score normalization if needed
            max_score = max((doc.get('similarity_score', 0) for doc in tfidf_results), default=1.0)
            if max_score > 0:
                for doc in tfidf_results:
                    doc['similarity_score'] = min(1.0, doc.get('similarity_score', 0) / max_score)
            
            # Initialize variables for probability-based distribution
            class_probs = {}
            
            # Apply Naive Bayes scoring if available and requested
            if use_naive_bayes and hasattr(self, 'use_nb') and self.use_nb and hasattr(self, 'nb_model'):
                try:
                    # Get Naive Bayes predictions for the query
                    nb_result = predict(query, *self.nb_model)
                    print(f"Naive Bayes prediction: {nb_result}")
                    
                    # Get probabilities for each class
                    class_probs = nb_result.get('probabilities', {})
                    
                    # Calculate combined scores
                    for doc in tfidf_results:
                        doc_label = doc.get('label', 'UNKNOWN')
                        # Get the probability for this document's label
                        label_prob = class_probs.get(doc_label, 0.0)
                        # Combine TF-IDF score with Naive Bayes probability
                        # Using a weighted average (e.g., 70% TF-IDF, 30% NB)
                        tfidf_score = doc.get('similarity_score', 0)
                        combined_score = (0.7 * tfidf_score) + (0.3 * label_prob)
                        doc['similarity_score'] = min(1.0, combined_score)  # Ensure score doesn't exceed 1.0
                        doc['nb_probability'] = float(label_prob)  # Store as float for JSON serialization
                    
                    # Re-sort by combined score
                    tfidf_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
                    print(f"Applied Naive Bayes re-ranking with probabilities")
                    
                except Exception as e:
                    print(f"Error applying Naive Bayes: {e}. Using TF-IDF results only.")
            
            # Sort results by score
            tfidf_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            # Apply source filtering if specified
            if filter_label:
                tfidf_results = [doc for doc in tfidf_results 
                              if doc.get('label', '').upper() == filter_label.upper()]
            
            # If we have class probabilities, distribute results accordingly
            if class_probs and len(tfidf_results) > 0:
                # Calculate how many results to take from each source based on probabilities
                source_counts = {}
                remaining = top_k
                
                # Sort sources by probability (descending)
                sorted_sources = sorted(class_probs.items(), key=lambda x: x[1], reverse=True)
                
                # Calculate initial distribution
                for source, prob in sorted_sources:
                    count = max(1, int(prob * top_k))  # At least 1 result per source with non-zero probability
                    source_counts[source] = min(count, remaining)
                    remaining -= count
                    if remaining <= 0:
                        break
                
                # If we still have remaining slots, distribute them to the top sources
                if remaining > 0 and source_counts:
                    for source, _ in sorted_sources:
                        if source in source_counts:
                            source_counts[source] += 1
                            remaining -= 1
                            if remaining == 0:
                                break
                
                # Collect results based on the distribution
                formatted_results = []
                source_results = {source: [] for source in source_counts}
                
                # First pass: collect results by source
                for doc in tfidf_results:
                    source = doc.get('label', 'UNKNOWN')
                    if source in source_counts and len(source_results[source]) < source_counts[source]:
                        source_results[source].append(doc)
                    
                    # Stop if we've collected enough results
                    if all(len(docs) >= source_counts[source] for source, docs in source_results.items()):
                        break
                
                # Flatten the results while maintaining source distribution
                for source, docs in source_results.items():
                    formatted_results.extend(docs)
                
                # If we still don't have enough results, fill with remaining best matches
                if len(formatted_results) < top_k and len(tfidf_results) > len(formatted_results):
                    remaining_results = [doc for doc in tfidf_results if doc not in formatted_results]
                    formatted_results.extend(remaining_results[:top_k - len(formatted_results)])
                
                # Format the results
                formatted_results = [
                    {
                        'rank': i,
                        'title': doc.get('title', 'Untitled'),
                        'content': doc.get('content', ''),
                        'url': doc.get('url', ''),
                        'source': doc.get('label', 'UNKNOWN'),
                        'score': float(doc.get('similarity_score', 0)),
                        'meta_image': doc.get('meta_image', '')
                    }
                    for i, doc in enumerate(formatted_results[:top_k], start=1)
                    if doc.get('similarity_score', 0) >= min_score
                ]

                
            else:
                # Fallback to simple top-k if no probability distribution
                formatted_results = []
                i = 1
                for doc in tfidf_results[:top_k]:
                    if doc.get('similarity_score', 0) >= min_score:
                        formatted_results.append({
                            'rank': i,
                            'title': doc.get('title', 'Untitled'),
                            'content': doc.get('content', ''),
                            'url': doc.get('url', ''),
                            'source': doc.get('label', 'UNKNOWN'),
                            'score': float(doc.get('similarity_score', 0)),
                            'meta_image': doc.get('meta_image', '')
                        })
                    i += 1
            
            return formatted_results
            
        except Exception as e:
            error_msg = f"Error performing search: {str(e)}"
            print(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )


# Create a singleton instance of the controller
tfidf_controller = TFIDFController()