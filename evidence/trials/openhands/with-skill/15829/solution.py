import sys
from openpyxl import load_workbook


def main(src, dst):
    wb = load_workbook(src)
    ws = wb.active

    first = 2
    last = first
    while ws.cell(row=last + 1, column=6).value not in (None, ""):
        last += 1

    tariff = f"$F${first}:$F${last}"
    lo = f"$G${first}:$G${last}"
    hi = f"$H${first}:$H${last}"
    fee = f"$I${first}:$I${last}"

    ws["B3"] = (
        f'=SUMIFS({fee},{tariff},$B$2,'
        f'{lo},"<="&$B$1,{hi},">="&$B$1)'
    )
    wb.save(dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
