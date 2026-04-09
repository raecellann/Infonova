#!/bin/bash

# Exit if any command fails
# set -e


# if [ ! -d "node_modules" ]; then
#   echo "node_modules not found. Installing dependencies..."
#   npm install
# fi
# echo "🔧 Building app..."

# npm run build

# echo "🧹 Cleaning up previous htdocs files..."
# rm -rf /mnt/c/xampp/htdocs/myapp/*
# mkdir -p /mnt/c/xampp/htdocs/myapp

# echo "📦 Moving built files to XAMPP htdocs..."
# cp -r ./dist/* /mnt/c/xampp/htdocs/myapp/

# echo "✅ Build and deployment complete!"

#!/bin/bash

# Exit if any command fails
set -e


if [ ! -d "node_modules" ]; then
  echo "node_modules not found. Installing dependencies..."
  npm install
  npm audit fix
fi

echo ""
if [ ! -d "dist" ]; then
  echo "dist not found. 🔧 Building app..."
  npm run build
fi


echo "🧹 Cleaning up previous htdocs files..."
if [ -d "/mnt/c/xampp/htdocs/myapp/*" ]; then
  echo "/mnt/c/xampp/htdocs/myapp/* found. Cleaning up..."
  rm -rf /mnt/c/xampp/htdocs/myapp/*
fi
mkdir -p /mnt/c/xampp/htdocs/myapp

echo "📦 Moving built files to XAMPP htdocs..."
cp -r ./dist/* /mnt/c/xampp/htdocs/myapp/

echo "✅ Build and deployment complete!"