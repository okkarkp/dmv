

#!/bin/bash
echo "=============================================="
echo "[BOOT] Starting DMW Validator Web UI on port 8085..."
python3 -m uvicorn ui_app:app \
  --host 0.0.0.0 \
  --port 8085
echo "----------------------------------------------"
echo "[READY] ✅ Services running"
echo "[INFO] Web UI : http://localhost:8085"
