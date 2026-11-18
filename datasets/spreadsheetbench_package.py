"""Convert the original SpreadsheetBench v0.1 files into a research package."""

import argparse
import hashlib
import json
from pathlib import Path
import re


SOURCE_URL = (
    "https://github.com/RUCKBReasoning/SpreadsheetBench/"
    "blob/main/data/spreadsheetbench_912_v0.1.tar.gz"
)


def build_package(root: Path) -> None:
    root = root.resolve()
    raw = root / "raw"
    source_file = raw / "dataset.json"
    source_bytes = source_file.read_bytes()
    records = json.loads(source_bytes.decode("utf-8-sig"))
    if not isinstance(records, list) or not records:
        raise ValueError("raw/dataset.json must contain a nonempty task list")

    entries = []
    seen = set()
    for record_index, record in enumerate(records):
        task_id = str(record["id"])
        if not task_id or task_id in seen:
            raise ValueError(f"Invalid or duplicate task id: {task_id!r}")
        seen.add(task_id)
        source_dir = record["spreadsheet_path"]
        expected_dir = f"spreadsheet/{task_id}"
        if source_dir != expected_dir:
            raise ValueError(f"Unexpected spreadsheet path for {task_id}: {source_dir!r}")
        case_dir = raw / source_dir
        cases = []
        for input_file in sorted(case_dir.glob("*.xlsx")):
            match = re.fullmatch(rf"(\d+)_{re.escape(task_id)}_input\s*\.xlsx", input_file.name)
            if match is None:
                continue
            number = match[1]
            if int(number) < 1:
                raise ValueError(f"Invalid case filename: {input_file}")
            answer_file = case_dir / f"{number}_{task_id}_answer.xlsx"
            if not answer_file.is_file():
                raise FileNotFoundError(answer_file)
            cases.append({
                "number": int(number),
                "input": input_file.relative_to(root).as_posix(),
                "answer": answer_file.relative_to(root).as_posix(),
            })
        if not cases:
            raise ValueError(f"Task {task_id} has no workbook cases")
        cases.sort(key=lambda case: case["number"])
        if [case["number"] for case in cases] != list(range(1, len(cases) + 1)):
            raise ValueError(f"Task {task_id} has nonconsecutive case numbers")
        entries.append({"id": task_id, "record_index": record_index, "cases": cases})

    description = {
        "schema_version": 1,
        "id": "spreadsheetbench",
        "version": "v0.1",
        "task_format": "research-spreadsheetbench-v1",
        "provenance": {
            "source": SOURCE_URL,
            "raw_dataset_sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
    }
    index = {"schema_version": 1, "task_count": len(entries), "tasks": entries}
    for name, document in (("dataset.json", description), ("index.json", index)):
        (root / name).write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Directory containing raw/dataset.json and raw/spreadsheet")
    build_package(parser.parse_args().root)
