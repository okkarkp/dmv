def detect_header_row(ws):
    """
    Header row is the first row containing
    'DESTINATION TABLE' or 'SOURCE TABLE'
    """
    for r in range(1, 30):
        rows = list(ws.iter_rows(min_row=r, max_row=r, values_only=True))
        if not rows:
            continue
        row = [str(c).upper() if c else "" for c in rows[0]]
        if "DESTINATION TABLE" in row or "SOURCE TABLE" in row:
            return r
    raise RuntimeError("Header row not found")
