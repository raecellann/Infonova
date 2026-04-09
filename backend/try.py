import pickle as pk
import json
import os


file = "trained_models/tfidf_index_v1.pkl"

with open(file, "rb") as f:
    print(pk.load(f))

# # Load the model
# file = "trained_models/bow_naive_bayes_model_v1.pkl"
# with open(file, "rb") as f:
#     model_data = pk.load(f)

# # Create output directory if it doesn't exist
# output_dir = "model_data"
# os.makedirs(output_dir, exist_ok=True)

# # Save as JSON
# output_file = os.path.join(output_dir, "model_v2.json")
# with open(output_file, "w", encoding='utf-8') as f:
#     # Convert numpy arrays to lists for JSON serialization
#     serializable_data = {
#         'class_counts': model_data['class_counts'],
#         'vocab_size': model_data['vocab_size'],
#         'class_word_counts': {
#             cls: {word: int(count) for word, count in word_counts.items()}
#             for cls, word_counts in model_data['class_word_counts'].items()
#         }
#     }
#     json.dump(serializable_data, f, indent=2, ensure_ascii=False)

# print(f"Model data saved to {output_file}")