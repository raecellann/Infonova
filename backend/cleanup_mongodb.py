import os
from pymongo import MongoClient
from dotenv import load_dotenv

def main():
    print("=" * 50)
    print("MongoDB Cleanup Tool")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Get MongoDB connection details
    mongo_uri = os.getenv('URI')
    db_name = os.getenv('DB_NAME', 'nlp_finals')
    
    if not mongo_uri:
        print("❌ Error: MongoDB URI not found in environment variables")
        return
    
    try:
        # Connect to MongoDB
        print(f"\n🔌 Connecting to MongoDB at: {mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri}")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        
        # List all collections
        collections = db.list_collection_names()
        print("\n📂 Collections in database:")
        for col in collections:
            print(f"- {col}")
        
        # Clean up tfidf_models collection if it exists
        if 'tfidf_models' in collections:
            collection = db['tfidf_models']
            
            # Get model_id from environment
            model_id = os.getenv('TFIDF_INDEX', 'tfidf_model')
            
            # Delete all documents for this model_id
            result = collection.delete_many({"model_id": model_id})
            print(f"\n🗑️  Deleted {result.deleted_count} documents for model_id: {model_id}")
            
            # Drop and recreate indexes
            print("\n🔄 Rebuilding indexes...")
            collection.drop_indexes()
            collection.create_index([("model_id", 1)])
            collection.create_index([("chunk_num", 1)])
            
            # Verify cleanup
            remaining = collection.count_documents({"model_id": model_id})
            if remaining == 0:
                print("✅ Successfully cleaned up MongoDB collection")
            else:
                print(f"⚠️  Warning: {remaining} documents still exist after cleanup")
        else:
            print("\nℹ️  No tfidf_models collection found")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'client' in locals():
            client.close()
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
