#!/usr/bin/env python3
import json
from pathlib import Path

def _load():
    here = Path(__file__).resolve().parent
    cfg_path = here / "config.json"
    if not cfg_path.exists():
        # Safe defaults if config is missing
        return {
            "web": {"host":"0.0.0.0","port":8085},
            "ai": {"enabled": False, "mode":"auto", "ai_model":"Phi-4-mini-instruct-Q4_K_M.gguf",
                   "ai_model_path": str(here / "models" / "Phi-4-mini-instruct-Q4_K_M.gguf"),
                   "ai_host":"127.0.0.1","ai_port":8080},
            "paths": {"uploads": str(here / "uploads"),
                      "outputs": str(here / "outputs"),
                      "logs": str(here / "logs")}
        }
    with cfg_path.open() as f:
        return json.load(f)

CFG = _load()
AI_CFG   = CFG.get("ai", {})
PATHS    = CFG.get("paths", {})
WEB_CFG  = CFG.get("web", {})
