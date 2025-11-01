import argparse, os, json, inspect
from dmw_validator.extractor import extract_dmw_rows
from dmw_validator.validator import validate_dmw_vs_ddl
from dmw_validator.ai_extensions import run_ai_extensions

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dmw", required=True, help="Path to Data Mapping Workbook (XLSX)")
    parser.add_argument("--ddl", required=True, help="Path to DDL SQL file")
    parser.add_argument("--baseline", help="Optional baseline DMW for comparison")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--model", choices=["tiny","light"], default="light", help="Model to use for AI mode")
    parser.add_argument("--mode", choices=["rules","ai"], default="rules", help="Run mode: rules or ai")
    parser.add_argument("--prompt-profile", choices=["business","technical","strict"], default="business", help="AI response style")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # === Step 1: Extract workbook rows ===
    valid_file, missing_file, nested_file = extract_dmw_rows(args.dmw, args.out)

    # === Step 2: Validate against DDL (auto-handle variable signatures)
    sig = inspect.signature(validate_dmw_vs_ddl)
    param_count = len(sig.parameters)

    if param_count == 3:
        ddl_file = validate_dmw_vs_ddl(valid_file, args.ddl, args.out)
    elif param_count == 4:
        ddl_file = validate_dmw_vs_ddl(valid_file, args.ddl, args.out, args.mode)
    elif param_count == 5:
        ddl_file = validate_dmw_vs_ddl(valid_file, args.ddl, args.out, args.mode, None)
    else:
        raise RuntimeError(f"Unexpected validate_dmw_vs_ddl signature: {param_count} parameters")

    # === Step 3: Run AI or Rules mode ===
    if args.mode == "ai":
        mismatched_path = os.path.join(args.out, "mismatched_fields_ai.json")
        if os.path.exists(mismatched_path):
            issues = json.load(open(mismatched_path))
            run_ai_extensions(
                issues,
                out_dir=os.path.join(args.out, "ai"),
                model=args.model,
                prompt_profile=args.prompt_profile
            )
        else:
            print("ℹ️ No mismatched_fields_ai.json found — skipping AI stage.")
    else:
        print("✅ Rule-based validation complete.")

if __name__ == "__main__":
    main()
