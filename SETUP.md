# Local Setup Instructions

## Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional, for containerized setup)

---

## Option 1: Run Locally (without Docker)

### 1. Install Python dependencies

```bash
pip install fastapi uvicorn openpyxl requests python-multipart jinja2
```

Or install via the package:

```bash
pip install -e .
```

> The package (`setup.py` / `pyproject.toml`) also pulls in `pandas` and `openpyxl`.

### 2. Create required directories

```bash
mkdir -p uploads outputs logs sim_data
```

### 3. Start the web UI

```bash
bash start_all.sh
```

This runs:

```bash
python3 -m uvicorn ui_app:app --host 0.0.0.0 --port 8085
```

The app will be available at **http://localhost:8085**

---

## Option 2: Run with Docker Compose

```bash
docker compose up --build
```

The app will be available at **http://localhost:8085**

Mounted volumes:
- `./uploads` → `/app/uploads`
- `./outputs` → `/app/outputs`
- `./logs` → `/app/logs`

---

## Option 3: Run with Docker directly

```bash
docker run -p 8085:8085 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/logs:/app/logs \
  okkarkp/dmw-validator-ai:latest
```

---

## Optional: AI Features

AI suggestions are disabled by default. To enable, edit `config.yaml`:

```yaml
ai:
  enabled: true
  mode: embedded
  model_path: /path/to/tiny-llama.Q4_K_M.gguf
  n_threads: 4
  n_ctx: 2048
```

To also run the llama.cpp model server locally:

```bash
bash entrypoint.sh
```

This starts the TinyLlama model server on port **8081**.
