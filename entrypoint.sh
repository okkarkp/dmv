#!/bin/bash
echo "[tinyllama-server] Starting..."
./llama.cpp/build/bin/llama-server \
  --model models/tiny-llama.Q4_K_M.gguf \
  --port 8081 \
  --host 0.0.0.0
