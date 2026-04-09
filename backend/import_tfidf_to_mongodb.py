import os
import sys
import pickle
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

def load_dotenv_safe():
    """Safely load environment variables from .env file."""
    try:
        load_dotenv()
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not load .env file: {e}")
        return False

def get_mongodb_connection():
    """Establish MongoDB connection using environment variables."""
    try:
        mongo_uri = os.getenv('URI')
        if not mongo_uri:
            raise ValueError("MongoDB URI not found in environment variables")
            
        client = MongoClient(mongo_uri)
        # Test the connection
        client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise

def import_tfidf_model():
    """Import TF-IDF model from file to MongoDB."""
    # Load environment variables
    load_dotenv_safe()
    
    # Get model paths - using direct path since we know the file is in trained_models/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, 'trained_models', 'tfidf_model.pkl')
    
    if not os.path.exists(model_path):
        print(f"❌ Model file not found: {model_path}")
        return False
    
    print(f"🔍 Found model file: {model_path}")
    
    try:
        # Connect to MongoDB
        client = get_mongodb_connection()
        db = client[os.getenv('DB_NAME', 'nlp_finals')]
        collection = db['tfidf_models']
        
        # Get model_id from environment
        model_id = os.getenv('TFIDF_INDEX', 'tfidf_model')
        print(f"📦 Preparing to import model with ID: {model_id}")
        
        # Delete any existing model chunks
        delete_result = collection.delete_many({"model_id": model_id})
        print(f"♻️  Deleted {delete_result.deleted_count} old model chunks")
        
        # Read the model file
        print("📂 Reading model file...")
        with open(model_path, 'rb') as f:
            model_data = f.read()
        
        # Split into chunks (15MB each to stay under MongoDB's 16MB limit)
        chunk_size = 15 * 1024 * 1024
        total_chunks = (len(model_data) + chunk_size - 1) // chunk_size
        print(f"✂️  Splitting model into {total_chunks} chunks...")
        
        # Insert chunks into MongoDB
        for i in range(total_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size
            chunk = model_data[start_idx:end_idx]
            
            chunk_doc = {
                "model_id": model_id,
                "chunk_num": i,
                "total_chunks": total_chunks,
                "data": chunk,
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow()
            }
            
            collection.insert_one(chunk_doc)
            print(f"  ✅ Saved chunk {i+1}/{total_chunks}", end='\r')
        
        # Create indexes for faster querying
        print("\n🔨 Creating indexes...")
        collection.create_index([("model_id", 1)])
        collection.create_index([("chunk_num", 1)])
        
        print(f"\n🎉 Successfully imported model with ID: {model_id}")
        print(f"   Total chunks: {total_chunks}")
        print(f"   Total size: {len(model_data) / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error importing model: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("=" * 50)
    print("TF-IDF Model Import to MongoDB")
    print("=" * 50)
    
    success = import_tfidf_model()
    
    print("\n" + "=" * 50)
    print("✅ Import completed successfully!" if success else "❌ Import failed")
    print("=" * 50)
