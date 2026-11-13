#!/usr/bin/env bash
set -e

echo "=== JARVIS Assistant Installer ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m jarvis doctor
echo "=== Setup Complete. Run with ./scripts/run.sh ==="
