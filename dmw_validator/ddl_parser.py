import os, re, json

def parse_ddl(ddl_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    with open(ddl_path, encoding="utf-8") as f:
        content = f.read()

    # Match: ALTER TABLE [dbo].[TableName] ... FOR [FieldName];
    pattern = re.findall(
        r"ALTER TABLE\s+\[dbo\]\.\[(.*?)\][\s\S]*?FOR\s+\[(.*?)\];",
        content,
        re.IGNORECASE
    )

    schema = {}
    for table, field in pattern:
        schema.setdefault(table, []).append(field)

    for table in schema:
        schema[table] = sorted(set(schema[table]))

    out_file = f"{out_dir}/ddl_fields.json"
    with open(out_file, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"✅ Extracted {len(schema)} tables from DDL → {out_file}")
    return schema
