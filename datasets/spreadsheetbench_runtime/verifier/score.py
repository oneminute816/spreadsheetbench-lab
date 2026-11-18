"""Score SpreadsheetBench output cells using the original benchmark's value rules."""

import datetime
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import BadZipFile

import openpyxl
from openpyxl.utils.cell import range_boundaries
from openpyxl.utils.exceptions import InvalidFileException


WORKSPACE = Path("/workspace")
VERIFIER = Path("/logs/verifier")


def normalized(value):
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    if isinstance(value, datetime.time):
        return str(value)[:-3]
    if isinstance(value, datetime.datetime):
        start = datetime.datetime(1899, 12, 30)
        delta = value - start
        return round(delta.days + delta.seconds / 86400.0, 0)
    if isinstance(value, str):
        try:
            return round(float(value), 2)
        except ValueError:
            return value
    return value


def same_value(expected, actual):
    left, right = normalized(expected), normalized(actual)
    if left in (None, "") and right in (None, ""):
        return True
    return type(left) is type(right) and left == right


def recalculated(source: Path, temporary: Path) -> Path:
    destination = temporary / uuid4().hex
    destination.mkdir()
    profile = temporary / ("profile-" + uuid4().hex)
    result = subprocess.run(
        ["libreoffice", f"-env:UserInstallation={profile.as_uri()}", "--headless",
         "--convert-to", "xlsx", "--outdir", str(destination), str(source)],
        capture_output=True, text=True, timeout=120, check=False,
    )
    output = destination / source.name
    if result.returncode != 0 or not output.is_file():
        raise RuntimeError(f"Formula recalculation failed for {source.name}: {result.stdout} {result.stderr}")
    return output


def compare(expected, actual, answer_position: str) -> tuple[bool, str]:
    for part in answer_position.split(","):
        if "!" in part:
            sheet_name, cell_range = part.split("!", 1)
            sheet_name = sheet_name.strip("'")
        else:
            sheet_name, cell_range = expected.sheetnames[0], part
        cell_range = cell_range.strip("'")
        if sheet_name not in actual:
            return False, f"worksheet not found: {sheet_name}"
        min_col, min_row, max_col, max_row = range_boundaries(cell_range)
        reference_sheet, output_sheet = expected[sheet_name], actual[sheet_name]
        for row in reference_sheet.iter_rows(
            min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col
        ):
            for cell in row:
                found = output_sheet[cell.coordinate].value
                if not same_value(cell.value, found):
                    return False, f"Value difference at {sheet_name}!{cell.coordinate}: expected {cell.value!r}, got {found!r}"
    return True, ""


def compare_files(expected_path: Path, output_path: Path, answer_position: str) -> tuple[bool, str]:
    expected = openpyxl.load_workbook(expected_path, data_only=True, read_only=True)
    try:
        try:
            actual = openpyxl.load_workbook(output_path, data_only=True, read_only=True)
        except (BadZipFile, InvalidFileException) as exc:
            return False, f"Invalid output workbook: {exc}"
        try:
            return compare(expected, actual, answer_position)
        finally:
            actual.close()
    finally:
        expected.close()


def main():
    metadata = json.loads(Path("/verifier/metadata.json").read_text(encoding="utf-8"))
    details = []
    with TemporaryDirectory(prefix="spreadsheetbench-") as directory:
        temporary = Path(directory)
        for number in metadata["case_numbers"]:
            output = WORKSPACE / ("output.xlsx" if number == 1 else f"{number}_output.xlsx")
            if not output.is_file():
                details.append({"case": number, "passed": False, "reason": "output file missing"})
                continue
            answer = WORKSPACE / f"{number}_answer.xlsx"
            if not answer.is_file():
                raise FileNotFoundError(answer)
            expected = recalculated(answer, temporary)
            try:
                actual = recalculated(output, temporary)
                passed, reason = compare_files(expected, actual, metadata["answer_position"])
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                passed, reason = False, str(exc)
            details.append({"case": number, "passed": passed, "reason": reason})

    results = [int(detail["passed"]) for detail in details]
    hard = int(all(results))
    report = {
        "task_id": metadata["task_id"],
        "answer_position": metadata["answer_position"],
        "test_case_results": results,
        "soft_restriction": sum(results) / len(results),
        "hard_restriction": hard,
        "case_details": details,
    }
    VERIFIER.mkdir(parents=True, exist_ok=True)
    (VERIFIER / "cases.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (VERIFIER / "reward.txt").write_text(str(hard), encoding="ascii")


if __name__ == "__main__":
    main()
