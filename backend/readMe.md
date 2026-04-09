# 📄 Backend Documentation
```mermaid
flowchart LR
  TP[🧹 Text Preprocessing] --> BOW[🧮 BoW / Naive Bayes]
  BOW --> TF[🔤 TF-IDF Vectorization]
  TF --> DB[(🗄️ Database)]
  DB --> SS[🔎 Similarity Search]
  
  classDef step fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
  classDef db fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#4e342e;
  classDef result fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
  
  class TP,BOW,TF step;
  class DB db;
  class SS result;
  
  linkStyle default stroke:#90caf9,stroke-width:2px;
```

## 🔎 Project Overview
This is a FastAPI backend that provides a comprehensive API for news and information management. It offers powerful search capabilities, user account management, and machine learning features for text processing and classification.

## 🗞️ Project Purpose
The backend's goal is to create a robust API platform that allows users to access news and information from multiple sources in one location. It aims to simplify the process of staying informed by providing powerful search capabilities, text classification, and user management features.

## Backend Overview

- Built with **FastAPI**, a modern, fast (high-performance) web framework for building APIs with Python 3.7+.
- Uses **CORS middleware** to allow cross-origin requests from any origin.
- Modular structure with controllers, routes, middlewares, models, schemas, and utilities.
- Implements **Machine Learning** capabilities including:
  - **N-gram models** for text prediction and autocomplete
  - **TF-IDF vectorization** for similarity search and text analysis
- **MongoDB Atlas** integration for data persistence
- **Web scraping** capabilities for news data collection

## Project Structure

```
/backend
  ├── main.py                    # FastAPI app entry point
  ├── src/
      ├── controllers/           # API controllers
      │   ├── accountController.py      # User account management
      │   ├── homeControllers.py        # Home page endpoints
      │   ├── tfidfController.py       # TF-IDF search and analysis
      │   └── ngramController.py       # Text prediction
      ├── routes/                # API route definitions
      │   ├── accountRoutes.py         # Account-related routes
      │   ├── homeRoutes.py            # Home page routes
      │   ├── tfidfRoutes.py          # TF-IDF search routes
      │   ├── ngramRoutes.py          # Text prediction routes
      │   └── index.py                # Main router configuration
      ├── middlewares/           # Authentication and authorization
      │   ├── authentication.py       # JWT authentication
      │   └── authorization.py        # Role-based access control
      ├── models/                # Database models and ML models
      │   ├── User.py                 # User data model
      │   ├── tfidf/                 # TF-IDF models and search engine
      │   │   ├── tfidf_search_engine.py
      │   │   └── integrated_search_engine.py
      │   ├── tfidf.py               # TF-IDF vectorization
      │   ├── tfidf_vectorizer.py    # TF-IDF vectorizer
      │   └── Ngram.py               # Text prediction model
      ├── schemas/               # Data validation schemas
      │   ├── accountSchema.py        # Account validation
      │   └── createAccount.py        # Account creation validation
      ├── core/                  # Core functionality
      │   └── mongodb_connect.py     # Database connection
      ├── utils/                 # Utility functions
      │   ├── hash.py                 # Password hashing
      │   └── mb_scraper.py          # News web scraper
      └── data/                  # Training data and datasets
          └── MANILA_datasets.csv # News articles dataset
              CNN_datasets.csv 
              GMA_datasets.csv 
              INQUIRER_datasets.csv 
              MANILA_datasets.csv 
              RAPPLER_datasets.csv 
```

## API Endpoints


### 🤖 N-gram Text Prediction (`/v1/ngram`)
- **POST** `/generate-ngrams` - Generate word n-grams from text
- **POST** `/predict-next-word` - Predict next word in sequence
- **GET** `/auto-suggest` - Get autocomplete suggestions

### 🔤 TF-IDF Search (`/v1/tfidf`)
- **GET** `/search` - Search documents using TF-IDF similarity
  - Query params:
    - `query` (string, required): Search query string
    - `limit` (int, default: 10): Max results to return (1-100)
    - `offset` (int, default: 0): Results to skip for pagination
    - `source` (string, optional): Filter by source label (e.g., GMA, RAPPLER)
    - `min_score` (float, default: 0.05): Minimum similarity score (0-1)
- **GET** `/status` - Get TF-IDF service/model status

## Backend Process Flow 🔄

### 1. Text Preprocessing 🧹
- Input text is cleaned and normalized
- Remove special characters, URLs, and extra whitespace
- Convert to lowercase for consistent processing
- Tokenize into individual words/phrases

### 2. BoW / Naive Bayes Classification (Background) 🧮
- Convert preprocessed text into Bag of Words representation
- Run Naive Bayes classification as a background/offline process
- Generate prior probabilities and category hints per document
- Store category labels/scores for downstream filtering and analytics

### 3. TF-IDF Vectorization 🔤
- Transform text into TF-IDF (Term Frequency-Inverse Document Frequency) vectors
- Calculate term frequencies within documents
- Compute inverse document frequencies across the corpus
- Create high-dimensional vectors representing document content
- Store vectors for efficient similarity search

### 4. Database Storage 🗄️
- Store processed documents and their TF-IDF vector representations
- Index vectors for fast similarity search
- Maintain metadata (titles, snippets, categories)
- Cache TF-IDF model artifacts and training data

### 5. Similarity Search 🔎
- Compare query vector against stored document vectors using TF-IDF
- Calculate cosine similarity scores for relevance
- Rank documents by similarity score
- Return top-k most similar results with TF-IDF confidence scores

## Dependencies

- **FastAPI** - Modern web framework for building APIs
- **Uvicorn** - ASGI server for running FastAPI
- **PyMongo** - MongoDB driver for Python
- **Pandas** - Data manipulation and analysis
- **Scikit-learn** - Machine learning library
- **Playwright** - Web scraping and automation
- **BeautifulSoup4** - HTML parsing
- **JWT** - JSON Web Token authentication
- **Python-dotenv** - Environment variable management

## Setup & Installation

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment configuration:**
   Create `.env` file:
   ```bash
   URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
   API_KEY=<your-api-key>
   API_SECRET_KEY=<jwt-secret>
   PORT=8000
   ```

4. **Run the server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## Features

### 🔍 Search & Discovery
- **TF-IDF based search** for relevant article retrieval
- **N-gram autocomplete** for search suggestions
- **Similarity scoring** for result ranking

### 🧠 Machine Learning
- **TF-IDF vectorization** for document representation
- **Similarity search** using cosine similarity
- **Model training** from document datasets
- **Real-time search** with relevance scoring

### 👤 User Management
- **Account registration** and authentication
- **JWT-based security** for API access
- **User profile management**
- **Password hashing** for security

### 📰 News Data
- **Web scraping** for news article collection
- **Content preprocessing** and cleaning
- **Multi-language detection** and filtering
- **Structured data storage** in MongoDB

## API Response Examples

### N-gram Autocomplete
```json
{
  "success": true,
  "message": "Suggestions generated successfully",
  "suggestions": ["machine", "learning", "artificial", "intelligence"]
}
```

### Search Results
```json
{
  "success": true,
  "message": "Search results",
  "results": [
    {
      "id": "doc123",
      "title": "Machine Learning Advances",
      "snippet": "Recent developments in ML...",
      "score": 0.87
    }
  ]
}
```

### TF-IDF Search Results
```json
{
  "success": true,
  "message": "Search completed successfully!",
  "data": {
    "query": "machine learning technology",
    "results": [
      {
        "id": "doc123",
        "title": "Machine Learning Advances",
        "snippet": "Recent developments in ML...",
        "similarity_score": 0.87,
        "tfidf_score": 0.92
      }
    ],
    "total_results": 1,
    "search_time": "0.023s"
  }
}
```

## Common Errors & Troubleshooting

- **400 Bad Request**: Missing required fields, invalid input format
- **401 Unauthorized**: Invalid or missing authentication token
- **422 Unprocessable Entity**: Validation errors, duplicate data
- **500 Internal Server Error**: Server-side processing errors

## Development Scripts

- `uvicorn main:app --reload` - Start development server
- `python -m pytest` - Run tests
- `python src/utils/mb_scraper.py` - Run news scraper

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

---

