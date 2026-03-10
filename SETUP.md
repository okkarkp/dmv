# Local Setup (without Docker)

## Prerequisites

- Python 3.10+

## Steps

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` installs: `fastapi`, `uvicorn`, `openpyxl`, `requests`

### 2. Create required directories

```bash
mkdir -p uploads outputs logs
```

### 3. Start the app

```bash
bash start_all.sh
```

This runs:

```bash
python3 -m uvicorn ui_app:app --host 0.0.0.0 --port 8085
```

The app will be available at **http://localhost:8085**

---

## Optional: AI Features

AI suggestions are disabled by default. To enable, edit `config.yaml`:

```yaml
ai:
  enabled: true
  model_path: /path/to/tiny-llama.Q4_K_M.gguf
```

Then start the TinyLlama model server (requires a pre-built `llama.cpp`):

```bash
bash entrypoint.sh
```

The model server runs on port **8081**.
