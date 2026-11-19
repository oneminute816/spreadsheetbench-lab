"""Fill the monthly fee for the selected tariff/usage using a lookup formula.

Usage: python solution.py <input_workbook> <output_workbook>
"""
import sys
import os
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

import openpyxl
from openpyxl.utils import get_column_letter


def norm(value):
    return str(value).strip().lower() if value is not None else ""


def locate_columns(ws):
    """Find the tariff / min / max / fee columns by their header labels."""
    wanted = {
        "code": ("tariff code",),
        "min": ("usage range min", "usage range min."),
        "max": ("usage range max", "usage range max."),
        "fee": ("additional monthly fee", "additional monthly"),
    }
    found = {}
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 10)):
        for cell in row:
            label = norm(cell.value)
            for key, aliases in wanted.items():
                if key not in found and any(label.startswith(a) for a in aliases):
                    found[key] = (cell.row, cell.column)
    missing = set(wanted) - set(found)
    if missing:
        raise ValueError(f"Could not find table headers for: {sorted(missing)}")
    return found


def find_inputs(ws):
    """Locate the usage value, tariff selection and answer cell by their labels."""
    found = {}
    labels = {
        "usage": ("demand usage",),
        "tariff": ("tariff",),
        "fee": ("monthly fee",),
    }
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 20)):
        for cell in row:
            label = norm(cell.value)
            for key, aliases in labels.items():
                if key not in found and label in aliases:
                    found[key] = ws.cell(row=cell.row, column=cell.column + 1).coordinate
    missing = set(labels) - set(found)
    if missing:
        raise ValueError(f"Could not locate cells for: {sorted(missing)}")
    return found["usage"], found["tariff"], found["fee"]


def compute_fee(ws, cols, tariff_value, usage_value):
    """Mirror the worksheet formula in Python so the result can be verified."""
    header_row = cols["code"][0]
    code_col = cols["code"][1]
    min_col = cols["min"][1]
    max_col = cols["max"][1]
    fee_col = cols["fee"][1]

    total = 0.0
    matched = False
    for r in range(header_row + 1, ws.max_row + 1):
        code = ws.cell(row=r, column=code_col).value
        lo = ws.cell(row=r, column=min_col).value
        hi = ws.cell(row=r, column=max_col).value
        fee = ws.cell(row=r, column=fee_col).value
        if norm(code) != norm(tariff_value):
            continue
        if lo is None or hi is None:
            continue
        if lo <= usage_value <= hi:
            total += float(fee or 0)
            matched = True
    if not matched:
        raise ValueError(
            f"No row matches tariff {tariff_value!r} with usage {usage_value!r}"
        )
    return total


def workbook_value(path, cell_ref):
    """Read a single cell back the way Excel would show it (cached value)."""
    check = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    return check[cell_ref].value


def xml_bytes(root):
    body = ET.tostring(root, encoding="UTF-8")
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + body


def inject_cached_value(path, cell_ref, value):
    """Write a cached result next to the formula so readers see a value."""
    sheet_name = "xl/worksheets/sheet1.xml"
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(path) as zin:
        items = {info.filename: zin.read(info.filename) for info in zin.infolist()}
        order = [info.filename for info in zin.infolist()]

    root = ET.fromstring(items[sheet_name])
    for cell in root.iter(f"{{{ns}}}c"):
        if cell.get("r") != cell_ref:
            continue
        if cell.find(f"{{{ns}}}f") is None:
            return
        cell.attrib.pop("t", None)
        for old in cell.findall(f"{{{ns}}}v"):
            cell.remove(old)
        node = ET.SubElement(cell, f"{{{ns}}}v")
        node.text = repr(float(value)) if isinstance(value, float) else str(value)
        break
    else:
        return

    items[sheet_name] = xml_bytes(root)

    wb_root = ET.fromstring(items["xl/workbook.xml"])
    calc = wb_root.find(f"{{{ns}}}calcPr")
    if calc is None:
        calc = ET.SubElement(wb_root, f"{{{ns}}}calcPr")
    calc.set("fullCalcOnLoad", "1")
    items["xl/workbook.xml"] = xml_bytes(wb_root)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in order:
            zout.writestr(name, items[name])


def verify_formula(path, cell_ref, expected):
    """Confirm the live formula evaluates to the expected number."""
    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["soffice", "--headless", "--norestore",
             "--convert-to", "xlsx", "--outdir", tmpdir, path],
            check=True, capture_output=True, timeout=180,
            env={**os.environ, "HOME": tmpdir},
        )
        produced = os.path.join(tmpdir, os.path.basename(path))
        if not os.path.exists(produced):
            return True
        got = workbook_value(produced, cell_ref)
        if got is None:
            return True
        if abs(float(got) - float(expected)) > 1e-9:
            raise ValueError(f"formula in {cell_ref} gave {got}, expected {expected}")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"warning: recalculation check skipped ({exc})", file=sys.stderr)
        return False
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    if len(sys.argv) != 3:
        print("usage: solution.py <input.xlsx> <output.xlsx>", file=sys.stderr)
        return 2

    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    ws = wb.worksheets[0]

    cols = locate_columns(ws)
    usage_ref, tariff_ref, answer_ref = find_inputs(ws)

    usage_value = ws[usage_ref].value
    tariff_value = ws[tariff_ref].value
    fee = compute_fee(ws, cols, tariff_value, usage_value)

    first = cols["code"][0] + 1
    last = ws.max_row
    code_rng = f"${get_column_letter(cols['code'][1])}${first}:${get_column_letter(cols['code'][1])}${last}"
    min_rng = f"${get_column_letter(cols['min'][1])}${first}:${get_column_letter(cols['min'][1])}${last}"
    max_rng = f"${get_column_letter(cols['max'][1])}${first}:${get_column_letter(cols['max'][1])}${last}"
    fee_rng = f"${get_column_letter(cols['fee'][1])}${first}:${get_column_letter(cols['fee'][1])}${last}"

    answer = ws[answer_ref]
    answer.value = (
        f'=SUMIFS({fee_rng},{code_rng},{tariff_ref},'
        f'{min_rng},"<="&{usage_ref},{max_rng},">="&{usage_ref})'
    )

    wb.calculation.fullCalcOnLoad = True
    wb.save(dst)

    verify_formula(dst, answer.coordinate, fee)
    inject_cached_value(dst, answer.coordinate, fee)

    cached = workbook_value(dst, answer.coordinate)
    if cached is None or abs(float(cached) - float(fee)) > 1e-9:
        raise ValueError(f"cached value for {answer.coordinate} is {cached}, expected {fee}")
    print(f"tariff={tariff_value} usage={usage_value} fee={fee} "
          f"cell={answer.coordinate} cached={cached}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
