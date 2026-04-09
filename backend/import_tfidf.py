import os
import pickle
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

def main():
    print("=" * 50)
    print("TF-IDF Model Import Tool")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Get paths and settings
    model_path = os.path.join('trained_models', 'tfidf_model.pkl')
    model_id = os.getenv('TFIDF_INDEX', 'tfidf_model')
    mongo_uri = os.getenv('URI')
    db_name = os.getenv('DB_NAME', 'nlp_finals')
    
    if not mongo_uri:
        print("❌ Error: MongoDB URI not found in environment variables")
        return
    
    if not os.path.exists(model_path):
        print(f"❌ Error: Model file not found at {model_path}")
        return
    
    try:
        # Connect to MongoDB
        print(f"\n🔌 Connecting to MongoDB...")
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db['tfidf_models']
        
        # Read the model file
        print(f"\n📦 Reading model from: {model_path}")
        with open(model_path, 'rb') as f:
            model_data = f.read()
        
        # Calculate chunk size (15MB to stay under 16MB limit)
        chunk_size = 15 * 1024 * 1024
        total_size = len(model_data)
        total_chunks = (total_size + chunk_size - 1) // chunk_size
        
        print(f"  - Model size: {total_size / (1024*1024):.2f} MB")
        print(f"  - Will be split into {total_chunks} chunks")
        
        # Delete any existing chunks for this model
        print(f"\n🗑️  Cleaning up any existing model chunks...")
        delete_result = collection.delete_many({"model_id": model_id})
        print(f"  - Deleted {delete_result.deleted_count} old chunks")
        
        # Insert chunks
        print(f"\n💾 Saving model to MongoDB...")
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
            print(f"  - Saved chunk {i+1}/{total_chunks} ({len(chunk) / (1024*1024):.1f} MB)", end='\r')
        
        # Create indexes
        print("\n\n🔨 Creating indexes...")
        collection.create_index([("model_id", 1)])
        collection.create_index([("chunk_num", 1)])
        
        # Verify
        saved_chunks = collection.count_documents({"model_id": model_id})
        print(f"\n✅ Successfully imported model")
        print(f"   - Model ID: {model_id}")
        print(f"   - Total chunks: {saved_chunks}")
        print(f"   - Total size: {total_size / (1024*1024):.2f} MB")
        
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
