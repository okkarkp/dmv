import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from web.app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_xlsx(tmp_path):
    p = tmp_path / "sample.xlsx"
    p.write_bytes(b"fake excel content")
    return p

@pytest.fixture
def sample_sql(tmp_path):
    p = tmp_path / "schema.sql"
    p.write_text("CREATE TABLE T1 (C1 INT);")
    return p
