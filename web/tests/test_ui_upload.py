from unittest.mock import patch, MagicMock

def test_upload_triggers_validation(client, sample_xlsx, sample_sql):
    fake_result = MagicMock()
    fake_result.stdout = "[OK] Validation completed"
    fake_result.stderr = ""

    with patch("web.app.subprocess.run", return_value=fake_result) as mock_run:
        resp = client.post(
            "/upload",
            files={
                "dmw_xlsx": ("dmw.xlsx", sample_xlsx.read_bytes()),
                "ddl_sql": ("ddl.sql", sample_sql.read_bytes()),
            },
        )

        assert resp.status_code == 200
        assert "[OK] Validation completed" in resp.text
        assert "Baseline_Data_Model_output.xlsx" in resp.text

        # Validate subprocess invocation
        args = mock_run.call_args[0][0]
        assert "validate_dmw_final.py" in " ".join(args)
        assert "--dmw-xlsx" in args
        assert "--ddl-sql" in args
        assert "--out" in args
