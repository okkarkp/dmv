#!/bin/bash
LOG=/opt/oss-migrate/logs/llama.log
PORT=8080
MODEL=/root/gptmodels/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf
BIN=/root/llama.cpp/build/bin/llama-server

if ! nc -z 127.0.0.1 $PORT 2>/dev/null; then
  echo "[INFO] Llama server not running, starting..."
  nohup $BIN -m $MODEL --ctx-size 512 --threads 8 --port $PORT --host 127.0.0.1 > $LOG 2>&1 &
  sleep 3
else
  echo "[INFO] Llama server already running on port $PORT."
fi

curl -s http://127.0.0.1:$PORT/v1/models || echo "[WARN] Still unreachable."
