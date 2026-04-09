# Stop on errors
$ErrorActionPreference = "Stop"

# Create venv if it doesn’t exist
if (-Not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists, skipping..."
}

# Activate venv
Write-Host "Activating virtual environment..."
& .venv\Scripts\activate

# Upgrade pip
Write-Host "Upgrading pip..."
python.exe -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing Dependencies..."
pip install "pymongo[srv]==3.12" python-dotenv fastapi uvicorn requests bs4 jwt pandas python-multipart pytest-playwright langdetect playwright-stealth numpy pandas
pip freeze > requirements.txt

$playwrightBrowsersPath = "$env:USERPROFILE\AppData\Local\ms-playwright"
if (-Not (Test-Path $playwrightBrowsersPath)) {
    Write-Host "Playwright browsers not found, installing..."
    playwright install
} else {
    Write-Host "Playwright browsers already installed, skipping..."
}

# Set port
Write-Host "Exporting port..."
$env:PORT = 8000

# Run FastAPI app
Write-Host "Running the API..."
uvicorn main:app --reload --port $env:PORT
