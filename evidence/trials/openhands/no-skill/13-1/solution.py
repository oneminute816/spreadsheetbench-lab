"""Summarise the 'RANGES' sheet of a workbook into the 'LISTS' sheet.

Each titled block on RANGES (title in column C, header row below it) is
aggregated by the (DATE, REF) pair found in columns B and C, amounts
(column E) are summed, and the result is written under the matching
section of the LISTS sheet, followed by a TOTAL row using a SUM formula.
"""
import copy
import datetime
import sys

from openpyxl import load_workbook

HEADER_LABELS = {"S.N", "SN"}


def norm_date(value):
    """Normalise a date value so text and real dates compare equally."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def norm_key(date_value, ref_value):
    day = norm_date(date_value)
    ref = str(ref_value).strip().upper()
    if day is None:
        return ("text", str(date_value).strip().upper(), ref)
    return ("date", day, ref)


def is_header_row(ws, row):
    a = ws.cell(row, 1).value
    b = ws.cell(row, 2).value
    return (
        isinstance(a, str)
        and a.strip().upper() in HEADER_LABELS
        and isinstance(b, str)
        and b.strip().upper() == "DATE"
    )


def is_title_row(ws, row):
    cell = ws.cell(row, 3)
    if not isinstance(cell.value, str) or not cell.value.strip():
        return False
    others = [ws.cell(row, c).value for c in (1, 2, 4, 5)]
    return all(v is None or str(v).strip() == "" for v in others)


def block_title(ws, header_row):
    """Title sits in column C, just above the block header row."""
    row = header_row - 1
    while row >= 1:
        if is_title_row(ws, row):
            return ws.cell(row, 3).value.strip()
        if ws.cell(row, 3).value is not None:
            return None
        row -= 1
    return None


def parse_ranges(ws):
    """Return {title: [(date, ref, amount), ...]} preserving row order."""
    tables = {}
    row = 1
    while row <= ws.max_row:
        if is_header_row(ws, row):
            title = block_title(ws, row)
            rows = []
            nxt = row + 1
            while nxt <= ws.max_row:
                date_value = ws.cell(nxt, 2).value
                ref_value = ws.cell(nxt, 4).value
                if date_value is None or str(date_value).strip() == "":
                    break
                if ref_value is None or str(ref_value).strip() == "":
                    break
                rows.append((date_value, ref_value, ws.cell(nxt, 5).value))
                nxt += 1
            if title:
                tables[title] = rows
            row = nxt
        else:
            row += 1
    return tables


def aggregate(rows):
    """Group by (DATE, REF), summing AMOUNTS, keeping first-seen order."""
    groups = []
    index = {}
    for date_value, ref_value, amount in rows:
        key = norm_key(date_value, ref_value)
        if key not in index:
            index[key] = len(groups)
            groups.append([date_value, ref_value, 0])
        if isinstance(amount, (int, float)):
            groups[index[key]][2] += amount
    for group in groups:
        total = group[2]
        if isinstance(total, float) and total.is_integer():
            group[2] = int(total)
    return groups


def find_sections(ws):
    """Locate titled sections: title row, header row, total row."""
    titles = [
        (row, ws.cell(row, 3).value.strip())
        for row in range(1, ws.max_row + 1)
        if is_title_row(ws, row)
    ]

    sections = []
    for pos, (title_row, title) in enumerate(titles):
        header_row = title_row + 1
        if not is_header_row(ws, header_row) and not (
            isinstance(ws.cell(header_row, 1).value, str)
            and ws.cell(header_row, 1).value.strip().upper() in HEADER_LABELS
        ):
            continue
        limit = titles[pos + 1][0] if pos + 1 < len(titles) else ws.max_row + 1
        total_row = None
        row = header_row + 1
        while row < limit:
            value = ws.cell(row, 1).value
            if isinstance(value, str) and value.strip().upper() == "TOTAL":
                total_row = row
                break
            row += 1
        sections.append(
            {"title": title, "title_row": title_row,
             "header_row": header_row, "total_row": total_row}
        )
    return sections


def grab_style(cell):
    return {
        "font": copy.copy(cell.font),
        "fill": copy.copy(cell.fill),
        "border": copy.copy(cell.border),
        "alignment": copy.copy(cell.alignment),
        "number_format": cell.number_format,
        "protection": copy.copy(cell.protection),
    }


def apply_style(cell, style):
    cell.font = copy.copy(style["font"])
    cell.fill = copy.copy(style["fill"])
    cell.border = copy.copy(style["border"])
    cell.alignment = copy.copy(style["alignment"])
    cell.number_format = style["number_format"]
    cell.protection = copy.copy(style["protection"])


def write_section(ws, section, groups):
    header_row = section["header_row"]
    total_row = section["total_row"]
    if total_row is None:
        total_row = header_row + 1

    data_style = {c: grab_style(ws.cell(header_row + 1, c)) for c in range(1, 5)}
    total_style = {c: grab_style(ws.cell(total_row, c)) for c in range(1, 5)}

    current = total_row - header_row - 1
    needed = len(groups)

    # Remove the previously generated range(s) before writing the new data.
    if needed < current:
        ws.delete_rows(header_row + 1 + needed, current - needed)
    elif needed > current:
        ws.insert_rows(total_row, needed - current)

    total_row = header_row + 1 + needed

    for offset, (date_value, ref_value, amount) in enumerate(groups):
        row = header_row + 1 + offset
        for col in range(1, 5):
            apply_style(ws.cell(row, col), data_style[col])
        ws.cell(row, 1).value = offset + 1
        ws.cell(row, 2).value = date_value
        ws.cell(row, 3).value = ref_value
        ws.cell(row, 4).value = amount

    for col in range(1, 5):
        apply_style(ws.cell(total_row, col), total_style[col])
        ws.cell(total_row, col).value = None
    ws.cell(total_row, 1).value = "TOTAL"
    if needed:
        ws.cell(total_row, 4).value = "=SUM(D{0}:D{1})".format(
            header_row + 1, total_row - 1
        )
    return total_row


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: solution.py <input.xlsx> <output.xlsx>")
    src, dst = sys.argv[1], sys.argv[2]

    wb = load_workbook(src)
    ranges = parse_ranges(wb["RANGES"])
    lists = wb["LISTS"]

    # Titles are captured first; positions are re-detected before each write so
    # that rows inserted/deleted for one block cannot leave later blocks stale.
    order = [section["title"] for section in find_sections(lists)]
    for title in order:
        section = None
        for candidate in find_sections(lists):
            if candidate["title"] == title:
                section = candidate
                break
        if section is None:
            continue
        write_section(lists, section, aggregate(ranges.get(title, [])))

    wb.save(dst)


if __name__ == "__main__":
    main()
