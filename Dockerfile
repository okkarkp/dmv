FROM python:3.10-slim

WORKDIR /app
COPY . /app

# 1️⃣ Install basic build tools (needed by llama-cpp-python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git && \
    rm -rf /var/lib/apt/lists/*

# 2️⃣ Create writable folders
RUN mkdir -p /app/uploads /app/outputs /app/logs /app/sim_data /app/models && chmod -R 777 /app

# 3️⃣ Install dependencies (including latest llama-cpp-python with GPT-4o tokenizer support)
RUN pip install --no-cache-dir \
    fastapi uvicorn openpyxl requests python-multipart \
    && pip install --no-cache-dir "llama-cpp-python>=0.2.90"

# 4️⃣ Copy model and expose ports
COPY models /app/models
EXPOSE 8081 8085

# 5️⃣ Start both AI microservice and Web UI
CMD ["bash", "start_all.sh"]
