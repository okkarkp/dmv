#!/bin/bash
set -e

echo "=============================================="
echo "[BOOT] Starting DMW Validator Web UI on port 8085..."

exec python3 -m uvicorn ui_app:app \
  --host 0.0.0.0 \
  --port 8085