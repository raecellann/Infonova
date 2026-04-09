import os
import sys
import pickle
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TFIDFPredictor:
    def __init__(self, model_path, labels_path):
        """Initialize the TF-IDF predictor with model and labels."""
        self.model_path = model_path
        self.labels_path = labels_path
        self.vectorizer = None
        self.labels = None
        self.load_model()
        
    def load_model(self):
        """Load the TF-IDF model and labels."""
        try:
            # Load the TF-IDF model
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.vectorizer = TFIDFVectorizer()
                self.vectorizer.vocabulary = model_data['vocabulary']
                self.vectorizer.idf = model_data['idf']
                self.vectorizer.fitted = model_data['fitted']
                logger.info(f"Loaded TF-IDF model with vocabulary size: {len(self.vectorizer.vocabulary)}")
            
            # Load the labels
            with open(self.labels_path, 'rb') as f:
                self.labels = pickle.load(f)
                logger.info(f"Loaded {len(self.labels)} labels")
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}", exc_info=True)
            raise
    
    def preprocess_text(self, text):
        """Preprocess text using the same pipeline as training."""
        from src.utils.contraction import expand_contraction
        from src.utils.tokenizer import tokenize
        
        # Apply the same preprocessing as during training
        text = str(text)
        text = expand_contraction(text)
        tokens = tokenize(
            text,
            special_tokens=False,
            remove_stopwords=True,
            use_lemmatization=True
        )
        return tokens
    
    def transform_text(self, text):
        """Transform a single text into TF-IDF vector."""
        if not self.vectorizer or not self.vectorizer.fitted:
            raise ValueError("Model not loaded or not fitted")
            
        # Convert text to TF-IDF vector
        tf = defaultdict(int)
        words = self.preprocess_text(text)
        
        # Calculate term frequencies
        for word in words:
            if word in self.vectorizer.vocabulary:
                tf[word] += 1
        
        # Create TF-IDF vector
        vec = [0.0] * len(self.vectorizer.vocabulary)
        for word, count in tf.items():
            if word in self.vectorizer.vocabulary:
                tf_val = count / len(words) if words else 0
                idf_val = self.vectorizer.idf.get(word, 0)
                vec[self.vectorizer.vocabulary[word]] = tf_val * idf_val
                
        return vec

# This class needs to match the one used during training
class TFIDFVectorizer:
    def __init__(self):
        self.vocabulary = {}
        self.idf = {}
        self.fitted = False

def predict_source(predictor, text):
    """
    Predict the news source and return metadata.
    
    Args:
        predictor: Initialized TFIDFPredictor instance
        text: Input text to predict
        
    Returns:
        dict: Dictionary containing prediction metadata
    """
    # Transform text to TF-IDF vector
    vector = predictor.transform_text(text)
    
    # Get the index of the highest value in the vector
    max_index = vector.index(max(vector))
    
    # Map the index to the corresponding label
    predicted_label = predictor.labels[max_index % len(predictor.labels)]
    
    # Create and return metadata
    return {
        "meta_image": "https://via.placeholder.com/150",  # Placeholder image
        "title": text[:50] + ("..." if len(text) > 50 else ""),  # First 50 chars as title
        "content": text[:200] + ("..." if len(text) > 200 else ""),  # First 200 chars as snippet
        "url": "https://example.com",  # Placeholder URL
        "label": predicted_label  # Predicted news source
    }

def main():
    # Paths to model files
    model_path = "models/tfidf_model_v2.pkl"
    labels_path = "models/tfidf_model_v2_labels.pkl"
    
    try:
        # Initialize predictor
        predictor = TFIDFPredictor(model_path, labels_path)
        
        # Example prediction
        test_text = "typhoon nando"
        
        # Get prediction with metadata
        result = predict_source(predictor, test_text)
        
        # Print results
        print("\n=== Prediction Results ===")
        print(f"Input text: {test_text}")
        print("\nMetadata:")
        for key, value in result.items():
            print(f"- {key}: {value}")
        
    except Exception as e:
        logger.error(f"Error during prediction: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()