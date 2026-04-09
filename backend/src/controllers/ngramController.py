from fastapi import Request, HTTPException
import os
import sys
import pickle
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from models.Ngram import Ngram

class NgramController:
    def __init__(self, data_path=None, force_retrain=False):
        self.initialized = False
        self.model_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'trained_models'
        )
        self.model_path = os.path.join(self.model_dir, 'ngram_model_v1.pkl')
        
        # Ensure models directory exists
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Default data path if not provided
        if data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_path = os.path.join(base_dir, 'data')
            
        # If directory is provided, look for datasets.pkl in it
        if os.path.isdir(data_path):
            data_path = os.path.join(data_path, 'datasets.pkl')
            
        print(f"Looking for dataset at: {data_path}")
        
        # Try to load existing model first if not forcing retrain
        if not force_retrain:
            try:
                # Look for existing model files
                model_files = [f for f in os.listdir(self.model_dir) 
                             if f.startswith('ngram_') and f.endswith('.pkl')]
                
                if model_files:
                    # Try to load the most recent model
                    model_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.model_dir, x)), 
                                  reverse=True)
                    model_path = os.path.join(self.model_dir, model_files[0])
                    
                    print(f"Loading existing ngram model from: {model_path}")
                    self.ngram = Ngram.load_model(model_path)
                    
                    if hasattr(self.ngram, 'vocab') and self.ngram.vocab:
                        print(f"✓ Successfully loaded ngram model with vocabulary size: {len(self.ngram.vocab)}")
                        self.initialized = True
                        return
                    else:
                        print("Warning: Loaded model has no vocabulary, will retrain...")
                
            except Exception as e:
                print(f"Error loading existing model: {e}")
                print("Will attempt to train a new model...")
        
        # If we get here, we need to train a new model
        print("Initializing new model...")
        self.ngram = Ngram(k=1)  # Using add-1 smoothing
        
        try:
            if not os.path.exists(data_path):
                # Try to find any .pkl file in the data directory
                data_dir = os.path.dirname(data_path)
                pkl_files = [f for f in os.listdir(data_dir) if f.endswith('.pkl')]
                if pkl_files:
                    data_path = os.path.join(data_dir, pkl_files[0])
                    print(f"Using found dataset: {data_path}")
                else:
                    raise FileNotFoundError(f"No dataset file found in {data_dir}")
            
            print(f"Loading dataset from: {data_path}")
            with open(data_path, 'rb') as f:
                try:
                    datasets = pickle.load(f)
                except Exception as e:
                    raise ValueError(f"Error loading dataset file {data_path}: {str(e)}")
            
            # Handle both DataFrame and dictionary formats
            all_texts = []
            
            if isinstance(datasets, pd.DataFrame):
                # Handle direct DataFrame
                print(f"Processing DataFrame with columns: {datasets.columns.tolist()}")
                if 'text' in datasets.columns:
                    all_texts.extend(datasets['text'].dropna().astype(str).tolist())
                elif 'content' in datasets.columns:
                    all_texts.extend(datasets['content'].dropna().astype(str).tolist())
                else:
                    # If no text or content column, try to use the first string column
                    for col in datasets.columns:
                        if datasets[col].dtype == 'object':
                            all_texts.extend(datasets[col].dropna().astype(str).tolist())
                            break
            elif isinstance(datasets, dict):
                # Handle dictionary of DataFrames/lists
                for dataset_name, dataset in datasets.items():
                    if isinstance(dataset, pd.DataFrame):
                        if 'text' in dataset.columns:
                            all_texts.extend(dataset['text'].dropna().astype(str).tolist())
                        elif 'content' in dataset.columns:
                            all_texts.extend(dataset['content'].dropna().astype(str).tolist())
                    elif isinstance(dataset, list):
                        all_texts.extend([str(text) for text in dataset if pd.notna(text)])
            else:
                raise ValueError(f"Unsupported data format in datasets.pkl: {type(datasets)}")
                
            print(f"Collected {len(all_texts)} text samples for training")
            
            if not all_texts:
                raise ValueError("No valid text data found in the datasets")
                
            # Train directly with the text corpus (no temporary file)
            print(f"Training model with {len(all_texts)} text samples...")
            
            # Combine all texts into a single corpus string
            corpus_text = "\n".join(all_texts)
            
            # Train the model directly with corpus parameter
            self.ngram.train(corpus=corpus_text, save_model=False)
            
            if not self.ngram.vocab:
                raise ValueError("Model training failed - empty vocabulary")
            
            # Save the model to our desired location
            self.ngram.save_model(self.model_path)
            
            print(f"Ngram model trained successfully with {len(self.ngram.vocab)} words in vocabulary")
            self.initialized = True
            
        except Exception as e:
            print(f"Error initializing Ngram model: {str(e)}")
            import traceback
            traceback.print_exc()
            self.initialized = False
    
    def _find_new_datasets(self, data_path: str) -> list:
        """Find datasets that haven't been processed yet."""
        if not os.path.exists(data_path):
            return []
            
        # Get all CSV files in data directory
        if os.path.isdir(data_path):
            csv_files = [os.path.join(data_path, f) for f in os.listdir(data_path) 
                        if f.endswith(('.csv', '.CSV'))]
        else:
            csv_files = [data_path] if data_path.endswith(('.csv', '.CSV')) else []
        
        # Get list of already processed datasets
        processed_datasets = set()
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    processed_datasets = set(model_data.get('processed_datasets', []))
            except Exception as e:
                print(f"Error reading processed datasets: {str(e)}")
        
        # Find new datasets that haven't been processed yet
        new_datasets = []
        for csv_file in csv_files:
            dataset_name = os.path.splitext(os.path.basename(csv_file))[0]
            if dataset_name not in processed_datasets:
                new_datasets.append(csv_file)
        
        return new_datasets
    
    def _update_model_with_new_data(self, new_data_paths: list):
        """Update the existing model with new data."""
        if not self.ngram or not self.initialized:
            print("Cannot update model: model not initialized")
            return False
            
        print(f"Updating model with {len(new_data_paths)} new datasets...")
        
        try:
            # Train on new data
            for data_path in new_data_paths:
                print(f"Processing new dataset: {os.path.basename(data_path)}")
                success = self.ngram.train(data_path=data_path, save_model=False)
                if not success:
                    print(f"Warning: Failed to process dataset: {data_path}")
            
            # Save the updated model
            self.ngram.save_model()
            print(f"Model updated successfully. New vocabulary size: {len(self.ngram.vocab)}")
            return True
            
        except Exception as e:
            print(f"Error updating model with new data: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _train_with_default_corpus(self) -> bool:
        """Train the model with a default corpus."""
        print("No dataset found, falling back to default corpus...")
        corpus_text = """
        I love playing chess with my friends in the evening. 
        He likes playing football with his friends at the park.
        We enjoy coding together after school.
        The quick brown fox jumps over the lazy dog.
        Machine learning is a subset of artificial intelligence.
        Natural language processing helps computers understand human language.
        Python is a popular programming language for data science.
        """
        return self.ngram.train(corpus=corpus_text, save_model=True)

    async def predict_next_word(self, request: Request):
        body = await request.json()
        text = body.get("text", "")

        if not text or not isinstance(text, str):
            raise HTTPException(status_code=400, detail={"success": False, "message": "Valid text is required"})

        predictions = self.ngram.predict_next_word(text)

        return {
            "success": True,
            "message": "Prediction generated successfully",
            "data": {
                "input_text": text,
                "predictions": predictions
            }
        }
        
        
    def get_suggestions(self, text: str, top_k: int = 5) -> list:
        """
        Get auto-suggestions for the given text.
        """
            
        if not text or not isinstance(text, str):
            return {
                "success": False,
                "message": "Invalid input text",
                "suggestions": []
            }
            
        try:
            print(f"Getting suggestions for: '{text}'")
            predictions = self.ngram.predict_next_word(text, top_k=top_k)
            
            # Ensure we return a list of strings (not tuples)
            suggestions = []
            if isinstance(predictions, list) and predictions:
                if isinstance(predictions[0], tuple):
                    suggestions = [word for word, _ in predictions]
                else:
                    suggestions = predictions
            
            print(f"Generated {len(suggestions)} suggestions")
            
            return {
                "success": True,
                "message": "Suggestions generated successfully",
                "suggestions": suggestions
            }
            
        except Exception as e:
            print(f"Error in get_suggestions: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "message": f"Error generating suggestions: {str(e)}",
                "suggestions": []
            }