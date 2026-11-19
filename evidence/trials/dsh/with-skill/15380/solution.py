import sys
from openpyxl import load_workbook

src, dst = sys.argv[1], sys.argv[2]
wb = load_workbook(src)
ws = wb["Sheet3"]
for row in range(3, 15):
    ws[f"B{row}"] = f'=IFERROR(INDEX(month,MATCH(MID(A{row},FIND("_",A{row})+1,2),codes2,0)),"")'
wb.save(dst)
