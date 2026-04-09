import os
import sys
import pickle
import argparse
import uuid
from bson.binary import Binary
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Add parent directory to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Chunk size in bytes (safely under MongoDB's 16MB limit)
CHUNK_SIZE = 15 * 1024 * 1024  # 15MB

def get_mongodb_collection():
    """Initialize and return MongoDB collection for model storage."""
    from src.core.mongodb_connect import create_connection
    
    try:
        client = create_connection()
        client.admin.command('ping')
        return client.get_database('nlp_finals')['tfidf_models']
    except Exception as e:
        print(f"\n❌ Failed to connect to MongoDB: {e}")
        raise

def save_model_in_batches(pickle_path: str, model_name: str) -> Optional[str]:
    """Save a large pickle file to MongoDB in batches with a unique tfidf_id."""
    if not os.path.exists(pickle_path):
        print(f"Error: File not found: {pickle_path}")
        return None
    
    try:
        # Read the entire file as binary
        with open(pickle_path, 'rb') as f:
            model_data = f.read()
        
        # Generate a unique ID for this model version
        tfidf_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        
        # Split the data into chunks
        chunks = [model_data[i:i + CHUNK_SIZE] for i in range(0, len(model_data), CHUNK_SIZE)]
        total_chunks = len(chunks)
        
        # Get the collection
        collection = get_mongodb_collection()
        
        # Save metadata first
        metadata = {
            'tfidf_id': tfidf_id,
            'model_name': model_name,
            'version': 1,  # You can increment this for new versions
            'total_chunks': total_chunks,
            'created_at': created_at,
            'status': 'uploading',
            'size_bytes': len(model_data)
        }
        collection.insert_one(metadata)
        
        # Save each chunk as a separate document
        operations = []
        for i, chunk in enumerate(chunks):
            operations.append({
                'tfidf_id': tfidf_id,
                'chunk_index': i,
                'data': Binary(chunk),
                'created_at': created_at
            })
        
        # Insert all chunks in a single batch
        if operations:
            collection.insert_many(operations)
        
        # Update status to completed
        collection.update_one(
            {'tfidf_id': tfidf_id, 'model_name': model_name},
            {'$set': {'status': 'completed'}}
        )
        
        print(f"✅ Successfully saved model '{model_name}' with ID: {tfidf_id}")
        print(f"   - Total chunks: {total_chunks}")
        print(f"   - Total size: {len(model_data) / (1024*1024):.2f} MB")
        return tfidf_id
        
    except Exception as e:
        print(f"❌ Error saving to MongoDB: {e}")
        # Update status to failed if possible
        try:
            collection.update_one(
                {'tfidf_id': tfidf_id, 'model_name': model_name},
                {'$set': {'status': 'failed', 'error': str(e)}}
            )
        except:
            pass
        return None

def load_model_by_id(tfidf_id: str, output_path: str) -> bool:
    """Load a model from MongoDB by tfidf_id and save as a pickle file."""
    try:
        collection = get_mongodb_collection()
        
        # Get metadata
        metadata = collection.find_one(
            {'tfidf_id': tfidf_id, 'status': 'completed'},
            {'_id': 0, 'total_chunks': 1, 'model_name': 1}
        )
        
        if not metadata:
            print(f"❌ No completed model found with ID: {tfidf_id}")
            return False
        
        # Find all chunks for this model, ordered by chunk_index
        chunks = list(collection.find(
            {'tfidf_id': tfidf_id, 'chunk_index': {'$exists': True}},
            {'_id': 0, 'chunk_index': 1, 'data': 1}
        ).sort('chunk_index', 1))
        
        if len(chunks) != metadata['total_chunks']:
            print(f"❌ Incomplete model data. Expected {metadata['total_chunks']} chunks, found {len(chunks)}")
            return False
        
        # Reassemble the data
        model_data = b''.join(chunk['data'] for chunk in chunks)
        
        # Save to file
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(model_data)
        
        print(f"✅ Successfully loaded model '{metadata['model_name']}' to {output_path}")
        print(f"   - Size: {len(model_data) / (1024*1024):.2f} MB")
        return True
        
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False

def list_models() -> None:
    """List all available models in the database."""
    try:
        collection = get_mongodb_collection()
        
        # Get distinct model names with their latest version
        pipeline = [
            {'$match': {'status': 'completed'}},
            {'$sort': {'created_at': -1}},
            {'$group': {
                '_id': '$model_name',
                'latest_version': {'$first': '$$ROOT'}
            }},
            {'$replaceRoot': {'newRoot': '$latest_version'}},
            {'$project': {
                '_id': 0,
                'model_name': 1,
                'tfidf_id': 1,
                'version': 1,
                'created_at': 1,
                'size_mb': {'$divide': ['$size_bytes', 1024 * 1024]}
            }}
        ]
        
        models = list(collection.aggregate(pipeline))
        
        if not models:
            print("No models found in the database.")
            return
        
        print("\nAvailable Models:")
        print("=" * 80)
        print(f"{'Name':<20} {'ID':<38} {'Version':<8} {'Size (MB)':<10} {'Created At'}")
        print("-" * 80)
        for model in models:
            print(f"{model['model_name'][:18]:<20} {model['tfidf_id']} {model.get('version', 1):<8} {model.get('size_mb', 0):<10.2f} {model['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error listing models: {e}")

def main():
    parser = argparse.ArgumentParser(description='Manage TF-IDF models in MongoDB')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Save command
    save_parser = subparsers.add_parser('save', help='Save a pickle file to MongoDB')
    save_parser.add_argument('pickle_path', help='Path to the pickle file')
    save_parser.add_argument('model_name', help='Name to store the model under in MongoDB')
    
    # Load command
    load_parser = subparsers.add_parser('load', help='Load a model from MongoDB to a pickle file')
    load_parser.add_argument('tfidf_id', help='ID of the model to load')
    load_parser.add_argument('output_path', help='Path where to save the pickle file')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all models in MongoDB')
    
    args = parser.parse_args()
    
    if args.command == 'save':
        tfidf_id = save_model_in_batches(args.pickle_path, args.model_name)
        if tfidf_id:
            print(f"Use this ID to load the model: {tfidf_id}")
    elif args.command == 'load':
        load_model_by_id(args.tfidf_id, args.output_path)
    elif args.command == 'list':
        list_models()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()