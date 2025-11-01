from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os, shutil, subprocess
from pathlib import Path
import uuid

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="DMW Validation Portal")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request,
                 dmw_xlsx: UploadFile,
                 ddl_sql: UploadFile,
                 frozen_xlsx: UploadFile | None = None):
    uid = uuid.uuid4().hex[:8]
    job_dir = OUTPUT_DIR / f"job_{uid}"
    job_dir.mkdir(parents=True, exist_ok=True)

    dmw_path = job_dir / dmw_xlsx.filename
    ddl_path = job_dir / ddl_sql.filename
    frozen_path = job_dir / frozen_xlsx.filename if frozen_xlsx else None

    for src, dest in [(dmw_xlsx, dmw_path), (ddl_sql, ddl_path)]:
        with dest.open("wb") as f: shutil.copyfileobj(src.file, f)
    if frozen_xlsx and getattr(frozen_xlsx, 'filename', None):
        if frozen_xlsx.filename.strip():
            frozen_path = job_dir / frozen_xlsx.filename
            with frozen_path.open("wb") as f:
                shutil.copyfileobj(frozen_xlsx.file, f)
        else:
            frozen_path = None
    else:
        frozen_path = None
    ("wb") as f: shutil.copyfileobj(frozen_xlsx.file, f)

    out_xlsx = job_dir / "Baseline_Data_Model_output.xlsx"
    cmd = [
        "python3", "/opt/oss-migrate/llm-planner/validate_dmw_vs_ddl_stream.py",
        "--dmw-xlsx", str(dmw_path),
        "--ddl-sql", str(ddl_path),
        "--out", str(out_xlsx),
        "--max-rows", "10000",
        "--config", "/opt/oss-migrate/llm-planner/config.yaml"
    ]
    if frozen_path:
        cmd += ["--frozen-xlsx", str(frozen_path)]

    print(f"[INFO] Running validation: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    files = list(job_dir.glob("*"))
    links = [f.name for f in files if f.is_file()]

    return templates.TemplateResponse("result.html", {
        "request": request,
        "job_id": uid,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "links": links
    })

@app.get("/download/{job_id}/{filename}")
async def download(job_id: str, filename: str):
    file_path = OUTPUT_DIR / f"job_{job_id}" / filename
    if file_path.exists():
        return FileResponse(path=file_path, filename=filename)
    return {"error": "File not found"}
