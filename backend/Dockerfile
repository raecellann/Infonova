# Use an official Python runtime as a base image
FROM python:3.12-slim

# Prevent Python from writing pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-venv \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list and build script first (for Docker caching)
COPY requirements.txt buildDocker.sh ./

# Run your script to install dependencies
RUN chmod +x buildDocker.sh && ./buildDocker.sh

# Copy the rest of your project
COPY . .

# Expose the FastAPI port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
