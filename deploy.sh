#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Target directory on the staging server
TARGET_DIR="/home/agentwhistle-snov-automation/htdocs/snov-automation.agentwhistle.com/snov"

echo "=================================================="
echo "🚀 Starting Deployment on Staging Server..."
echo "=================================================="

# Navigate to the project root directory
echo "📂 Navigating to project root: $TARGET_DIR..."
cd "$TARGET_DIR"

# 1. Setup/Update Python Backend
echo "🐍 Setting up Python backend virtual environment..."
cd backend
if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment (.venv)..."
  python3 -m venv .venv
fi

echo "🔌 Activating virtual environment and installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Verify if backend/.env file exists
if [ ! -f ".env" ]; then
  echo "⚠️  WARNING: backend/.env file is missing! Please configure SNOV_CLIENT_ID and SNOV_CLIENT_SECRET on the server."
else
  echo "✅ backend/.env file is present."
fi

# 2. Restart/Reload FastAPI Server under PM2
echo "🔄 Reloading FastAPI process using PM2..."
pm2 startOrReload ecosystem.config.js

# Go back to root
cd "$TARGET_DIR"

# 3. Setup/Build React Frontend
echo "💻 Setting up React frontend..."
cd frontend

echo "📦 Installing npm dependencies..."
npm install

# Verify if frontend/.env file exists with required keys
if [ ! -f ".env" ]; then
  echo "⚠️  WARNING: frontend/.env file is missing! VITE_SUPABASE_ANON_KEY must be set before building."
  echo "   Vite env vars are baked in at build time. Create frontend/.env with:"
  echo "   VITE_SUPABASE_URL=https://ocydnvzzvfucjxdjochw.supabase.co"
  echo "   VITE_SUPABASE_ANON_KEY=your_key_here"
elif ! grep -q "VITE_SUPABASE_ANON_KEY=.\+" .env; then
  echo "⚠️  WARNING: VITE_SUPABASE_ANON_KEY is empty in frontend/.env! Login will ask for manual key entry."
else
  echo "✅ frontend/.env file is present with VITE_SUPABASE_ANON_KEY."
fi

echo "🛠️ Building static assets for production..."
npm run build

echo "=================================================="
echo "🎉 Deployment Completed successfully!"
echo "=================================================="
