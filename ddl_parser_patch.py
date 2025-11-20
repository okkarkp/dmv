# --- SQL Server Compatible DDL Parser ---

import re
from pathlib import Path

def parse_ddl(path: str):
    """Parse SQL Server DDL into {TABLE: {COLUMN: DATATYPE}}"""
    raw = Path(path).read_bytes()

    # Detect encoding
    if raw.startswith(b"\xff\xfe"):
        enc="utf-16-le"
    elif raw.startswith(b"\xfe\xff"):
        enc="utf-16-be"
    elif raw.startswith(b"\xef\xbb\xbf"):
        enc="utf-8-sig"
    else:
        try:
            raw.decode("utf-8")
            enc="utf-8"
        except:
            enc="latin-1"

    ddl = raw.decode(enc, errors="ignore")

    tables = {}
    current_table = None

    # Regex patterns for SQL Server
    create_table_pattern = re.compile(
        r"CREATE\s+TABLE\s+\[?(?P<schema>[A-Za-z0-9_]+)\]?\.\[?(?P<table>[A-Za-z0-9_]+)\]?|"
        r"CREATE\s+TABLE\s+\[?(?P<table2>[A-Za-z0-9_]+)\]?",
        re.IGNORECASE
    )

    column_pattern = re.compile(
        r"^\s*\[?(?P<col>[A-Za-z0-9_]+)\]?\s+"
        r"(?P<type>[A-Za-z0-9_\(\),\s]+?)(?:,)?\s*$"
    )

    for line in ddl.splitlines():
        line = line.strip()

        # Skip irrelevant lines
        if not line or line.upper().startswith("DROP ") or line.upper().startswith("GO"):
            continue

        # Detect CREATE TABLE
        m = create_table_pattern.search(line)
        if m:
            table = (
                m.group("table") or
                m.group("table2")
            )
            if table:
                table = table.upper()
                tables[table] = {}
                current_table = table
            continue

        # Parse column definitions only inside CREATE TABLE block
        if current_table:
            m2 = column_pattern.match(line)
            if m2:
                col = m2.group("col").upper()
                datatype = m2.group("type").upper().rstrip(",")
                tables[current_table][col] = datatype
                continue

            # Handle end of column list: ')'
            if line.startswith(")"):
                current_table = None

    return tables
