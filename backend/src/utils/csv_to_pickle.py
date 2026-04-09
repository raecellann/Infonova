import pandas as pd
import os
import glob
from pathlib import Path

def merge_csv_to_pickle():
    """
    Merge all CSV files from the data directory into a single pickle file.
    The script assumes all CSV files have the same structure.
    """
    # Define paths
    base_dir = Path(__file__).parent.parent.parent  # Go up to backend directory
    data_dir = base_dir / 'data'
    output_file = data_dir / 'datasets.pkl'
    
    # Get all CSV files in the data directory
    csv_files = glob.glob(str(data_dir / '*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in {data_dir}")
        return
    
    print(f"Found {len(csv_files)} CSV files to process...")
    
    # Initialize an empty list to store dataframes
    dfs = []
    
    # Read each CSV file and append to the list
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            dfs.append(df)
            print(f"Processed {os.path.basename(file)}: {len(df)} rows")
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
    
    if not dfs:
        print("No valid CSV files were processed.")
        return
    
    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Save to pickle
    combined_df.to_pickle(output_file)
    print(f"\nSuccessfully merged {len(dfs)} files with {len(combined_df)} total rows")
    print(f"Combined data saved to: {output_file}")
    
    # Print some basic info about the combined data
    print("\nCombined DataFrame Info:")
    print(f"Total rows: {len(combined_df)}")
    print("\nFirst few rows:")
    print(combined_df.head())

if __name__ == "__main__":
    # Uncomment the line below to regenerate the pickle file
    merge_csv_to_pickle()