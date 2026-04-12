#!/bin/bash
set -e

echo "=== JusticIA startup ==="

# Install Python dependencies
echo "[1/3] Installing Python dependencies..."
if python3 -m pip install -r backend/requirements.txt -q 2>/tmp/justicia_pip.err; then
  echo "Python dependencies installed."
else
  if grep -q "externally-managed-environment" /tmp/justicia_pip.err; then
    echo "Python environment is externally managed (Nix). Skipping pip install."
  else
    cat /tmp/justicia_pip.err
    exit 1
  fi
fi

# Build frontend if dist doesn't exist
if [ ! -d "frontend/dist" ]; then
  echo "[2/3] Building frontend..."
  cd frontend
  npm install -q
  npm run build -q
  cd ..
else
  echo "[2/3] Frontend already built, skipping."
fi

# Start FastAPI
echo "[3/3] Starting FastAPI server..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
