"""Run repeatable live-registry checks without storing skill instructions."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener


LOCAL_HTTP = build_opener(ProxyHandler({}))


def call(base: str, endpoint: str, payload: dict | None = None) -> tuple[int, dict]:
    if payload is None:
        request = Request(base + endpoint, headers={"Accept": "application/json"})
    else:
        request = Request(
            base + endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
    try:
        with LOCAL_HTTP.open(request, timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            return error.code, json.load(error)
        except ValueError:
            return error.code, {}


def measure(records: list, round_number: int, stage: str, name: str, action) -> bool:
    started = time.perf_counter()
    try:
        action()
        success, error = True, None
    except Exception as exc:
        success, error = False, {"type": type(exc).__name__, "detail": str(exc)}
    records.append({
        "round": round_number,
        "stage": stage,
        "name": name,
        "success": success,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "error": error,
    })
    return success


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def load_manifest(path: Path, skills_root: Path) -> list[dict]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expect(manifest.get("schema_version") == 1, "Unknown manifest schema")
    skills = manifest["skills"]
    expect(len(skills) >= 51, "Manifest has fewer than 51 skills")
    expect(len({skill["name"] for skill in skills}) == len(skills), "Duplicate skill names")
    for skill in skills:
        relative = Path(skill["relative_dir"])
        expect(not relative.is_absolute() and ".." not in relative.parts, "Unsafe relative path")
        skill_file = (skills_root / relative / "SKILL.md").resolve()
        expect(skill_file.is_relative_to(skills_root), "Skill escapes source root")
        expect(skill_file.is_file(), f"Missing SKILL.md for {skill['name']}")
        expect(sha256(skill_file.read_bytes()).hexdigest() == skill["sha256"],
               f"Source hash differs for {skill['name']}")
        skill["directory"] = str(skill_file.parent)
    return skills


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def summarize(records: list[dict], *, manifest: Path, skill_count: int, rounds: int,
              concurrency: int, pid: int, alive: bool, duration: float) -> dict:
    groups = defaultdict(list)
    for record in records:
        groups[record["stage"]].append(record)
    stages = {}
    for stage, items in sorted(groups.items()):
        times = [item["duration_ms"] for item in items]
        stages[stage] = {
            "checks": len(items),
            "passed": sum(item["success"] for item in items),
            "failed": sum(not item["success"] for item in items),
            "p50_ms": round(statistics.median(times), 2),
            "p95_ms": round(percentile(times, 0.95), 2),
        }
    return {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha256(manifest.read_bytes()).hexdigest(),
        "skill_count": skill_count,
        "rounds": rounds,
        "concurrency": concurrency,
        "server_pid": pid,
        "same_process_alive_at_end": alive,
        "duration_sec": round(duration, 2),
        "stages": stages,
        "failures": [
            {"round": item["round"], "stage": item["stage"],
             "name": item["name"], "type": item["error"]["type"]}
            for item in records if not item["success"]
        ],
    }


def run(skills: list[dict], base: str, rounds: int, concurrency: int) -> list[dict]:
    records = []
    for round_number in range(1, rounds + 1):
        active = []
        for skill in skills:
            name = skill["name"]

            def register(skill=skill):
                status, data = call(base, "/add_skill", {"root_dir": skill["directory"]})
                expect(status == 200 and data.get("name") == skill["name"],
                       f"Registration failed: HTTP {status}")

            if not measure(records, round_number, "register", name, register):
                continue
            active.append(skill)

            def search(name=name):
                status, data = call(base, "/search_skills", {
                    "query": "", "exposed_skills": [name]})
                expect(status == 200 and data.get("count") == 1
                       and data["skills"][0]["name"] == name,
                       f"Search mismatch: HTTP {status}")

            def load(name=name):
                status, data = call(base, "/load_skill?" + urlencode({"skill_name": name}))
                loaded = data.get("skill", {})
                expect(status == 200 and loaded.get("name") == name
                       and bool(loaded.get("content")) and isinstance(loaded.get("resources"), list),
                       f"Load mismatch: HTTP {status}")

            measure(records, round_number, "search", name, search)
            measure(records, round_number, "load", name, load)

        if round_number == 1 and active:
            first = active[0]

            def duplicate():
                status, _ = call(base, "/add_skill", {"root_dir": first["directory"]})
                expect(status == 400, f"Duplicate was accepted: HTTP {status}")

            measure(records, round_number, "reject_duplicate", first["name"], duplicate)

            with tempfile.TemporaryDirectory(prefix="task2-invalid-skill-") as bad_dir:
                (Path(bad_dir) / "SKILL.md").write_text(
                    "---\nname: task2-invalid\n---\nInvalid metadata\n", encoding="utf-8")

                def invalid():
                    status, _ = call(base, "/add_skill", {"root_dir": bad_dir})
                    expect(status == 400, f"Invalid metadata was accepted: HTTP {status}")
                    status, data = call(base, "/search_skills", {
                        "query": "", "exposed_skills": ["task2-invalid"]})
                    expect(status == 200 and data.get("count") == 0,
                           "Invalid skill changed the index")

                measure(records, round_number, "reject_invalid", "task2-invalid", invalid)

            def xlsx_resource():
                status, data = call(base, "/load_resource?" + urlencode({
                    "skill_name": "xlsx", "relative_path": "recalc.py"}))
                expect(status == 200 and data.get("success") is True
                       and bool(data.get("content")), "xlsx resource was not readable")

            measure(records, round_number, "load_xlsx_resource", "xlsx", xlsx_resource)

        def concurrent_load(skill):
            name = skill["name"]
            status, data = call(base, "/load_skill?" + urlencode({"skill_name": name}))
            expect(status == 200 and data.get("skill", {}).get("name") == name,
                   f"Concurrent load mismatch: HTTP {status}")

        def timed_concurrent_load(skill):
            result = []
            measure(result, round_number, "concurrent_load", skill["name"],
                    lambda: concurrent_load(skill))
            return result[0]

        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(timed_concurrent_load, skill) for skill in active]
            for future in as_completed(futures):
                records.append(future.result())

        for skill in reversed(active):
            name = skill["name"]

            def delete(name=name):
                status, data = call(base, "/delete_skill", {"skill_name": name})
                expect(status == 200 and data.get("deleted") is True,
                       f"Deletion failed: HTTP {status}")

            if not measure(records, round_number, "delete", name, delete):
                continue

            def search_absent(name=name):
                status, data = call(base, "/search_skills", {
                    "query": "", "exposed_skills": [name]})
                expect(status == 200 and data.get("count") == 0,
                       f"Deleted skill still searchable: HTTP {status}")

            def load_absent(name=name):
                status, _ = call(base, "/load_skill?" + urlencode({"skill_name": name}))
                expect(status == 404, f"Deleted skill still loads: HTTP {status}")

            measure(records, round_number, "search_after_delete", name, search_absent)
            measure(records, round_number, "load_after_delete", name, load_absent)
            measure(records, round_number, "source_preserved", name,
                    lambda skill=skill: expect((Path(skill["directory"]) / "SKILL.md").is_file(),
                                               "Source file disappeared"))
        if active:
            time.sleep(1.2)
            first_name = active[0]["name"]

            def remains_absent():
                status, data = call(base, "/search_skills", {
                    "query": "", "exposed_skills": [first_name]})
                expect(status == 200 and data.get("count") == 0,
                       "Deleted skill returned after background refresh")

            measure(records, round_number, "absent_after_refresh", first_name,
                    remains_absent)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-project", required=True, type=Path)
    parser.add_argument("--skills-root", required=True, type=Path)
    parser.add_argument("--manifest", type=Path,
                        default=Path(__file__).with_name("skills-manifest.json"))
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--limit", type=int, default=51,
                        help="Use the first N fixed manifest entries; 1 checks xlsx only")
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--raw", type=Path)
    args = parser.parse_args()
    if args.rounds < 1 or args.concurrency < 1 or args.limit < 1:
        parser.error("rounds, concurrency and limit must be positive")
    skills_root = args.skills_root.resolve()
    manifest = args.manifest.resolve()
    skills = load_manifest(manifest, skills_root)
    if args.limit > len(skills):
        parser.error("limit exceeds the fixed manifest size")
    skills = skills[:args.limit]
    port = free_port()
    base = f"http://127.0.0.1:{port}"

    with tempfile.TemporaryDirectory(prefix="task2-registry-") as empty_root:
        env = os.environ.copy()
        env.update({"SKILLS_DIR": empty_root, "HOST": "127.0.0.1", "PORT": str(port),
                    "PYTHONPATH": str(args.registry_project.resolve() / "src")})
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as server_log:
            server = subprocess.Popen(
                [sys.executable, "-m", "skill_registry.app"],
                cwd=args.registry_project.resolve(), env=env,
                stdout=server_log, stderr=subprocess.STDOUT,
            )
            started = time.perf_counter()
            try:
                for _ in range(100):
                    if server.poll() is not None:
                        break
                    try:
                        status, _ = call(base, "/openapi.json")
                        if status == 200:
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Registry did not become ready")
                if server.poll() is not None:
                    server_log.seek(0)
                    raise RuntimeError("Registry exited during startup: " + server_log.read()[-2000:])
                records = run(skills, base, args.rounds, args.concurrency)
                alive = server.poll() is None
                summary = summarize(records, manifest=manifest, skill_count=len(skills),
                                    rounds=args.rounds,
                                    concurrency=args.concurrency, pid=server.pid, alive=alive,
                                    duration=time.perf_counter() - started)
                args.summary.parent.mkdir(parents=True, exist_ok=True)
                args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
                if args.raw:
                    args.raw.parent.mkdir(parents=True, exist_ok=True)
                    args.raw.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
                print(f"Checks: {len(records)}; failures: {len(summary['failures'])}; "
                      f"same process alive: {alive}")
                if summary["failures"] or not alive:
                    raise SystemExit(1)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    main()
