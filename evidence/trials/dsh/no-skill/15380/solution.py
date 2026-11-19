#!/usr/bin/env python3
"""Populate column B with the month matching a code found in column A.

The workbook is expected to define named ranges ``codes2`` and ``month``.
For each row from 3 through 14, the first code from ``codes2`` that occurs
anywhere in the corresponding column-A text is mapped to the value in the
same position of the ``month`` range.
"""

import re
import sys

import openpyxl
from openpyxl.utils import range_boundaries


def named_range_cells(workbook, name):
    """Return (worksheet, min_col, min_row, max_col, max_row) for a name."""
    if name not in workbook.defined_names:
        raise KeyError(f"Named range {name!r} was not found")

    defined_name = workbook.defined_names[name]
    destinations = list(defined_name.destinations)
    if not destinations:
        raise ValueError(f"Named range {name!r} has no valid destination")

    sheet_title, cell_range = destinations[0]
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    return workbook[sheet_title], min_col, min_row, max_col, max_row


def main(input_path, output_path):
    workbook = openpyxl.load_workbook(input_path)

    # Read the two lookup columns from their named ranges.
    _, code_col, code_start_row, _, code_end_row = named_range_cells(
        workbook, "codes2"
    )
    month_sheet, month_col, month_start_row, _, month_end_row = named_range_cells(
        workbook, "month"
    )

    code_count = code_end_row - code_start_row + 1
    month_count = month_end_row - month_start_row + 1
    if code_count != month_count:
        raise ValueError("The 'codes2' and 'month' ranges must have equal sizes")

    # Use the sheet containing the named ranges/data. In the supplied workbook
    # this is Sheet3, with input text in A3:A14 and output in B3:B14.
    sheet = month_sheet
    lookup_pairs = []
    for offset in range(code_count):
        code_value = sheet.cell(code_start_row + offset, code_col).value
        month_value = sheet.cell(month_start_row + offset, month_col).value
        if code_value is not None:
            lookup_pairs.append((str(code_value), month_value))

    def matching_month(source_text):
        """Find a code as a complete underscore/alphanumeric-delimited token.

        Requiring token boundaries is important: a code such as ``01`` would
        otherwise incorrectly match inside the year ``2014``.
        """
        for code_text, month_value in lookup_pairs:
            pattern = (
                r"(?<![A-Za-z0-9])"
                + re.escape(code_text)
                + r"(?![A-Za-z0-9])"
            )
            if re.search(pattern, source_text):
                return month_value
        return None

    # The requested output range is B3:B14.
    for row in range(3, 15):
        source_value = sheet.cell(row, 1).value
        if source_value is None:
            continue
        sheet.cell(row, 2).value = matching_month(str(source_value))

    workbook.save(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python solution.py <input workbook path> <output workbook path>"
        )
    main(sys.argv[1], sys.argv[2])
