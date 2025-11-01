from pathlib import Path
import re

path = Path("/opt/oss-migrate/llm-planner/web/app.py")
text = path.read_text(encoding="utf-8")

# Replace the frozen_xlsx block with safe check
pattern = r"if frozen_xlsx:\n\s+with frozen_path\.open"
replacement = """if frozen_xlsx and getattr(frozen_xlsx, 'filename', None):
        if frozen_xlsx.filename.strip():
            frozen_path = job_dir / frozen_xlsx.filename
            with frozen_path.open("wb") as f:
                shutil.copyfileobj(frozen_xlsx.file, f)
        else:
            frozen_path = None
    else:
        frozen_path = None
    """
text = re.sub(pattern, replacement, text)

path.write_text(text, encoding="utf-8")
print("✅ Patch applied: frozen_xlsx file now safely optional.")
