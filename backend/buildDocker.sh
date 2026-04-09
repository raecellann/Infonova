#!/bin/bash
set -e  # stop if any command fails

echo "Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Installing extra packages..."
pip install --no-cache-dir \
    python-dotenv \
    fastapi \
    uvicorn \
    requests \
    beautifulsoup4 \
    PyJWT \
    pandas \
    "pymongo[srv]==3.12" \
    python-multipart

echo "Build complete."
