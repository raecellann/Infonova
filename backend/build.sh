#!/bin/bash
set -e  # stop if any command fails

# Ensure python3-venv is installed
if ! dpkg -s python3-venv >/dev/null 2>&1; then
    echo "python3-venv is not installed. Installing..."
    sudo apt-get update && sudo apt-get install -y python3-venv
fi

# Create virtual environment if it doesn’t exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# For Windows PowerShell, use: venv\Scripts\activate

# Upgrade pip inside venv
pip install --upgrade pip

# Install dependencies inside venv
pip install python-dotenv fastapi uvicorn requests bs4 jwt pandas "pymongo[srv]==3.12" python-multipart pytest-playwright langdetect playwright-stealth

# Set port
export PORT=8000

# Run FastAPI app
uvicorn main:app --reload --port $PORT



