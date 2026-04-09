import pickle as pk
import json
import os

# Path to the TF-IDF model
model_path = "trained_models/tfidf_model.pkl"

try:
    # Load the TF-IDF model
    with open(model_path, "rb") as f:
        tfidf_data = pk.load(f)
    
    print("Successfully loaded TF-IDF model")
    
    # Extract documents
    if 'documents' in tfidf_data:
        # Create output directory if it doesn't exist
        output_dir = "model_data"
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare documents in the required format
        formatted_docs = []
        for doc in tfidf_data['documents']:
            formatted_doc = {
                'id': doc.get('id'),
                'title': doc.get('title', ''),
                'content': doc.get('content', ''),
                'url': doc.get('url', ''),
                'label': doc.get('label', ''),
                'meta_image': doc.get('meta_image', '')
            }
            formatted_docs.append(formatted_doc)
        
        # Save as JSON
        output_file = os.path.join(output_dir, "tfidf_documents.json")
        with open(output_file, "w", encoding='utf-8') as f:
            json.dump(formatted_docs, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully saved {len(formatted_docs)} documents to {output_file}")
        
        # Also save model metadata
        metadata = {
            'document_count': len(tfidf_data.get('documents', [])),
            'vocabulary_size': len(tfidf_data.get('vocab', set())),
            'has_tfidf_vectors': 'tfidf_vectors' in tfidf_data and len(tfidf_data['tfidf_vectors']) > 0
        }
        
        metadata_file = os.path.join(output_dir, "tfidf_metadata.json")
        with open(metadata_file, "w", encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        print(f"Model metadata saved to {metadata_file}")
    
    else:
        print("Error: No documents found in the TF-IDF model")
        if hasattr(tfidf_data, '__dict__'):
            print("Available attributes:", tfidf_data.__dict__.keys())
        else:
            print("Model data type:", type(tfidf_data))

except Exception as e:
    print(f"Error processing TF-IDF model: {str(e)}")
    raise