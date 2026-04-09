import os
import pickle
import math
from typing import Dict, List, Any
from utils.tokenizer import tokenize

class NaiveBayes:
    def __init__(self, model_path: str = None):
        """
        Initialize NaiveBayes classifier.
        
        Args:
            model_path (str, optional): Path to the pre-trained model. If not provided,
                                     will look for 'models/naive_model.pkl' relative to the backend directory.
        """
        self.model_path = model_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                   'models', 'naive_model.pkl')
        self.model = None
        self.classes_ = None
        self.vocab_size = 0
        self.is_trained = False
        
        # Load the model if path is provided
        if self.model_path and os.path.exists(self.model_path):
            self.load_model()
    
    def load_model(self, model_path: str = None) -> None:
        """
        Load a pre-trained Naive Bayes model from disk.
        
        Args:
            model_path (str, optional): Path to the model file. If not provided, uses the path from initialization.
        """
        if model_path:
            self.model_path = model_path
            
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                
            # Extract model parameters
            self.class_word_counts = model_data['class_word_counts']
            
            # Process class_counts to only include valid numeric values
            self.class_counts = {}
            for k, v in model_data['class_counts'].items():
                try:
                    self.class_counts[k] = int(v) if str(v).isdigit() else 0
                except (ValueError, TypeError):
                    continue  # Skip non-numeric values
            
            # If no valid class counts were found, set a default
            if not self.class_counts:
                self.class_counts = {k: 1 for k in self.class_word_counts.keys()}
            
            # Ensure vocab_size is an integer
            try:
                self.vocab_size = int(model_data.get('vocab_size', len(set(
                    word for counts in self.class_word_counts.values() 
                    for word in (counts.split() if isinstance(counts, str) else counts.keys())
                ))) if 'vocab_size' in model_data else 1000)
            except (ValueError, TypeError):
                self.vocab_size = 1000  # Default value if vocab_size is invalid
            
            self.is_trained = bool(model_data.get('is_trained', False))
            
            # Get class labels from class_counts (which now only contains valid entries)
            self.classes_ = list(self.class_counts.keys())
            
            # Ensure we have at least one class
            if not self.classes_ and self.class_word_counts:
                self.classes_ = list(self.class_word_counts.keys())
                self.class_counts = {k: 1 for k in self.classes_}
            
            # Process class_word_counts to handle both string and dict formats
            self.class_word_counts_processed = {}
            self.class_total_words = {}
            
            for cls, counts in self.class_word_counts.items():
                if isinstance(counts, str):
                    # If it's a string, split into words and count frequencies
                    words = counts.lower().split()
                    word_counts = {}
                    for word in words:
                        word_counts[word] = word_counts.get(word, 0) + 1
                    self.class_word_counts_processed[cls] = word_counts
                    self.class_total_words[cls] = len(words)
                elif isinstance(counts, dict):
                    # If it's already a dictionary of word counts
                    self.class_word_counts_processed[cls] = counts
                    self.class_total_words[cls] = sum(counts.values())
                else:
                    raise ValueError(f"Unexpected type {type(counts)} for class_word_counts['{cls}']")
            
            # Calculate class priors with Laplace smoothing
            total_classes = len(self.classes_)
            total_docs = sum(self.class_counts.values())
            
            # Apply Laplace smoothing to prevent division by zero
            self.class_priors = {
                cls: (count + 1) / (total_docs + total_classes) 
                for cls, count in self.class_counts.items()
            }
            
            # Store log probabilities for prediction
            self.log_class_priors = {}
            for cls in self.classes_:
                try:
                    self.log_class_priors[cls] = math.log(self.class_priors[cls])
                except (ValueError, ArithmeticError):
                    # If there's an error with log(0), use a very small number
                    self.log_class_priors[cls] = -1e10  # A very small number (log of a very small positive number)
            
            # Precompute log likelihoods for each class and word
            self.log_likelihoods = {}
            for cls in self.classes_:
                self.log_likelihoods[cls] = {}
                total_words_in_class = self.class_total_words[cls]
                for word, count in self.class_word_counts_processed[cls].items():
                    # Laplace smoothing
                    self.log_likelihoods[cls][word] = math.log(
                        (count + 1) / (total_words_in_class + self.vocab_size)
                    )
                
            print(f"Loaded Naive Bayes model with {len(self.classes_)} classes and vocab size {self.vocab_size}")
            
        except Exception as e:
            raise Exception(f"Failed to load model from {self.model_path}: {str(e)}")
    
    def predict_proba(self, text: str) -> Dict[str, float]:
        """
        Predict class probabilities for a single text input.
        
        Args:
            text (str): Input text to classify
            
        Returns:
            Dict[str, float]: Dictionary of class probabilities (excluding 'source')
        """
        if not self.is_trained:
            raise ValueError("Model is not trained. Please load a trained model first.")
        
        # Initialize scores with class priors
        scores = {cls: self.log_class_priors[cls] for cls in self.classes_}
        
        # Tokenize the input text (simple whitespace tokenizer)
        words = tokenize(text)
        
        # Calculate log likelihood for each class
        for cls in self.classes_:
            for word in words:
                if word in self.log_likelihoods[cls]:
                    scores[cls] += self.log_likelihoods[cls][word]
                else:
                    # Handle out-of-vocabulary words with Laplace smoothing
                    scores[cls] += math.log(1 / (self.class_total_words[cls] + self.vocab_size))
        
        # Convert log probabilities back to probabilities
        max_score = max(scores.values())
        exp_scores = {cls: math.exp(score - max_score) for cls, score in scores.items() 
                    if cls != 'source'}  # Exclude 'source' class
        sum_exp_scores = sum(exp_scores.values())
        
        # Return normalized probabilities
        return {cls: exp_scores[cls] / sum_exp_scores for cls in exp_scores}

    def predict(self, text: str) -> str:
        """
        Predict the most likely class for a single text input.
        
        Args:
            text (str): Input text to classify
            
        Returns:
            str: Predicted class label (prefers 'label' class if it exists)
        """
        probas = self.predict_proba(text)
        if not probas:  # In case all classes were filtered out
            return "Unknown"
        
        # If 'label' is one of the possible classes, return its prediction
        # if 'label' in probas:
        #     return str(probas['label'])
        
        # Otherwise return the class with highest probability
        return max(probas.items(), key=lambda x: x[1])[0]
    
    def predict_batch(self, texts: List[str]) -> List[str]:
        """
        Predict the most likely class for multiple text inputs.
        
        Args:
            texts (List[str]): List of input texts to classify
            
        Returns:
            List[str]: List of predicted class labels
        """
        return [self.predict(text) for text in texts]
    
    def get_classes(self) -> List[str]:
        """
        Get the list of class labels.
        
        Returns:
            List[str]: List of class labels
        """
        return self.classes_ if self.is_trained else []

# Example usage
if __name__ == "__main__":
    # Initialize the classifier
    nb = NaiveBayes()  # This will load the model
    prediction = nb.predict("Typhoon opong")
    probabilities = nb.predict_proba("Typhoon opong")
    print(f"Prediction: {prediction}")
    print("Probabilities:", probabilities)