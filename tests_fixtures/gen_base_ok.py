from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "Baseline Data Model"

headers = [
    "Source Table","Source Column Name",
    "Destination Table","Destination Column Name",
    "Migrating Column","Reason for Not Migrating",
    "Destination Data Type","Destination Data Length",
    "Destination Nullable","Transformation Logic",
    "Introduced Sprint","Last Updated Sprint","Change Log"
]
ws.append(headers)

ws.append([
    "SRC","A","T1","C1",
    "Yes","",
    "INT","",
    "NOT NULL","copy",
    "S1","S1",""
])

wb.save("tests_fixtures/dmw/base_ok.xlsx")
