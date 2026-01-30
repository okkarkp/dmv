from pathlib import Path

def test_download_file(client, tmp_path):
    job_id = "jobtest"
    out_dir = Path("web/outputs") / f"job_{job_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    f = out_dir / "test.txt"
    f.write_text("hello")

    resp = client.get(f"/download/{job_id}/test.txt")
    assert resp.status_code == 200
    assert resp.content == b"hello"
