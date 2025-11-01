import os, csv, json, re, argparse
from retriever_faiss import query_top_k
from llm_runner import run_llm

# Parse CLI args
parser = argparse.ArgumentParser()
parser.add_argument("--model", choices=["tiny", "light"], default=None,
                    help="Choose which model to use: tiny (TinyLlama) or light (Llama-3.2-3B)")
args = parser.parse_args()

# -- Helper to get headers from CSV file --
def get_headers(csv_path):
    with open(csv_path, newline='') as f:
        reader = csv.reader(f)
        return next(reader)

# -- Inputs --
source_fields = get_headers("uploads/source.csv")
target_fields = get_headers("uploads/target.csv")
output_folder = "outputs/job1"

# -- Prompt with grounding --
schema_diff = f"source: {', '.join(source_fields)}\ntarget: {', '.join(target_fields)}"
context_rules = query_top_k("field mapping and dq checks", k=5)

prompt = f"""You are a data transformation planner.

Strictly respond ONLY in valid JSON with the following keys:
- "mappings"
- "transform_sql"
- "dq_checks_sql"
- "recon_sql"

Do NOT include markdown, explanation, comments, or code blocks.

## Rules:
{chr(10).join(f'- {r}' for r in context_rules)}

## Schema Diff:
{schema_diff}
"""

# -- Run LLM --
llm_output = run_llm(prompt)

# -- Save raw output --
os.makedirs(f"{output_folder}/logs", exist_ok=True)
with open(f"{output_folder}/logs/raw_output.txt", "w") as f:
    f.write(llm_output)

# -- Save logs with prompt --
with open(f"{output_folder}/logs/notes.md", "w") as f:
    f.write(f"# Prompt\n\n{prompt}\n\n---\n\n# Output\n\n{llm_output}")

# -- Robust JSON parser --
def try_extract_json(text):
    try:
        return json.loads(text)
    except:
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
    return {}

output_json = try_extract_json(llm_output)

# Handle mapping vs mappings
if "mappings" not in output_json and "mapping" in output_json:
    output_json["mappings"] = output_json.pop("mapping")

# Fallback defaults
output_json.setdefault("mappings", {})
output_json.setdefault("transform_sql", "-- transform_sql missing or not parsed")
output_json.setdefault("dq_checks_sql", "-- dq_checks_sql missing or not parsed")
output_json.setdefault("recon_sql", "-- recon_sql missing or not parsed")

# -- Save outputs --
os.makedirs(f"{output_folder}/01_plan", exist_ok=True)
os.makedirs(f"{output_folder}/02_sql", exist_ok=True)
os.makedirs(f"{output_folder}/03_dq", exist_ok=True)
os.makedirs(f"{output_folder}/04_recon", exist_ok=True)

with open(f"{output_folder}/01_plan/mappings.json", "w") as f:
    json.dump(output_json["mappings"], f, indent=2)

with open(f"{output_folder}/02_sql/transform.sql", "w") as f:
    f.write(output_json["transform_sql"])

with open(f"{output_folder}/03_dq/dq_checks.sql", "w") as f:
    f.write(output_json["dq_checks_sql"])

with open(f"{output_folder}/04_recon/recon.sql", "w") as f:
    f.write(output_json["recon_sql"])

print(f"\n✅ Worker complete. Output saved to: {output_folder}")

# --- AI logic evaluation + SQL generation on flagged mismatches ---
try:
    from ai_extensions import evaluate_flagged_issues
    issue_file = "outputs/logs/mismatched_fields.json"
    evaluate_flagged_issues(issue_file, out_dir=f"{output_folder}/ai")
except Exception as e:
    print(f"⚠️ AI flagged-issue evaluation skipped: {e}")
