#!/usr/bin/env bash
set -e

echo "=== Project Matilda Developer Environment Setup ==="

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

echo "Setting up Python virtual environment..."
cd backend
python3 -m venv venv || true
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
cd ..

echo "Installing Frontend dependencies..."
cd frontend
npm install
cd ..

echo "=== Environment Setup Complete! ==="
echo "To run backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "To run frontend: cd frontend && npm run dev"
