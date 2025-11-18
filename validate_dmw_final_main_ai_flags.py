#!/usr/bin/env python3

def main():
    import argparse, traceback
    from pathlib import Path
    from validate_dmw_final import validate  # Ensure correct import

    ap = argparse.ArgumentParser(description="DMW Validator with AI flags wrapper")

    # Required inputs
    ap.add_argument("--dmw-xlsx", required=True, help="Path to DataMappingWorkbook")
    ap.add_argument("--ddl-sql", required=True, help="Path to DDL SQL")
    ap.add_argument("--out", required=True, help="Output Excel")

    # Optional previous versions (for diffing)
    ap.add_argument("--prev-dmw", default=None, help="Previous DMW for comparison")
    ap.add_argument("--prev-ddl", default=None, help="Previous DDL for comparison")

    # Optional AI flags
    ap.add_argument("--enable-ai", action="store_true",
                    help="Enable AI-based reasoning for failed validation rules")

    ap.add_argument("--ai-host", default="127.0.0.1",
                    help="AI server host")

    ap.add_argument("--ai-port", type=int, default=8081,
                    help="AI server port")

    ap.add_argument("--ai-model", default="local-model",
                    help="Model identifier sent to the AI server")

    args = ap.parse_args()

    # Compose AI config object for validator
    ai_cfg = {
        "enabled": args.enable_ai,
        "ai_host": args.ai_host,
        "ai_port": args.ai_port,
        "ai_model": args.ai_model
    }

    if ai_cfg["enabled"]:
        print(f"[AI] Enabled → {ai_cfg['ai_host']}:{ai_cfg['ai_port']} model={ai_cfg['ai_model']}")
    else:
        print("[AI] Disabled")

    try:
        validate(
            Path(args.dmw_xlsx),
            Path(args.ddl_sql),
            Path(args.out),
            ai_cfg,
            Path(args.prev_dmw) if args.prev_dmw else None,
            Path(args.prev_ddl) if args.prev_ddl else None
        )
    except Exception:
        print("[FATAL] Exception during validation:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
