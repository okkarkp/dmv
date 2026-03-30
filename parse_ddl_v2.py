import re
from pathlib import Path
from typing import Dict

def sniff_encoding(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16-be"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"

def strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"--[^\n]*", "", sql)
    return sql

def split_top_level_commas(block: str):
    parts, buf, depth = [], [], 0
    for ch in block:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts

def parse_ddl_v2(path: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Returns:
      tables[TABLE_UPPER][COL_UPPER] = {"type": "...", "nullable": "NULL|NOT NULL|"}
    """
    raw = Path(path).read_bytes()
    enc = sniff_encoding(raw)
    ddl = raw.decode(enc, errors="ignore")
    ddl = strip_sql_comments(ddl)

    tables: Dict[str, Dict[str, Dict[str, str]]] = {}

    create_table_re = re.compile(
        r"CREATE\s+TABLE\s+(?:\[(?P<schema>\w+)\]\.)?\[(?P<table>\w+)\]\s*\(",
        re.IGNORECASE
    )

    # Column definition:
    # [Col] [nvarchar](100) ... OR [Col] nvarchar(100) ...
    col_re = re.compile(
        r"^\s*\[(?P<col>[^\]]+)\]\s+"
        r"(?:(?:\[(?P<type1>[A-Za-z0-9_]+)\])|(?P<type2>[A-Za-z0-9_]+))"
        r"\s*(?P<params>\([^\)]*\))?"
        r"(?P<rest>.*)$",
        re.IGNORECASE
    )

    for m in create_table_re.finditer(ddl):
        table = (m.group("table") or "").upper()

        # find matching closing paren of CREATE TABLE ( ... )
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

        cols: Dict[str, Dict[str, str]] = tables.get(table, {})

        for item in split_top_level_commas(block):
            line = item.strip()
            if not line:
                continue

            up = line.upper()

            # Skip constraint / index / period blocks
            if up.startswith((
                "CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY", "CHECK",
                "UNIQUE", "INDEX", "PERIOD FOR SYSTEM_TIME", "WITH"
            )):
                continue

            # Skip PK ordering lines like: [Id] ASC
            if re.match(r"^\s*\[[^\]]+\]\s+(ASC|DESC)\b", line, re.IGNORECASE):
                continue

            # Skip computed columns
            if re.search(r"\bAS\s*\(", up):
                continue

            m2 = col_re.match(line)
            if not m2:
                continue

            col = (m2.group("col") or "").strip().upper()

            # Defensive: don't overwrite a real definition
            if col in cols:
                continue

            base = (m2.group("type1") or m2.group("type2") or "").strip().upper()
            params = (m2.group("params") or "").replace(" ", "")
            rest = (m2.group("rest") or "")

            rest_up = rest.upper()
            # Remove COLLATE and IDENTITY(...) noise
            rest_up = re.sub(r"\bCOLLATE\b\s+\S+", "", rest_up)
            rest_up = re.sub(r"\bIDENTITY\s*\([^\)]*\)", "", rest_up)

            dtype = f"{base}{params}"

            # Exclude only rowversion/timestamp (optional)
            if dtype in ("ROWVERSION", "TIMESTAMP"):
                continue

            nullable = ""
            if "NOT NULL" in rest_up:
                nullable = "NOT NULL"
            elif re.search(r"\bNULL\b", rest_up):
                nullable = "NULL"

            cols[col] = {"type": dtype, "nullable": nullable}

        tables[table] = cols

    return tables
