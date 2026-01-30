from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import subprocess
import uuid

# --------------------------------------------------
# Paths
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

for d in [UPLOAD_DIR, OUTPUT_DIR, TEMPLATES_DIR, STATIC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI(title="DMW Validation Portal")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --------------------------------------------------
# Home
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

# --------------------------------------------------
# Upload & Validate
# --------------------------------------------------
@app.post("/upload", response_class=HTMLResponse)
async def upload(
    request: Request,
    dmw_xlsx: UploadFile,
    ddl_sql: UploadFile,
    prev_dmw: UploadFile | None = None,
    prev_ddl: UploadFile | None = None,
    ref_dmw: UploadFile | None = None,
    master_dmw: UploadFile | None = None,
):
    job_id = uuid.uuid4().hex[:8]
    job_dir = OUTPUT_DIR / f"job_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)

    def save(file: UploadFile | None):
        if not file:
            return None
        if not file.filename or not file.filename.strip():
            return None

        dest = job_dir / file.filename
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        return dest

    dmw_path = save(dmw_xlsx)
    ddl_path = save(ddl_sql)
    prev_dmw_path = save(prev_dmw)
    prev_ddl_path = save(prev_ddl)
    ref_dmw_path = save(ref_dmw)
    master_dmw_path = save(master_dmw)

    out_xlsx = job_dir / "Baseline_Data_Model_output.xlsx"

    cmd = [
        "python3",
        str(BASE_DIR / "validate_dmw_final.py"),
        "--dmw-xlsx", str(dmw_path),
        "--ddl-sql", str(ddl_path),
        "--out", str(out_xlsx),
    ]

    if prev_dmw_path:
        cmd += ["--prev-dmw", str(prev_dmw_path)]
    if prev_ddl_path:
        cmd += ["--prev-ddl", str(prev_ddl_path)]
    if ref_dmw_path:
        cmd += ["--ref-dmw", str(ref_dmw_path)]
    if master_dmw_path:
        cmd += ["--master-dmw", str(master_dmw_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)

    files = sorted([f.name for f in job_dir.iterdir() if f.is_file()])

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "job_id": job_id,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "files": files,
        }
    )

# --------------------------------------------------
# Download
# --------------------------------------------------
@app.get("/download/{job_id}/{filename}")
async def download(job_id: str, filename: str):
    path = OUTPUT_DIR / f"job_{job_id}" / filename
    if not path.exists():
        return {"error": "File not found"}
    return FileResponse(path=path, filename=filename)
