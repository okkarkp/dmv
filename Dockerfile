# --- Universal DMW Validator (Web only) ---
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY . /app

# System build tools (keep – required by you)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

# Required folders (IMPORTANT)
RUN mkdir -p /app/uploads /app/outputs /app/logs /app/sim_data /app/static /app/templates \
    && chmod -R 777 /app

# Python deps (FIX: add jinja2)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    openpyxl \
    requests \
    python-multipart \
    jinja2

EXPOSE 8085

CMD ["bash", "start_all.sh"]
