## 🔎 Project Overview
This project is a web application with a React frontend and a FastAPI backend. It offers a website with access to news and information along with search and user account management features.

## 🗞️ Project Purpose
The project's goal is to create a platform that will allow users to get news and information from multiple sources in one location. It aims to simplify the process of staying informed by searching articles and providing powerful search capabilities to quickly find relevant content.

## Backend Overview

- Built with **FastAPI**, a modern, fast (high-performance) web framework for building APIs with Python 3.7+.
- Uses **CORS middleware** to allow cross-origin requests from any origin.
- Modular structure with controllers, routes, middlewares, models, schemas, and utilities.

## Frontend Overview

- Built with **React** using **React Router** for client-side routing.
- Main pages include:
  - **Home**: Landing page displaying a welcome message.
  - **Search**: Search interface for querying articles.
  - **Result**: Displays search results and news articles.
- Uses modern frontend tools including **Vite** for build tooling, **TailwindCSS** for styling, and **styled-components**.

## 📂 Project Structure

```
/backend
  ├── main.py                # FastAPI app entry point
  ├── src/
      ├── controllers/       # API controllers
      ├── routes/            # API route definitions
      ├── middlewares/       # Authentication and authorization
      ├── models/            # Database models
      ├── schemas/           # Data validation schemas
      └── utils/             # Utility functions

/frontend
  ├── src/
      ├── components/        # React components
      ├── pages/             # React pages (Home, Search, Result)
      ├── assets/            # Images and static assets
      ├── Layouts/           # Layout components
      └── App.jsx            # React app entry point
  ├── package.json           # Frontend dependencies and scripts
```

## ⛏️ Dependencies

- Backend: FastAPI, Uvicorn, and related Python packages.
- Frontend: React, React Router, Vite, TailwindCSS, styled-components, axios.

## 🐳 Docker Setup

This project supports Docker for quick setup and deployment.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- A running MongoDB instance (local or cloud).

You must set the `MONGODB_URI` environment variable or create a `.env` file in the root of the project with your actual connection string.

✅ Example for **MongoDB Atlas**:
```
MONGODB_URI=mongodb+srv://username:password@cluster0.abcd.mongodb.net/myDatabase
```

✅ Example for **local MongoDB**:
```
MONGODB_URI=mongodb://localhost:27017/myDatabase
```
---

### 🔨 Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/college-of-mary-immaculate/esmabe-gallardo-galvez-nolasco-staana.git
   
   cd <project-directory>
   ```

2. **Set the environment variable for MongoDB:**
   Create a `.env` file in the root directory with:
   ```
   MONGODB_URI=mongodb+srv://<your-username>:<your-password>@<your-cluster-url>/<your-database>
   ```

3. **Build and run the containers:**
   ```bash
   docker-compose up --build -d
   ```

4. **Access the application:**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000

---

### Useful Docker Commands

| Action                        | Command                                    |
|-------------------------------|---------------------------------------------|
| Check running containers      | `docker ps`                                 |
| Start containers              | `docker-compose up`                         |
| Build containers              | `docker-compose build`                      |
| Build & run (detached)        | `docker-compose up --build -d`             |
| View container logs           | `docker logs -f <container_name>`          |
| Stop & remove containers      | `docker-compose down`                       |

## Scope and Limitations

### 📘 Scope
- Infonova uses datasets from GMA, RAPPLER, Inquirer and Manila Bulletin for training and testing.
- Displays 10 news articles per result page.
- When no suggestion is found, the system falls back to unigram suggestions.
- Mainly supports English words for normalization and processing.


### ⚠️ Limitations
- The model needs to be reloaded to maintain its accuracy.
- Non-English words or mixed-language articles may not be processed correctly.
- It is word based only. It won’t suggest results for partial words (example: typing “compu” won’t suggest “computer”).
- The system is trained on small datasets.
- TF-IDF only counts word frequency, but it cannot recognize synonyms, semantics, or the relationships between words.
- Naive Bayes assumes all words are independent, making it less accurate with context-dependent text. 

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

### Contributors
Big thanks to the following contributors who made this project possible. 

1. Wilson
2. Izyne
3. Daniel
4. Eleina
5. Raecell Ann