#!/usr/bin/env python3
from pathlib import Path
import os
import json

# ------------------------------------------------------------
# Base directory (project root)
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

def _p(env_key: str, default: Path) -> Path:
    """
    Resolve path from environment variable if present,
    otherwise use project-relative default.
    """
    return Path(os.environ.get(env_key, str(default))).resolve()

# ------------------------------------------------------------
# PATHS (works for local, Docker, Azure VM)
# ------------------------------------------------------------
PATHS = {
    "uploads": _p("DMW_UPLOADS", BASE_DIR / "uploads"),
    "outputs": _p("DMW_OUTPUTS", BASE_DIR / "outputs"),
    "logs": _p("DMW_LOGS", BASE_DIR / "logs"),
    "sim_data": _p("DMW_SIM_DATA", BASE_DIR / "sim_data"),
}

# Ensure directories exist
for p in PATHS.values():
    p.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# AI configuration
# ------------------------------------------------------------
AI_CFG = {
    "enabled": False,
    "ai_host": os.environ.get("AI_HOST", "127.0.0.1"),
    "ai_port": int(os.environ.get("AI_PORT", "8081")),
    "ai_model": os.environ.get("AI_MODEL", "local-model"),
}

# ------------------------------------------------------------
# Web configuration
# ------------------------------------------------------------
WEB_CFG = {
    "host": os.environ.get("WEB_HOST", "0.0.0.0"),
    "port": int(os.environ.get("WEB_PORT", "8085")),
}

# ------------------------------------------------------------
# General config (optional)
# ------------------------------------------------------------
CFG = {
    "base_dir": str(BASE_DIR),
    "paths": {k: str(v) for k, v in PATHS.items()},
    "ai": AI_CFG,
    "web": WEB_CFG,
}

if __name__ == "__main__":
    print(json.dumps(CFG, indent=2))
