import pickle
import io
from bson.binary import Binary
from typing import Any, Optional
from datetime import datetime
from src.core.mongodb_connect import create_connection

class ModelStorageMongoDB:
    def __init__(self, db_name: str = 'nlp_models', collection_name: str = 'trained_models'):
        """
        Initialize MongoDB model storage.
        
        Args:
            db_name: Name of the MongoDB database
            collection_name: Name of the collection to store models
        """
        self.client = create_connection()
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
    
    def save_model(self, model: Any, model_name: str, metadata: Optional[dict] = None) -> str:
        """
        Save a model to MongoDB with metadata.
        
        Args:
            model: The model object to save (must be pickleable)
            model_name: Name to identify the model
            metadata: Additional metadata to store with the model
            
        Returns:
            The document ID of the saved model
        """
        # Serialize the model to bytes
        model_bytes = io.BytesIO()
        pickle.dump(model, model_bytes)
        model_bytes = model_bytes.getvalue()
        
        # Prepare document
        doc = {
            'name': model_name,
            'model_data': Binary(model_bytes),
            'created_at': datetime.utcnow(),
            'metadata': metadata or {}
        }
        
        # Update if exists, insert if not
        result = self.collection.update_one(
            {'name': model_name},
            {'$set': doc},
            upsert=True
        )
        
        return str(result.upserted_id) if result.upserted_id else str(result.modified_count)
    
    def load_model(self, model_name: str) -> Any:
        """
        Load a model from MongoDB.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            The loaded model object
            
        Raises:
            ValueError: If the model is not found
        """
        doc = self.collection.find_one({'name': model_name})
        
        if not doc:
            raise ValueError(f"Model '{model_name}' not found in the database")
        
        # Deserialize the model
        model_bytes = io.BytesIO(doc['model_data'])
        return pickle.load(model_bytes)
    
    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model from MongoDB.
        
        Args:
            model_name: Name of the model to delete
            
        Returns:
            True if the model was deleted, False otherwise
        """
        result = self.collection.delete_one({'name': model_name})
        return result.deleted_count > 0
    
    def list_models(self) -> list:
        """
        List all available models in the database.
        
        Returns:
            List of model metadata dictionaries
        """
        models = []
        for doc in self.collection.find({}, {'model_data': 0}):  # Exclude model_data for listing
            doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
            models.append(doc)
        return models
    
    def close(self):
        """Close the MongoDB connection."""
        self.client.close()
