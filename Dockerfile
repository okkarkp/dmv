# --- Universal DMW Validator + AI (auto-builds llama-cpp if wheel missing) ---
FROM python:3.10-slim

ARG TARGETARCH
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY . /app

# 1️⃣ System build tools for compiling llama-cpp from source if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git && \
    rm -rf /var/lib/apt/lists/*

# 2️⃣ Writable folders
RUN mkdir -p /app/uploads /app/outputs /app/logs /app/sim_data && chmod -R 777 /app

# 3️⃣ Core Python deps
RUN pip install --no-cache-dir fastapi uvicorn openpyxl requests python-multipart

# 4️⃣ Try prebuilt wheel first; if not found, compile from source automatically
RUN echo "🏗️ Building for architecture: ${TARGETARCH}" && \
    pip install --no-cache-dir "llama-cpp-python>=0.3.2" || \
    (echo "⚙️  Wheel not found; building llama-cpp-python from source..." && \
     pip install --no-cache-dir --verbose "llama-cpp-python>=0.3.2" --no-binary=llama-cpp-python)

# 5️⃣ Expose AI (8081) + Web (8085)
EXPOSE 8081 8085

# 6️⃣ Start AI + Web UI
CMD ["bash", "start_all.sh"]
