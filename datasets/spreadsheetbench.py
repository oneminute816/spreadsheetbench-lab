"""SpreadsheetBench v0.1 tasks, isolated workbooks, and native-style scoring."""

import hashlib
import json
from pathlib import Path
import shutil

import yaml

from datasets.package import read_package_index, resource_path
from evaluation.contracts import AgentResult, PreparedTask, Score, Task, TrialContext


TASK_FORMAT = "research-spreadsheetbench-v1"
RUNTIME = Path(__file__).with_name("spreadsheetbench_runtime")
XLSX_SKILL = Path("skillsbench/skills/xlsx-recover-data/xlsx")


def _records(package):
    source = resource_path(package.root, "raw/dataset.json")
    content = source.read_bytes()
    expected = package.metadata["provenance"]["raw_dataset_sha256"]
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("SpreadsheetBench source records changed after package conversion")
    records = json.loads(content.decode("utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("SpreadsheetBench raw dataset must be a list")
    return records


def load_tasks(index: Path, task_ids: list[str] | None = None) -> list[Task]:
    package = read_package_index(index, task_format=TASK_FORMAT)
    records = _records(package)
    entries = {entry["id"]: entry for entry in package.index["tasks"]}
    selected = list(entries) if task_ids is None else task_ids
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("Task selection must be nonempty and contain no duplicates")
    unknown = set(selected) - entries.keys()
    if unknown:
        raise ValueError(f"Unknown SpreadsheetBench task IDs: {sorted(unknown)}")

    tasks = []
    for task_id in selected:
        entry = entries[task_id]
        record = records[entry["record_index"]]
        if str(record["id"]) != task_id:
            raise ValueError(f"SpreadsheetBench record order changed for {task_id}")
        instruction = record["instruction"]
        answer_position = record["answer_position"]
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError(f"Empty instruction for {task_id}")
        if not isinstance(answer_position, str) or not answer_position.strip():
            raise ValueError(f"Missing answer position for {task_id}")
        for case in entry["cases"]:
            resource_path(package.root, case["input"], must_exist=False)
            resource_path(package.root, case["answer"], must_exist=False)
        prompt = (
            f"{instruction.strip()}\n\n"
            f"Fill the answer at {answer_position}. The input workbook is /workspace/input.xlsx. "
            "Create /workspace/solution.py that accepts an input workbook path and an output workbook path "
            "as its two command-line arguments. The script must derive its result from the input workbook. "
            "Run it on /workspace/input.xlsx and save /workspace/output.xlsx. "
            "Only this workbook is available while you solve the task."
        )
        tasks.append(Task(
            id=task_id,
            instruction=prompt,
            source={"index": str(package.index_path), "record_index": entry["record_index"],
                    "cases": entry["cases"], "raw_dataset_sha256": package.metadata["provenance"]["raw_dataset_sha256"]},
            metadata={"instruction_type": record["instruction_type"],
                      "answer_position": answer_position, "original_instruction": instruction},
            agent_timeout_sec=600,
        ))
    return tasks


def prepare_task(task: Task, destination: Path, condition: str) -> PreparedTask:
    if condition not in {"no-skill", "with-skill"}:
        raise ValueError(f"Unsupported SpreadsheetBench condition: {condition!r}")
    package = read_package_index(task.source["index"], task_format=TASK_FORMAT)
    _records(package)
    if package.metadata["provenance"]["raw_dataset_sha256"] != task.source["raw_dataset_sha256"]:
        raise ValueError("SpreadsheetBench package changed after task selection")
    cases = task.source["cases"]
    if not cases or cases[0]["number"] != 1:
        raise ValueError(f"Task {task.id} must start with case 1")
    source_input = resource_path(package.root, cases[0]["input"])
    shutil.copytree(RUNTIME, destination)
    shutil.copy2(source_input, destination / "environment" / "input.xlsx")
    (destination / "verifier" / "metadata.json").write_text(
        json.dumps({"task_id": task.id, "answer_position": task.metadata["answer_position"],
                    "case_numbers": [case["number"] for case in cases]}, ensure_ascii=False),
        encoding="utf-8",
    )
    task_document = (
        "---\n"
        "schema_version: '1.3'\n"
        "metadata:\n  author_name: research-team\n  difficulty: medium\n  category: spreadsheet\n"
        "verifier:\n  type: test-script\n  timeout_sec: 600\n  service: main\n"
        "agent:\n  timeout_sec: 600\n"
        "sandbox:\n  network_mode: public\n  build_timeout_sec: 1800\n"
        "  os: linux\n  cpus: 2\n  memory_mb: 4096\n  storage_mb: 10240\n  gpus: 0\n"
        "---\n\n" + task.instruction + "\n"
    )
    (destination / "task.md").write_text(task_document, encoding="utf-8")
    if condition == "no-skill":
        return PreparedTask(destination)

    source = package.root.parent / XLSX_SKILL
    skill_file = source / "SKILL.md"
    if not source.is_dir() or not skill_file.is_file():
        raise FileNotFoundError(f"SkillsBench xlsx skill is missing: {source}")
    for path in source.rglob("*"):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Linked skill resources are not supported: {path}")
    lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"Skill frontmatter is missing: {skill_file}")
    end = next((index for index, line in enumerate(lines[1:], 1) if line == "---"), None)
    if end is None:
        raise ValueError(f"Skill frontmatter is incomplete: {skill_file}")
    metadata = yaml.safe_load("\n".join(lines[1:end]))
    if (not isinstance(metadata, dict) or metadata.get("name") != "xlsx"
            or not isinstance(metadata.get("description"), str)
            or not metadata["description"].strip()):
        raise ValueError(f"Unexpected SkillsBench xlsx skill metadata: {skill_file}")

    skills_dir = destination.parent / "skills"
    shutil.copytree(source, skills_dir / "xlsx")
    catalog = [{
        "name": metadata["name"],
        "description": metadata["description"],
        "path": "/skills/xlsx/SKILL.md",
        "sha256": hashlib.sha256(skill_file.read_bytes()).hexdigest(),
        "source": "data/skillsbench/skills/xlsx-recover-data/xlsx",
    }]
    return PreparedTask(destination, skills_dir, catalog)


async def setup_environment(context: TrialContext) -> None:
    absent = await context.environment.execute(["test", "!", "-e", "/skills"], timeout=10)
    if absent.timed_out:
        raise TimeoutError("Checking /skills timed out")
    if not absent.success:
        raise ValueError("Task image already contains /skills")
    if context.condition == "no-skill":
        if context.prepared.skills_dir is not None or context.prepared.skill_catalog:
            raise ValueError("no-skill task exposes a skill")
        return
    if (context.condition != "with-skill" or context.prepared.skills_dir is None
            or len(context.prepared.skill_catalog) != 1):
        raise ValueError("with-skill task is missing the xlsx skill")
    await context.environment.upload(context.prepared.skills_dir, "/skills")


def create_environment(task_dir: Path, *, output_dir: Path, **options):
    from environment import DockerEnvironment

    return DockerEnvironment(
        task_dir, output_dir=output_dir, workdir="/workspace", cleanup_volumes=True,
        worker_python_executable="/usr/local/bin/python3", **options,
    )


async def evaluate(context: TrialContext, agent: AgentResult) -> Score:
    package = read_package_index(context.task.source["index"], task_format=TASK_FORMAT)
    cases = context.task.source["cases"]
    replay = []
    for case in cases[1:]:
        number = case["number"]
        await context.environment.upload(
            resource_path(package.root, case["input"]), f"/workspace/{number}_input.xlsx"
        )
        result = await context.environment.execute(
            ["python", "/workspace/solution.py", f"/workspace/{number}_input.xlsx",
             f"/workspace/{number}_output.xlsx"], timeout=120,
        )
        replay.append({"case": number, "exit_code": result.exit_code,
                       "timed_out": result.timed_out, "stdout": result.stdout, "stderr": result.stderr})

    artifacts = context.output_dir / "artifacts" / "spreadsheetbench"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "replay.json").write_text(
        json.dumps(replay, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for name in ["solution.py", "output.xlsx", *[f"{case['number']}_output.xlsx" for case in cases[1:]]]:
        remote = f"/workspace/{name}"
        exists = await context.environment.execute(["test", "-f", remote], timeout=10)
        if exists.timed_out:
            raise TimeoutError(f"Checking {remote} timed out")
        if exists.success:
            await context.environment.download(remote, artifacts / name)

    for case in cases:
        number = case["number"]
        await context.environment.upload(
            resource_path(package.root, case["answer"]), f"/workspace/{number}_answer.xlsx"
        )
    rewards = await context.environment.verify()
    verifier_dir = context.output_dir / "verifier"
    report_path = verifier_dir / "cases.json"
    if not report_path.is_file():
        await context.environment.download("/logs/verifier/cases.json", report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    reward = rewards.get("reward")
    if reward is None or float(reward) != report["hard_restriction"]:
        raise ValueError("Native verifier reward does not match workbook case results")
    return Score(reward=float(reward), metrics={"soft_restriction": report["soft_restriction"],
                                               "test_case_results": report["test_case_results"]})
