import os
import os
import sys
import math
import time
import logging
import pickle
from datetime import datetime
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tfidf_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import custom utilities
from src.utils.tokenizer import tokenize
from src.utils.lemmatization import lemmatize
from src.utils.contraction import expand_contraction

def log_execution_time(func):
    """Decorator to log the execution time of a function"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Starting {func.__name__}...")
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Completed {func.__name__} in {end_time - start_time:.2f} seconds")
        return result
    return wrapper

class TFIDFVectorizer:
    def __init__(self, mongodb_uri=None, db_name=None):
        """
        Initialize TF-IDF Vectorizer
        
        Args:
            mongodb_uri: Optional MongoDB URI for document storage
            db_name: Optional database name
        """
        self.vocabulary = {}
        self.idf = {}
        self.fitted = False
        self.mongodb_uri = mongodb_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        
        # Initialize MongoDB connection if URI provided
        if mongodb_uri and db_name:
            try:
                from pymongo import MongoClient
                self.client = MongoClient(mongodb_uri)
                self.db = self.client[db_name]
                logger.info(f"Connected to MongoDB: {db_name}")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {str(e)}")
        
        # Load Naive Bayes model to get vocabulary
        self.load_naive_bayes_vocabulary()

    def load_naive_bayes_vocabulary(self):
        """Load vocabulary from the trained Naive Bayes model"""
        try:
            # Import here to avoid circular imports
            from backend.models.bow_naive_bayes import load_model
            
            # Load the Naive Bayes model
            class_counts, class_word_counts, vocab_size = load_model("bow_naive_bayes_model_v1.pkl")
            
            # Build vocabulary from the Naive Bayes model
            nb_vocab = set()
            for label in class_word_counts:
                nb_vocab.update(class_word_counts[label].keys())
            
            # Create vocabulary mapping
            self.vocabulary = {word: idx for idx, word in enumerate(sorted(nb_vocab))}
            logger.info(f"Loaded {len(self.vocabulary)} words from Naive Bayes vocabulary")
            
        except Exception as e:
            logger.error(f"Failed to load Naive Bayes vocabulary: {str(e)}")
            raise
    
    def preprocess_text(self, text):
        """
        Preprocess text using the project's utilities.
        - Expands contractions
        - Tokenizes
        - Lemmatizes
        - Removes stopwords
        """
        # Expand contractions first
        text = expand_contraction(text)
        
        # Tokenize with lemmatization and stopword removal
        tokens = tokenize(
            text,
            special_tokens=False,
            remove_stopwords=True,
            use_lemmatization=True
        )
        
        return tokens

    @log_execution_time
    def fit(self, documents):
        """
        Learn the vocabulary and idf from a list of documents.
        documents: list of strings
        """
        logger.info(f"Fitting TF-IDF vectorizer on {len(documents)} documents...")
        # Build vocabulary
        doc_count = 0
        doc_freq = defaultdict(int)
        total_words = 0
        
        for i, doc in enumerate(documents, 1):
            if i % 100 == 0:
                logger.info(f"Processing document {i}/{len(documents)}...")
                
            doc_count += 1
            seen_words = set()
            words = self.preprocess_text(doc)
            total_words += len(words)
            
            for word in words:
                if word not in seen_words:
                    doc_freq[word] += 1
                    seen_words.add(word)
        
        # Create vocabulary with term indices
        self.vocabulary = {term: idx for idx, term in enumerate(sorted(doc_freq.keys()))}
        
        # Calculate IDF
        total_docs = doc_count
        logger.info(f"Calculating IDF for {len(self.vocabulary)} unique terms...")
        for term, count in doc_freq.items():
            self.idf[term] = math.log((1 + total_docs) / (1 + count)) + 1
        
        self.fitted = True
        logger.info(f"Fit complete. Processed {total_docs} documents with {total_words} total tokens and {len(self.vocabulary)} unique terms.")
        return self

    @log_execution_time
    def transform(self, documents):
        """
        Transform documents to TF-IDF features.
        """
        if not self.fitted:
            raise ValueError("TF-IDF vectorizer not fitted. Call 'fit' first.")
        
        logger.info(f"Transforming {len(documents)} documents to TF-IDF features...")
        # Initialize document-term matrix
        X = []
        
        for i, doc in enumerate(documents, 1):
            if i % 100 == 0:
                logger.info(f"Transforming document {i}/{len(documents)}...")
                
            # Calculate term frequencies
            tf = defaultdict(int)
            words = self.preprocess_text(doc)
            
            for word in words:
                if word in self.vocabulary:
                    tf[word] += 1
            
            # Calculate TF-IDF vector
            vec = [0.0] * len(self.vocabulary)
            for word, count in tf.items():
                if word in self.vocabulary:
                    tf_val = count / len(words) if words else 0  # Term frequency
                    idf_val = self.idf.get(word, 0)  # Inverse document frequency
                    vec[self.vocabulary[word]] = tf_val * idf_val
            
            X.append(vec)
        
        logger.info(f"Transformation complete. Created {len(X)} document vectors.")
        return X

    def fit_transform(self, documents):
        """
        Learn vocabulary and idf, return document-term matrix.
        """
        return self.fit(documents).transform(documents)

def load_datasets(data_dir):
    """
    Load data from CSV files in the data directory.
    Returns a list of documents and their corresponding labels.
    """
    import os
    import pandas as pd
    from glob import glob
    
    # Look for CSV files in the data directory
    csv_files = glob(os.path.join(data_dir, '*.csv'))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    all_documents = []
    all_labels = []
    
    for csv_file in csv_files:
        try:
            logger.info(f"Loading data from {os.path.basename(csv_file)}...")
            
            # Read the CSV file
            df = pd.read_csv(csv_file)
            
            # Try to identify text and label columns (case insensitive)
            text_columns = [col for col in df.columns if any(x in col.lower() for x in ['text', 'content', 'article', 'tweet'])]
            label_columns = [col for col in df.columns if any(x in col.lower() for x in ['label', 'sentiment', 'class', 'category'])]
            
            if not text_columns:
                logger.warning(f"Could not identify text column in {csv_file}. Using first column.")
                text_columns = [df.columns[0]]
                
            if not label_columns:
                logger.warning(f"Could not identify label column in {csv_file}. Using 'label' if exists, otherwise using second column.")
                label_columns = ['label'] if 'label' in df.columns else [df.columns[1] if len(df.columns) > 1 else df.columns[0]]
            
            text_col = text_columns[0]
            label_col = label_columns[0]
            
            logger.info(f"Using column '{text_col}' as text and '{label_col}' as label")
            
            # Extract documents and labels
            documents = df[text_col].fillna('').astype(str).tolist()
            labels = df[label_col].fillna('').astype(str).tolist()
            
            all_documents.extend(documents)
            all_labels.extend(labels)
            
            logger.info(f"Loaded {len(documents)} documents from {os.path.basename(csv_file)}")
            
        except Exception as e:
            logger.error(f"Error loading {csv_file}: {str(e)}")
            continue
    
    if not all_documents:
        raise ValueError("No valid data could be loaded from any CSV file")
    
    logger.info(f"Total documents loaded: {len(all_documents)}")
    logger.info(f"Sample document: {all_documents[0][:100]}...")
    logger.info(f"Sample label: {all_labels[0]}")
    
    return all_documents, all_labels

def save_tfidf_model(vectorizer, output_path):
    """
    Save the TF-IDF vectorizer to a file.
    """
    try:
        model_data = {
            'vocabulary': vectorizer.vocabulary,
            'idf': vectorizer.idf,
            'fitted': vectorizer.fitted,
            'vocabulary_size': len(vectorizer.vocabulary),
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info(f"TF-IDF model saved successfully to {output_path}")
        logger.info(f"Vocabulary size: {len(vectorizer.vocabulary)}")
        
    except Exception as e:
        logger.error(f"Failed to save TF-IDF model: {str(e)}", exc_info=True)
        raise

@log_execution_time
def train_and_save_model():
    """
    Main function to train and save the TF-IDF model.
    Integrates with the existing Naive Bayes model for consistent vocabulary.
    """
    start_time = time.time()
    logger.info("Starting TF-IDF model training...")
    
    # Load datasets
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
    logger.info(f"Loading datasets from: {data_dir}")
    
    documents, labels = load_datasets(data_dir)
    
    if not documents:
        logger.error("No documents found in the dataset")
        return
    
    logger.info(f"Loaded {len(documents)} documents for training")
    
    # Try to load Naive Bayes model to get vocabulary
    try:
        from backend.models.bow_naive_bayes import load_model
        class_counts, class_word_counts, vocab_size = load_model("bow_naive_bayes_model_v1.pkl")
        logger.info(f"Successfully loaded Naive Bayes model with vocabulary size: {vocab_size}")
        
        # Build vocabulary from Naive Bayes model
        nb_vocab = set()
        for label in class_word_counts:
            nb_vocab.update(class_word_counts[label].keys())
        
        logger.info(f"Extracted {len(nb_vocab)} unique terms from Naive Bayes model")
        
    except Exception as e:
        logger.error(f"Failed to load Naive Bayes model: {str(e)}")
        logger.error("Please ensure the Naive Bayes model is trained first.")
        logger.error("Run the Naive Bayes training script before training TF-IDF.")
        return
    
    # Initialize and fit the vectorizer
    try:
        logger.info("Initializing TF-IDF vectorizer...")
        vectorizer = TFIDFVectorizer()
        
        # Set the vocabulary from Naive Bayes model
        vectorizer.vocabulary = {word: idx for idx, word in enumerate(sorted(nb_vocab))}
        logger.info(f"Set vocabulary size: {len(vectorizer.vocabulary)}")
        
        # Fit the vectorizer to calculate IDF scores
        logger.info("Fitting TF-IDF vectorizer...")
        vectorizer.fit(documents)
        
        # Save the model
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'trained_models')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'tfidf_model.pkl')
        
        save_tfidf_model(vectorizer, output_path)
        
        # Save the labels for reference
        labels_path = os.path.join(output_dir, 'tfidf_model_labels.pkl')
        with open(labels_path, 'wb') as f:
            pickle.dump(labels, f)
        
        # Test the vectorizer
        test_text = "This is a test document to verify TF-IDF works with Naive Bayes vocabulary."
        try:
            vector = vectorizer.transform([test_text])
            non_zero = sum(1 for x in vector[0] if x > 0)
            logger.info(f"Test vector has {non_zero} non-zero features out of {len(vector[0])}")
        except Exception as e:
            logger.error(f"Error testing vectorizer: {str(e)}")
        
        # Log completion
        end_time = time.time()
        logger.info(f"TF-IDF model training completed successfully in {end_time - start_time:.2f} seconds")
        logger.info(f"Vocabulary size: {len(vectorizer.vocabulary)}")
        logger.info(f"Model saved to: {output_path}")
        logger.info(f"Labels saved to: {labels_path}")
            
    except Exception as e:
        logger.error(f"Error during TF-IDF training: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
        
        return vectorizer, X, labels
        
    except Exception as e:
        logger.error(f"Error during model training: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    train_and_save_model()
