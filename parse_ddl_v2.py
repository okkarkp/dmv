import re
from pathlib import Path
from typing import Dict

def parse_ddl_v2(path: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Enterprise-grade SQL Server DDL parser.

    Returns:
      tables[TABLE][COLUMN] = {
          "type": "...",
          "nullable": "NULL|NOT NULL|"
      }

    Excludes:
      - IDENTITY columns
      - ROWVERSION / TIMESTAMP
      - GENERATED ALWAYS
      - Computed columns (AS ...)
      - Constraints / PK / FK / INDEX blocks
    """

    raw = Path(path).read_bytes()
    ddl = raw.decode("utf-8", errors="ignore")

    tables: Dict[str, Dict[str, Dict[str, str]]] = {}

    create_table_re = re.compile(
        r"CREATE\s+TABLE\s+(?:\[(\w+)\]\.)?\[(\w+)\]\s*\(",
        re.IGNORECASE
    )

    col_re = re.compile(
        r"""
        ^\s*
        \[(?P<col>\w+)\]                      # column name
        \s+
        (?P<type>[A-Z0-9_]+(?:\s*\([^)]*\))?) # datatype
        (?P<rest>.*)                          # rest
        $
        """,
        re.IGNORECASE | re.VERBOSE
    )

    for m in create_table_re.finditer(ddl):
        table = m.group(2).upper()
        start = m.end()

        depth = 1
        i = start
        while i < len(ddl) and depth > 0:
            if ddl[i] == "(":
                depth += 1
            elif ddl[i] == ")":
                depth -= 1
            i += 1

        block = ddl[start:i - 1]
        cols = {}

        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            up = line.upper()

            # Skip non-column definitions
            if up.startswith((
                "CONSTRAINT",
                "PRIMARY KEY",
                "FOREIGN KEY",
                "CHECK",
                "UNIQUE",
                "INDEX",
                "PERIOD FOR SYSTEM_TIME",
                "WITH"
            )):
                continue

            m2 = col_re.match(line)
            if not m2:
                continue

            col = m2.group("col").upper()
            dtype = m2.group("type").upper()
            rest = m2.group("rest").upper()

            # ❌ Exclude computed & system-generated columns
            if (
                " AS " in up or
                "IDENTITY" in rest or
                "GENERATED ALWAYS" in rest or
                dtype in ("ROWVERSION", "TIMESTAMP")
            ):
                continue

            nullable = ""
            if "NOT NULL" in rest:
                nullable = "NOT NULL"
            elif re.search(r"\bNULL\b", rest):
                nullable = "NULL"

            cols[col] = {
                "type": dtype,
                "nullable": nullable
            }

        tables[table] = cols

    return tables
