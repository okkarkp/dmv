import pandas as pd, os, json

data = [
  {
    "Target Table Name": "RefAccountTaxes",
    "Target Field Name": "TaxCode1",
    "Source Table Name": "SrcTaxMaster",
    "Source Field Name": "TaxCd1",
    "Transformation Logic": "UPPER(TRIM(SrcTaxMaster.TaxCd))",
    "Business Rule": "Tax must be active before 2025-01-01",
    "Comments": "Reviewed with BA"
  },
  {
    "Target Table Name": "RefAccountTaxes",
    "Target Field Name": "TaxCode2",
    "Source Table Name": "SrcTaxMaster",
    "Source Field Name": "TaxCd2",
    "Transformation Logic": "UPPER(TRIM(SrcTaxMaster.TaxCd))",
    "Business Rule": "Tax must be active before 2025-01-01",
    "Comments": "Reviewed with BA"
  },
  {
    "Target Table Name": "RefAccountTaxes",
    "Target Field Name": "TaxCode3",
    "Source Table Name": "SrcTaxMaster",
    "Source Field Name": "TaxCd3",
    "Transformation Logic": "UPPER(TRIM(SrcTaxMaster.TaxCd))",
    "Business Rule": "Tax must be active before 2025-01-01",
    "Comments": "Reviewed with BA"
  }
]

os.makedirs("uploads", exist_ok=True)
df = pd.DataFrame(data)
df.to_excel("uploads/DMW_Enriched.xlsx", index=False)
print("✅ Sample DMW_Enriched.xlsx generated with", len(df), "rows.")
