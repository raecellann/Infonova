import os
import pickle
from pathlib import Path
from typing import Any, Optional

def save_to_pickle(data: Any, file_path: str) -> None:
    """Save data to a pickle file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"Data saved to {file_path}")
    except Exception as e:
        print(f"Error saving pickle file {file_path}: {str(e)}")
        raise

def load_from_pickle(file_path: str) -> Any:
    """Load data from a pickle file."""
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Error loading pickle file {file_path}: {str(e)}")
        raise

def get_pickle_path(csv_path: str) -> str:
    """Convert a CSV file path to a pickle file path."""
    base = os.path.splitext(csv_path)[0]
    return f"{base}.pkl"

def get_dataset_name(file_path: str) -> str:
    """Extract a clean dataset name from file path."""
    base_name = os.path.basename(file_path)
    return os.path.splitext(base_name)[0]

def get_dataset_pickle_path(dataset_name: str) -> str:
    """Get the path for a dataset's pickle file."""
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models')
    os.makedirs(models_dir, exist_ok=True)
    return os.path.join(models_dir, f"{dataset_name}.pkl")

def get_all_dataset_pickles() -> list:
    """Get a list of all dataset pickle files."""
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'models')
    if not os.path.exists(models_dir):
        return []
    return [f for f in os.listdir(models_dir) if f.endswith('.pkl') and f != 'ngram_model_v1.pkl']

def load_or_process_csv(csv_path: str, process_func, force_reload: bool = False):
    """
    Load data from pickle if exists and not force_reload, otherwise process CSV and save as pickle.
    
    Args:
        csv_path: Path to the CSV file
        process_func: Function that takes a file path and returns processed data
        force_reload: If True, always reprocess the CSV even if pickle exists
        
    Returns:
        Tuple of (dataset_name, processed_data)
    """
    dataset_name = get_dataset_name(csv_path)
    pickle_path = get_dataset_pickle_path(dataset_name)
    
    if not force_reload and os.path.exists(pickle_path):
        print(f"Loading dataset '{dataset_name}' from pickle: {pickle_path}")
        try:
            return dataset_name, load_from_pickle(pickle_path)
        except Exception as e:
            print(f"Failed to load pickle for '{dataset_name}', reprocessing CSV: {str(e)}")
    
    # Process CSV and save as pickle
    print(f"Processing dataset '{dataset_name}' from CSV: {csv_path}")
    data = process_func(csv_path)
    save_to_pickle(data, pickle_path)
    return dataset_name, data

def merge_datasets(datasets: list) -> dict:
    """Merge multiple datasets into a single dataset."""
    if not datasets:
        return {}
        
    merged = {
        'unigrams': {},
        'bigrams': {},
        'trigrams': {},
        'vocab': set(),
        'datasets': []
    }
    
    for dataset_name, dataset in datasets:
        if not dataset:
            continue
            
        merged['datasets'].append(dataset_name)
        
        # Merge unigrams
        for k, v in dataset.get('unigrams', {}).items():
            merged['unigrams'][k] = merged['unigrams'].get(k, 0) + v
            
        # Merge bigrams
        for k, v in dataset.get('bigrams', {}).items():
            merged['bigrams'][k] = merged['bigrams'].get(k, 0) + v
            
        # Merge trigrams
        for k, v in dataset.get('trigrams', {}).items():
            merged['trigrams'][k] = merged['trigrams'].get(k, 0) + v
            
        # Merge vocabulary
        merged['vocab'].update(dataset.get('vocab', set()))
    
    return merged
