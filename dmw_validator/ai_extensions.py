import os, json, time
from dmw_validator.ai_core import _run_batch
from dmw_validator.ai_precheck import quick_syntax_check

def run_ai_extensions(issues, out_dir="outputs/ai", model="light", prompt_profile="business"):
    """
    Enhanced AI logic validation with syntax pre-checks.
    """
    os.makedirs(out_dir, exist_ok=True)
    results = []
    start_time = time.time()

    print(f"⚙️ AI validation (improved pre-check) started… total {len(issues)} rows")

    for idx, rec in enumerate(issues, start=1):
        data = rec.get("data", {})
        logic = data.get("Transformation Logic") or data.get("transformation logic") or ""

        # 🔍 Precheck before AI
        status, msg = quick_syntax_check(logic)
        if status in ["ERROR", "EMPTY", "WARN"]:
            results.append({
                "Target Table": rec.get("table", ""),
                "Target Field": rec.get("field", ""),
                "Logic": logic,
                "AI_Judgement": status,
                "AI_Explanation": msg,
                "AI_Suggested_Followup": "Fix syntax or verify manually before revalidation."
            })
            continue

        # 🧠 Pass to AI only if logic looks valid
        parsed = _run_batch([rec], offset=idx-1, focus="Check logic", model=model, prompt_profile=prompt_profile)
        ai_result = parsed[0] if parsed else {}

        results.append({
            "Target Table": rec.get("table", ""),
            "Target Field": rec.get("field", ""),
            "Logic": logic,
            "AI_Judgement": ai_result.get("judgement", "Unparsed"),
            "AI_Explanation": ai_result.get("explanation", "No explicit output from model"),
            "AI_Suggested_Followup": ai_result.get("suggested_followup", "")
        })

    # 📝 Write results
    out_file = os.path.join(out_dir, "logic_quality.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ AI validation complete → {out_dir} ({len(results)} rows, {round(time.time() - start_time, 2)}s)")
