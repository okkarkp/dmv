#!/bin/bash
echo "=============================================="
echo "[BOOT] Starting AI microservice on port 8081..."
python3 -m uvicorn ai_server:app --host 0.0.0.0 --port 8081 &
sleep 3
echo "[BOOT] Starting DMW Validator Web UI on port 8085..."
python3 -m uvicorn dmw_web_app:app --host 0.0.0.0 --port 8085
echo "----------------------------------------------"
echo "[READY] ✅ Services running"
echo "[INFO] Web UI : http://localhost:8085"
echo "[INFO] AI Port: http://127.0.0.1:8081"
