import json
from llama_cpp import Llama
import importlib.resources as pkg_resources
import dmw_validator

with pkg_resources.open_text(dmw_validator, "config.json") as f:
    cfg = json.load(f)

MODEL_PATH = cfg["models"][cfg["default_model"]]

def _cfg_max_tokens(key: str, fallback: int) -> int:
    """Read max_tokens from centralised config; fall back to supplied default."""
    return int(cfg.get("max_tokens", {}).get(key, fallback))

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_threads=4,
    temperature=0.1,       # low temp for deterministic output
    repeat_penalty=1.2,
    verbose=False
)

def run_llm(prompt: str) -> str:
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=_cfg_max_tokens("spec2code", 4096)
    )
    return response["choices"][0]["message"]["content"].strip()
