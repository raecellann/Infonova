# Exit if any command fails
$ErrorActionPreference = "Stop"

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "node_modules not found. Installing dependencies..."
    npm install
    npm audit fix 
}

# Check if dist exists
if (-not (Test-Path "dist")) {
    Write-Host "Building app..."
    npm run build
}

Write-Host "Cleaning up previous htdocs files..."
# Check if "C:\xampp\htdocs\myapp\*" exists
if (Test-Path "C:\xampp\htdocs\myapp\*") {
    Remove-Item -Path "C:\xampp\htdocs\myapp\*" -Recurse -Force
}

New-Item -ItemType Directory -Force -Path "C:\xampp\htdocs\myapp"

Write-Host "Moving built files to XAMPP htdocs..."
Copy-Item -Path ".\dist\*" -Destination "C:\xampp\htdocs\myapp" -Recurse -Force

Write-Host "Build and deployment complete!"
npm run dev