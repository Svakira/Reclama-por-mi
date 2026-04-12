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

# Always build frontend so deployed UI stays up to date
echo "[2/3] Building frontend..."
cd frontend
npm install -q
npm run build -q
cd ..

# Start FastAPI
echo "[3/3] Starting FastAPI server..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-5000}"
