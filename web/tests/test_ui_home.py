def test_home_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Data Mapping Workbook Validator" in resp.text
    assert "Validation Setup" in resp.text
