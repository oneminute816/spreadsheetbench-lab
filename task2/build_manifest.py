"""Select 50 unambiguous, text-only SkillsBench skills plus the task-one xlsx skill."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

import yaml


NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
XLSX = Path("xlsx-recover-data/xlsx")


def read_metadata(skill_file: Path) -> dict:
    lines = skill_file.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"Missing frontmatter: {skill_file}")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError(f"Incomplete frontmatter: {skill_file}") from error
    metadata = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(metadata, dict):
        raise ValueError(f"Invalid frontmatter: {skill_file}")
    return metadata


def build_manifest(skills_root: Path) -> dict:
    candidates = []
    all_names = []
    for skill_file in skills_root.rglob("SKILL.md"):
        if skill_file.is_symlink() or skill_file.parent.is_symlink():
            continue
        try:
            metadata = read_metadata(skill_file)
        except (OSError, UnicodeError, yaml.YAMLError, ValueError):
            continue
        name = metadata.get("name")
        if isinstance(name, str):
            all_names.append(name)
        description = metadata.get("description")
        if (not isinstance(name, str) or not NAME.fullmatch(name)
                or not isinstance(description, str) or not description.strip()):
            continue
        relative_dir = skill_file.parent.relative_to(skills_root)
        resources = [path for path in skill_file.parent.rglob("*") if path.is_file()]
        candidates.append((name, relative_dir, skill_file, len(resources) == 1))

    counts = Counter(all_names)
    selected = sorted(
        (item for item in candidates if counts[item[0]] == 1 and item[3]
         and item[1] != XLSX),
        key=lambda item: item[0],
    )[:50]
    if len(selected) != 50:
        raise ValueError(f"Expected 50 eligible skills, found {len(selected)}")
    xlsx_file = skills_root / XLSX / "SKILL.md"
    xlsx_metadata = read_metadata(xlsx_file)
    if xlsx_metadata.get("name") != "xlsx":
        raise ValueError("Task-one xlsx skill is missing")

    def entry(name: str, relative_dir: Path, skill_file: Path) -> dict:
        return {
            "name": name,
            "relative_dir": relative_dir.as_posix(),
            "sha256": sha256(skill_file.read_bytes()).hexdigest(),
        }

    skills = [entry("xlsx", XLSX, xlsx_file)]
    skills.extend(entry(name, directory, file) for name, directory, file, _ in selected)
    return {"schema_version": 1, "source": "skillsbench/skills", "skills": skills}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = build_manifest(args.skills_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Selected {len(manifest['skills'])} skills: {args.output}")


if __name__ == "__main__":
    main()
