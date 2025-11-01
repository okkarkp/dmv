import re, json, time
from llama_cpp import Llama
import importlib.resources as pkg_resources
import dmw_validator

# === Load configuration ===
with pkg_resources.open_text(dmw_validator, "config.json") as f:
    CFG = json.load(f)

def load_llm(model_choice="light"):
    """Dynamically load Tiny or Light model with optimized parameters."""
    model_path = CFG["models"].get(model_choice, CFG["models"]["light"])
    print(f"🧠 Loading model: {model_choice} → {model_path}")

    if model_choice == "tiny":
        params = dict(n_ctx=2048, n_threads=4, n_batch=128, temperature=0.08)
    elif model_choice == "light":
        params = dict(n_ctx=8192, n_threads=6, n_batch=512, temperature=0.1)
    else:
        params = dict(n_ctx=8192, n_threads=8, n_batch=512, temperature=0.12)

    print(f"⚙️  Model parameters: ctx={params['n_ctx']} | threads={params['n_threads']} | batch={params['n_batch']}")
    start = time.time()
    llm = Llama(model_path=model_path, top_p=0.8, repeat_penalty=1.05, verbose=False, **params)
    print(f"✅ Model ready in {time.time()-start:.1f}s")
    return llm


def _safe_json_parse(text):
    """Parse or recover JSON array responses."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict): parsed = [parsed]
        return parsed
    except Exception:
        objs = re.findall(r"\{[^\{\}]+\}", text, re.S)
        parsed = []
        for o in objs:
            try: parsed.append(json.loads(o))
            except: pass
        if parsed: return parsed
        return [{"judgement":"Unparsed","explanation":text.strip()[:400]}]


def _run_batch(batch, offset=0, focus="", llm=None, prompt_profile="business"):
    """Generate prompt tuned by profile and model type."""
    schema_hint = '{"judgement":"","explanation":"","suggested_followup":"","dq_sql":"","recon_sql":""}'
    rows = []
    for i, r in enumerate(batch):
        t = r.get("table") or r.get("Target Table") or r.get("Target Table Name", "")
        f = r.get("field") or r.get("Target Field") or r.get("Target Field Name", "")
        logic = r.get("data", {}).get("transformation logic") or r.get("data", {}).get("Transformation Logic") or "N/A"
        rows.append(f"RowID={offset+i+1} | Target Table={t} | Target Field={f} | Logic={logic}")
    rows_text = "\n".join(rows)

    model_path = getattr(llm, "model_path", None) or getattr(llm, "_model_path", "")
    model_id = str(model_path).lower()

    # === Prompt Profiles ===
    if prompt_profile == "business":
        system_prompt = (
            "You are a senior data business analyst reviewing DMW mappings. "
            "Explain in clear, simple language what each mapping does and whether it makes sense. "
            "Reply in JSON with keys: judgement, explanation, suggested_followup."
        )
    elif prompt_profile == "technical":
        system_prompt = (
            "You are a senior data engineer reviewing transformation logic. "
            "Detect syntax errors, invalid SQL, and mismatched source/target fields. "
            "Reply only in structured JSON keys: judgement, explanation, suggested_followup."
        )
    elif prompt_profile == "strict":
        system_prompt = (
            "Respond strictly in JSON only; no markdown, no text outside JSON. "
            "Schema: " + schema_hint
        )
    else:
        system_prompt = "Provide structured JSON analysis of each mapping: " + schema_hint

    if "tiny" in model_id:
        system_msg = {"role": "system", "content": system_prompt + " Example: [{\"judgement\":\"Valid\",\"explanation\":\"OK\",\"suggested_followup\":\"None\"}]"}
    else:
        system_msg = {"role": "system", "content": system_prompt}

    user_msg = {"role": "user", "content": f"{focus}\nAnalyse these mappings:\n{rows_text}"}

    resp = llm.create_chat_completion(messages=[system_msg, user_msg], max_tokens=256)
    text = resp["choices"][0]["message"]["content"]
    parsed = _safe_json_parse(text)
    if len(parsed) < len(batch):
        parsed += [{"judgement":"Unparsed","explanation":"Truncated"}]*(len(batch)-len(parsed))
    return parsed
