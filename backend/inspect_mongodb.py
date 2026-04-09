import os
from pymongo import MongoClient
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
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
        
        # List all collections
        collections = db.list_collection_names()
        print("\n📂 Collections in database:")
        for col in collections:
            print(f"- {col}")
        
        # Check tfidf_models collection
        if 'tfidf_models' in collections:
            collection = db['tfidf_models']
            
            # Count total documents
            total_docs = collection.count_documents({})
            print(f"\n📊 Total documents in tfidf_models: {total_docs}")
            
            # Count documents per model_id
            pipeline = [
                {"$group": {"_id": "$model_id", "count": {"$sum": 1}, "chunks": {"$push": "$chunk_num"}}},
                {"$sort": {"_id": 1}}
            ]
            
            print("\n📋 Documents by model_id:")
            for doc in collection.aggregate(pipeline):
                model_id = doc['_id']
                count = doc['count']
                chunks = sorted(doc['chunks'])
                print(f"\nModel ID: {model_id}")
                print(f"Total chunks: {count}")
                print(f"Chunk numbers: {chunks}")
                
                # Get the first document for this model_id to check its structure
                first_doc = collection.find_one({"model_id": model_id})
                if first_doc:
                    print("\nDocument structure:")
                    for key in first_doc:
                        value_type = type(first_doc[key]).__name__
                        value_preview = f"{first_doc[key]}" if not isinstance(first_doc[key], (bytes, dict, list)) else f"<{value_type}>"
