import os
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

def main():
    # Load environment variables
    if not load_dotenv_safe():
        print("❌ Failed to load environment variables")
        return
    
    # Get model_id from environment
    model_id = os.getenv('TFIDF_INDEX', 'tfidf_model')
    
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv('URI')
        if not mongo_uri:
            raise ValueError("MongoDB URI not found in environment variables")
            
        client = MongoClient(mongo_uri)
        db_name = os.getenv('DB_NAME', 'nlp_finals')
        db = client[db_name]
        collection = db['tfidf_models']
        
        # Count and delete chunks for the model
        count = collection.count_documents({"model_id": model_id})
        print(f"🔍 Found {count} chunks for model ID: {model_id}")
        
        if count > 0:
            result = collection.delete_many({"model_id": model_id})
            print(f"🗑️  Deleted {result.deleted_count} chunks for model ID: {model_id}")
        else:
            print("✅ No chunks found to delete")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()

if __name__ == "__main__":
    print("=" * 50)
    print("MongoDB Model Cleanup")
    print("=" * 50)
    main()
    print("\n" + "=" * 50)
