"""Use the existing SpreadsheetBench workflow with xlsx loaded from the registry."""

import asyncio
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import yaml

from datasets import spreadsheetbench
from datasets.package import read_package_index
from evaluation.contracts import PreparedTask, Task, TrialContext


SKILL_NAME = "xlsx"
SKILL_PATH = "registry:xlsx"


def _xlsx_source(task: Task) -> Path:
    package = read_package_index(task.source["index"],
                                 task_format=spreadsheetbench.TASK_FORMAT)
    return package.root.parent / spreadsheetbench.XLSX_SKILL / "SKILL.md"


def _skill_document(skill_file: Path) -> tuple[dict, str]:
    lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"Skill frontmatter is missing: {skill_file}")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError(f"Skill frontmatter is incomplete: {skill_file}") from error
    metadata = yaml.safe_load("\n".join(lines[1:end]))
    if (not isinstance(metadata, dict) or metadata.get("name") != SKILL_NAME
            or not isinstance(metadata.get("description"), str)
            or not metadata["description"].strip()):
        raise ValueError(f"Unexpected xlsx skill metadata: {skill_file}")
    return metadata, "\n".join(lines[end + 1:]).strip()


def load_tasks(index: Path, task_ids: list[str] | None = None) -> list[Task]:
    tasks = spreadsheetbench.load_tasks(index, task_ids)
    return [replace(task, instruction=task.instruction +
                    "\n\nBefore editing the workbook, use search_skills and load_skill "
                    "to read the registered xlsx skill.") for task in tasks]


def prepare_task(task: Task, destination: Path, condition: str) -> PreparedTask:
    if condition != "registry-skill":
        raise ValueError(f"Unsupported task-two condition: {condition}")
    prepared = spreadsheetbench.prepare_task(task, destination, "no-skill")
    skill_file = _xlsx_source(task)
    metadata, _ = _skill_document(skill_file)
    catalog = [{
        "name": SKILL_NAME,
        "description": metadata["description"],
        "path": SKILL_PATH,
        "sha256": sha256(skill_file.read_bytes()).hexdigest(),
        "source": "data/skillsbench/skills/xlsx-recover-data/xlsx",
    }]
    return PreparedTask(prepared.task_dir, skill_catalog=catalog)


async def setup_environment(context: TrialContext) -> None:
    if context.condition != "registry-skill":
        raise ValueError(f"Unsupported task-two condition: {context.condition}")
    registry = context.environment.executor.registry
    if registry is None:
        raise ValueError("Task-two trial requires environment.registry_url")
    if registry.allowed is not None and SKILL_NAME not in registry.allowed:
        raise ValueError("environment.allowed_skills excludes xlsx")
    registry.allowed = frozenset({SKILL_NAME})
    registered = await asyncio.to_thread(registry.load_skill, SKILL_NAME)
    _, expected_content = _skill_document(_xlsx_source(context.task))
    if registered["content"] != expected_content:
        raise ValueError("Registered xlsx content differs from the task-one source")
    absent = await context.environment.execute(["test", "!", "-e", "/skills"], timeout=10)
    if absent.timed_out:
        raise TimeoutError("Checking /skills timed out")
    if not absent.success:
        raise ValueError("Task image already contains /skills")
