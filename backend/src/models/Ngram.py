import os
import sys
import re
import pandas as pd
import pickle
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Set, Tuple, Optional, Any, Union

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from utils.pickle_utils import load_or_process_csv, get_pickle_path, save_to_pickle, load_from_pickle
from utils.tokenizer import tokenize

class Ngram:
    def __init__(self, k=1):
        self.k = k
        self.unigrams = Counter()
        self.bigrams = Counter()
        self.trigrams = Counter()
        self.vocab = set()
        self.data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data'
        )

    def _process_csv_file(self, file_path: str) -> dict:
        """Process a single CSV file and return n-gram data."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
            print(f"CSV columns: {df.columns.tolist()}")
            print(f"Number of rows: {len(df)}")
            
            # Initialize counters for this dataset
            unigrams = Counter()
            bigrams = Counter()
            trigrams = Counter()
            vocab = set()
            
            for _, row in df.iterrows():
                try:
                    # Safely get title and content, handle missing values
                    title = str(row.get('title', '')).strip()
                    content = str(row.get('content', row.get('text', ''))).strip()
                    
                    # Only process if we have valid text
                    if title or content:
                        text = f"{title}. {content}" if title and content else title or content
                        if text and len(text) > 10:  # Only process if we have reasonable amount of text
                            tokens = tokenize(text)
                            if len(tokens) >= 2:  # Need at least 2 tokens for bigrams
                                # Update unigrams
                                unigrams.update(tokens)
                                
                                # Update bigrams
                                for i in range(len(tokens) - 1):
                                    bigram = (tokens[i], tokens[i+1])
                                    bigrams[bigram] += 1
                                
                                # Update trigrams
                                for i in range(len(tokens) - 2):
                                    trigram = (tokens[i], tokens[i+1], tokens[i+2])
                                    trigrams[trigram] += 1
                                
                                # Update vocabulary
                                vocab.update(tokens)
                                
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
            
            print(f"Processed {len(df)} rows from {os.path.basename(file_path)}")
            print(f"Extracted {len(unigrams)} unigrams, {len(bigrams)} bigrams, {len(trigrams)} trigrams")
            
            return {
                'unigrams': dict(unigrams),
                'bigrams': dict(bigrams),
                'trigrams': dict(trigrams),
                'vocab': list(vocab),
                'source': os.path.basename(file_path),
                'processed_at': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def load_cnn_data(self, file_path: Optional[str] = None, force_reload: bool = False) -> List[str]:
        """Load data from CSV or pickle, with fallback to default corpus."""
        if file_path is None:
            # Look for any CSV file in the data directory
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
            csv_files = [f for f in os.listdir(data_dir) if f.endswith('_datasets.csv')]
            
            if not csv_files:
                print(f"No dataset files found in {data_dir}")
                return []
                
            file_path = os.path.join(data_dir, csv_files[0])
        
        print(f"Looking for dataset at: {file_path}")
        if not os.path.exists(file_path):
            print(f"Error: Dataset not found at {file_path}")
            return []
        
        try:
            # Use the pickle utility to load or process the data
            texts = load_or_process_csv(
                file_path, 
                process_func=self._process_csv_file,
                force_reload=force_reload
            )
            
            print(f"Successfully loaded {len(texts)} texts from {os.path.basename(file_path)}")
            return texts
            
        except Exception as e:
            print(f"Error in load_cnn_data: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_model(self, file_path: Optional[str] = None) -> bool:
        """Save the trained model to a file."""
        if file_path is None:
            model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'trained_models')
            os.makedirs(model_dir, exist_ok=True)
            file_path = os.path.join(model_dir, 'ngram_model_v1.pkl')
        
        try:
            model_data = {
                'unigrams': dict(self.unigrams),
                'bigrams': dict(self.bigrams),
                'trigrams': dict(self.trigrams),
                'vocab': list(self.vocab),
                'k': self.k
            }
            save_to_pickle(model_data, file_path)
            print(f"Model saved to {file_path}")
            return True
        except Exception as e:
            print(f"Error saving model: {str(e)}")
            return False
    
    @classmethod
    def load_model(cls, file_path: Optional[str] = None) -> Optional['Ngram']:
        """Load a trained model from a file."""
        if file_path is None:
            file_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'models',
                'ngram_model_v1.pkl'
            )
        
        try:
            model_data = load_from_pickle(file_path)
            model = cls(k=model_data.get('k', 1))
            model.unigrams = Counter(model_data.get('unigrams', {}))
            model.bigrams = Counter(model_data.get('bigrams', {}))
            model.trigrams = Counter(model_data.get('trigrams', {}))
            model.vocab = set(model_data.get('vocab', []))
            print(f"Model loaded from {file_path}")
            return model
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            return None

    def train(self, corpus=None, data_path=None, save_model: bool = True, force_reload: bool = False):
        """Train the n-gram model on the provided corpus or data file(s).
        
        Args:
            corpus: Optional text or list of texts to train on
            data_path: Optional path to CSV file or directory containing CSV files
            save_model: Whether to save the trained model to disk
            force_reload: If True, reprocess all CSVs even if pickles exist
            
        Returns:
            bool: True if training was successful, False otherwise
        """
        print("Starting training...")
        start_time = pd.Timestamp.now()
        
        try:
            if corpus:
                print("Training on provided corpus...")
                if isinstance(corpus, str):
                    self._train_on_text(corpus)
                elif isinstance(corpus, (list, tuple)):
                    for i, text in enumerate(corpus, 1):
                        if i % 1000 == 0:
                            print(f"Processed {i}/{len(corpus)} texts...")
                        self._train_on_text(str(text))
            else:
                # Handle data path (file or directory)
                if os.path.isdir(data_path):
                    # Get all CSV files in directory
                    csv_files = [os.path.join(data_path, f) for f in os.listdir(data_path) 
                               if f.endswith(('.csv', '.CSV'))]
                    if not csv_files:
                        print(f"No CSV files found in {data_path}")
                        return False
                else:
                    csv_files = [data_path] if data_path and os.path.exists(data_path) else []
                
                if not csv_files:
                    print("No valid data files provided for training")
                    return False
                
                print(f"Found {len(csv_files)} dataset(s) to process")
                processed_datasets = []
                
                for csv_file in csv_files:
                    try:
                        # Process the CSV file (or load from pickle)
                        dataset_name, dataset = load_or_process_csv(
                            csv_file, 
                            process_func=self._process_csv_file,
                            force_reload=force_reload
                        )
                        
                        if dataset:
                            processed_datasets.append((dataset_name, dataset))
                            print(f"Processed dataset '{dataset_name}' with {len(dataset.get('vocab', [])):,} unique words")
                        
                    except Exception as e:
                        print(f"Error processing {csv_file}: {str(e)}")
                        continue
                
                if not processed_datasets:
                    print("No valid datasets were processed")
                    return False
                
                # If we have multiple datasets, merge them
                if len(processed_datasets) > 1:
                    print(f"Merging {len(processed_datasets)} datasets...")
                    merged_data = merge_datasets(processed_datasets)
                    
                    # Update model with merged data
                    self.unigrams.update(merged_data.get('unigrams', {}))
                    self.bigrams.update(merged_data.get('bigrams', {}))
                    self.trigrams.update(merged_data.get('trigrams', {}))
                    self.vocab.update(merged_data.get('vocab', set()))
                    
                    print(f"Merged {len(merged_data.get('datasets', []))} datasets with {len(self.vocab):,} unique words")
                else:
                    # Single dataset
                    dataset_name, dataset = processed_datasets[0]
                    self.unigrams.update(dataset.get('unigrams', {}))
                    self.bigrams.update(dataset.get('bigrams', {}))
                    self.trigrams.update(dataset.get('trigrams', {}))
                    self.vocab.update(dataset.get('vocab', set()))
            
            training_time = (pd.Timestamp.now() - start_time).total_seconds()
            print(f"\nTraining completed in {training_time:.2f} seconds")
            print(f"Vocabulary size: {len(self.vocab):,}")
            print(f"Unigrams: {len(self.unigrams):,}, Bigrams: {len(self.bigrams):,}, Trigrams: {len(self.trigrams):,}")
            
            if save_model:
                self.save_model()
                
            return True
            
        except Exception as e:
            print(f"Error during training: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _train_on_text(self, text):
        try:
            tokens = tokenize(text)
            if not tokens or len(tokens) < 2:  # Need at least 2 tokens for bigrams
                return
                
            self.vocab.update(tokens)
            self.unigrams.update(tokens)
            
            # Create and count bigrams
            for i in range(len(tokens) - 1):
                bigram = (tokens[i], tokens[i + 1])
                self.bigrams[bigram] += 1
            
            # Create and count trigrams
            for i in range(len(tokens) - 2):
                trigram = (tokens[i], tokens[i + 1], tokens[i + 2])
                self.trigrams[trigram] += 1
                
        except Exception as e:
            print(f"Error in _train_on_text: {str(e)}")
            import traceback
            traceback.print_exc()

    def predict_next_word(self, text, top_k=5):
        if not self.vocab:
            print("Warning: Model not trained or vocabulary is empty!")
            return []
            
        try:
            tokens = tokenize(text)
            if not tokens:
                print(f"Warning: No tokens found for '{text}'")
                return []
                
            # Start with unigrams as fallback
            candidates = self.unigrams.most_common()
            
            # If we have at least one word, try bigrams
            if tokens and len(tokens) >= 1:
                last_word = tokens[-1]
                bigram_candidates = [(w2, count) for (w1, w2), count in self.bigrams.items() 
                                   if w1 == last_word]
                if bigram_candidates:
                    candidates = bigram_candidates
                    print(f"Found {len(bigram_candidates)} bigram candidates for '{last_word}'")
            
            # If we have at least two words, try trigrams
            if len(tokens) >= 2:
                prev_bigram = tuple(tokens[-2:])
                trigram_candidates = [(w3, count) for (w1, w2, w3), count in self.trigrams.items()
                                    if (w1, w2) == tuple(prev_bigram)]
                if trigram_candidates:
                    candidates = trigram_candidates
                    print(f"Found {len(trigram_candidates)} trigram candidates for '{prev_bigram}'")
            
            # Sort by frequency and take top_k
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            # Return just the words, not the counts
            result = [word for word, count in candidates[:top_k]]
            print(f"Predictions for '{text}': {result}")
            return result
            
        except Exception as e:
            print(f"Error in predict_next_word: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
