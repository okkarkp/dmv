#!/usr/bin/env bash
set -euo pipefail
cd /opt/oss-migrate/llm-planner
python3 -m pip show openpyxl >/dev/null 2>&1 || python3 -m pip install openpyxl
python3 /opt/oss-migrate/llm-planner/tests_auto/run_all.py
