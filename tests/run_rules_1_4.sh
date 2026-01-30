#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Create test DMWs
python3 tests/data/create_rule1_dmw.py
python3 tests/data/create_rule2_dmw.py
python3 tests/data/create_rule3_dmw.py
python3 tests/data/create_rule4_dmw.py

# Run validator for each rule dataset to the exact output the tests read
python3 validate_dmw_final.py \
  --dmw-xlsx tests/data/rule1_dmw.xlsx \
  --out tests/data/rule1_out.xlsx

python3 validate_dmw_final.py \
  --dmw-xlsx tests/data/rule2_dmw.xlsx \
  --out tests/data/rule2_out.xlsx

python3 validate_dmw_final.py \
  --dmw-xlsx tests/data/rule3_dmw.xlsx \
  --out tests/data/rule3_out.xlsx

python3 validate_dmw_final.py \
  --dmw-xlsx tests/data/rule4_dmw.xlsx \
  --ddl-sql tests/data/rule4_ddl.sql \
  --out tests/data/rule4_out.xlsx

# Run assertions (unchanged tests)
python3 tests/test_rule1_local.py
python3 tests/test_rule2_local.py
python3 tests/test_rule3_local.py
python3 tests/test_rule4_local.py

echo "[OK] Rules 1–4 locked."
