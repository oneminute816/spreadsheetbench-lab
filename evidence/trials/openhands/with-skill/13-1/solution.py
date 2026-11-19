import sys
import datetime as dt
from copy import copy

from openpyxl import load_workbook

DATE_FORMATS = ('%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%d/%m/%Y')


def norm_date(value):
    """Canonical key so text dates ('02/22/2024') match real date cells."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        for fmt in DATE_FORMATS:
            try:
                return dt.datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return value


def is_header_row(ws, row):
    return str(ws.cell(row, 1).value).strip().upper() in ('S.N', 'SN')


def block_title(ws, header_row):
    for r in range(header_row - 1, 0, -1):
        label = ws.cell(r, 3).value
        if label not in (None, ''):
            return str(label).strip().upper()
    return None


def read_ranges(ws):
    """Aggregate each RANGES block by (DATE, REF), keyed by the block's title."""
    headers = [r for r in range(1, ws.max_row + 1) if is_header_row(ws, r)]
    blocks = {}
    for idx, h in enumerate(headers):
        end = headers[idx + 1] - 1 if idx + 1 < len(headers) else ws.max_row
        groups = {}
        for r in range(h + 1, end + 1):
            date_v, ref_v, amount = (ws.cell(r, 2).value, ws.cell(r, 4).value,
                                     ws.cell(r, 5).value)
            if date_v is None and ref_v is None:      # blank or next block's title
                continue
            key = (norm_date(date_v), str(ref_v).strip().upper() if ref_v else None)
            if key not in groups:
                groups[key] = [date_v, ref_v, 0]
            groups[key][2] += amount or 0
        blocks[block_title(ws, h)] = list(groups.values())
    return blocks


def list_titles(ws):
    """Block labels live in column C; each owns the rows below it."""
    rows = []
    for r in range(1, ws.max_row + 1):
        label = ws.cell(r, 3).value
        if label not in (None, '') and str(label).strip().upper() not in ('REF', 'STAGE'):
            if ws.cell(r, 1).value in (None, ''):
                rows.append((r, str(label).strip().upper()))
    return rows


def grab_style(cell):
    return {'font': copy(cell.font), 'fill': copy(cell.fill),
            'border': copy(cell.border), 'align': copy(cell.alignment),
            'numfmt': cell.number_format}


def apply_style(cell, style):
    cell.font = copy(style['font'])
    cell.fill = copy(style['fill'])
    cell.border = copy(style['border'])
    cell.alignment = copy(style['align'])
    cell.number_format = style['numfmt']


def write_row(ws, row, values, styles):
    for c, value in enumerate(values, start=1):
        cell = ws.cell(row, c)
        cell.value = value
        apply_style(cell, styles[c - 1])


def main(in_path, out_path):
    wb = load_workbook(in_path)
    ranges_ws = wb['RANGES']
    ws = wb['LISTS']

    titles = list_titles(ws)
    lookup = {}
    for i, (r, name) in enumerate(titles):
        end = titles[i + 1][0] - 1 if i + 1 < len(titles) else ws.max_row
        lookup[name] = (r, end)
    data_blocks = read_ranges(ranges_ws)

    sample_h = next((r for r in range(1, ws.max_row + 1)
                     if is_header_row(ws, r)), None)
    header_tpl = [grab_style(ws.cell(sample_h, c)) for c in range(1, 5)]
    data_tpl = [grab_style(ws.cell(sample_h + 1, c)) for c in range(1, 5)]
    total_r = next((r for r in range(sample_h + 1, ws.max_row + 1)
                    if str(ws.cell(r, 1).value).strip().upper() == 'TOTAL'), None)
    total_tpl = [grab_style(ws.cell(total_r, c)) for c in range(1, 5)]

    jobs = []
    for i, (title_row, name) in enumerate(titles):
        rows = data_blocks.get(name, [])
        header = next((r for r in range(title_row + 1, lookup[name][1] + 1)
                       if is_header_row(ws, r)), None)
        jobs.append((title_row, lookup[name][1], header, rows))

    # Bottom-up: rebuilding a block never disturbs the blocks still to come.
    for title_row, block_end, header, rows in sorted(jobs, key=lambda j: j[0],
                                                     reverse=True):
        if header is None:                                   # brand-new range
            header = title_row + 1
            ws.insert_rows(header, len(rows) + 2)
            write_row(ws, header, ('SN', 'DATE', 'REF', 'AMOUNTS'), header_tpl)
        else:                       # drop the old range, then re-create it
            last = header
            for r in range(header + 1, block_end + 1):
                if any(ws.cell(r, c).value not in (None, '') for c in range(1, 5)):
                    last = r
            if last > header:
                ws.delete_rows(header + 1, last - header)
            ws.insert_rows(header + 1, len(rows) + 1)

        for i, (date_v, ref_v, amount) in enumerate(rows, start=1):
            write_row(ws, header + i, (i, date_v, ref_v, amount), data_tpl)

        total_row = header + len(rows) + 1
        write_row(ws, total_row, ('TOTAL', None, None,
                                  '=SUM(D{}:D{})'.format(header + 1, total_row - 1)
                                  if rows else 0), total_tpl)

    wb.save(out_path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
