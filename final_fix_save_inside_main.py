from pathlib import Path
import re

path = Path("/opt/oss-migrate/llm-planner/validate_dmw_vs_ddl_stream.py")
text = path.read_text(encoding="utf-8")

# Replace any old "out_wb.save" or "print final workbook" near end of main()
text = re.sub(
    r'out_wb\.save\(.*?\)\s*print\(f?"\[INFO\].*saved.*?"\)',
    '',
    text,
    flags=re.S
)

# Append safe save code **inside main()** before it exits
insert_block = r"""
    # ---------------- SAFE SAVE HANDLER ----------------
    try:
        print(f"[INFO] Forcing workbook write to: {args.out}")
        for ws in getattr(out_wb, 'worksheets', []):
            try:
                ws.close()
            except Exception:
                pass
        out_wb.save(args.out)
        out_wb.close()
        print(f"[SUCCESS] Workbook saved successfully to {args.out}")
    except Exception as e:
        import traceback
        print("[FATAL] Failed to save workbook:")
        traceback.print_exc()
"""
# Insert right before 'if ai_enabled' block to ensure workbook exists
text = re.sub(r'(?=\nif ai_enabled and aiq:)', insert_block, text)

path.write_text(text, encoding="utf-8")
print("✅ Moved safe-save block inside main() where out_wb is defined.")
