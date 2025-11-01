def main():
    import argparse, traceback, json
    from pathlib import Path

    ap = argparse.ArgumentParser()
    ap.add_argument("--dmw-xlsx", required=True)
    ap.add_argument("--ddl-sql", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-rows", type=int, default=10000)
    ap.add_argument("--frozen-xlsx", default=None)

    # 🔧 AI flags (all optional)
    ap.add_argument("--enable-ai", action="store_true",
                    help="Enable AI reasoning for failed rules")
    ap.add_argument("--ai-host", default="127.0.0.1", help="LLM server host")
    ap.add_argument("--ai-port", type=int, default=8080, help="LLM server port")
    ap.add_argument("--ai-model", default="TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf",
                    help="Model name to send in payload")

    args = ap.parse_args()

    # Compose AI config
    ai_cfg = {
        "enabled": args.enable_ai,
        "host": args.ai_host,
        "port": args.ai_port,
        "model": args.ai_model,
    }

    if ai_cfg["enabled"]:
        print(f"[AI] Enabled → {ai_cfg['host']}:{ai_cfg['port']} model={ai_cfg['model']}")
    else:
        print("[AI] Disabled")

    try:
        validate(
            Path(args.dmw_xlsx),
            Path(args.ddl_sql),
            Path(args.out),
            Path(args.frozen_xlsx) if args.frozen_xlsx else None,
            ai_cfg,
            args.max_rows,
        )
    except Exception:
        print("[FATAL] Exception during validation:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
