# SpreadsheetBench v0.1 first-week baseline

This adapter uses the original 912-question archive. Keep the archive outside Git;
`data/*` is ignored by this repository. The original `dataset.json` is a list of
questions, while a research resource package requires an object at that path.
Extract the archive so its original files are at
`data/spreadsheetbench/raw/dataset.json` and
`data/spreadsheetbench/raw/spreadsheet/`, then run from the research root:

```powershell
uv run python -m datasets.spreadsheetbench_package data/spreadsheetbench
```

The conversion creates the package's `dataset.json` and `index.json`, preserving
original task order and listing each input/answer workbook pair. The current
configuration selects `12307`, `15380`, `15829`, `13-1`, and `17-35`.

The trial shows the Agent only the first input workbook. It must create
`/workspace/solution.py` accepting input and output paths and produce
`/workspace/output.xlsx`. After the agent stops, the evaluator runs that script
on cases 2 and 3, then exposes the reference workbooks only to the verifier.
The verifier compares calculated values at `answer_position`, following the
official evaluator's two-decimal numeric normalization, and writes
`verifier/cases.json`. The trial reward is 1 only if every case passes; the
per-case results and pass fraction remain in `Score.metrics`. Workbook outputs,
`solution.py`, and replay command results are saved in
`artifacts/spreadsheetbench/` before the container is destroyed. Missing or
invalid model outputs are valid zero scores; environment or verifier failures
retain an error and no score.

This keeps the original first-case/replay evaluation idea, but asks OpenHands
for a reusable CLI script instead of extracting code from the original agent's
final message. The prompt, tools, and agent scaffold therefore differ from
the original paper setting; report results as this research baseline, not as an
official leaderboard submission. The upstream `evaluation.py` currently points
`proc_path` at the input workbook, so this adapter scores the generated output
explicitly.

On Windows, BenchFlow requires Linux (`fcntl`). Run the evaluation from a Linux
host container with access to the Docker Desktop Linux engine. From the research
root in PowerShell, build the host image and open a shell:

```powershell
docker build -t research-spreadsheetbench-host:latest -f datasets/spreadsheetbench_runner/Dockerfile .
docker run --rm -it -e UV_PROJECT_ENVIRONMENT=/tmp/research-venv `
  -v 'E:\大规模skills:/run/desktop/mnt/host/e/大规模skills' `
  -v /var/run/docker.sock:/var/run/docker.sock `
  -w '/run/desktop/mnt/host/e/大规模skills/research' `
  research-spreadsheetbench-host:latest bash
```

Inside that shell, install the locked Linux dependencies and preview one trial:

```sh
uv sync --locked --python 3.12
uv run --no-sync python -m evaluation \
  --dataset config/datasets/spreadsheetbench.toml \
  --environment config/environments/spreadsheetbench.toml \
  --agent config/agents/openhands-spreadsheetbench.toml \
  --evaluation config/evaluation/spreadsheetbench.toml \
  --name spreadsheetbench-12307-openhands --plan
```

The preview should show the five task IDs and `planned_trials: 5`. For a first
single-task run, temporarily set `task_ids = ["12307"]`; this should show one
trial. Before running, set `THINGO_UNI_API_KEY` in the ignored `research/.env`.
Running without `--plan` calls a paid model. Use a fresh experiment name for
each attempt so failed runs remain available. The recorder writes `agent/trace/`,
`agent/usage.jsonl`, and `agent/usage-config.json` in each trial directory.
Never commit `.env` or the resource package.

## First-week observations

The first five tasks were run once with DeepSeek Flash and OpenHands. Task
`12307` was rerun after a verifier shell script with Windows line endings failed
on Linux. Its later run passed all three cases. Tasks `13-1` and `17-35` ran the
replay script successfully, but the original verifier crashed on blank cells in
read-only workbooks. Their original `result.json` files retain `reward=null`;
the stored output workbooks were scored separately with the corrected verifier.
See the personal delivery repository's `REPORT.md` for the per-task results and
failure analysis.

## DSH single-task check

The `dsh-spreadsheetbench.toml` configuration uses the same DeepSeek Flash
endpoint and dataset with DSH's native `terminal` tool. Its tool set and stop
condition differ from OpenHands, so the single result is a connectivity check,
not a matched harness comparison. In the Linux host container, install the
profile dependencies once before running DSH:

```sh
apt-get update
apt-get install -y --no-install-recommends nodejs npm
npm install --global pnpm@9.15.4
DSH_HOME="$PWD/config/dsh" /tmp/research-venv/bin/dsh plugin --profile sdk-minimal install
uv run --no-sync python -m evaluation \
  --dataset config/datasets/spreadsheetbench.toml \
  --environment config/environments/spreadsheetbench.toml \
  --agent config/agents/dsh-spreadsheetbench.toml \
  --evaluation config/evaluation/spreadsheetbench.toml \
  --name spreadsheetbench-12307-dsh-check --task 12307 --plan
```

The preview should show one trial. Remove `--plan` and choose a fresh name for
the actual run. The first local DSH attempt failed before any model call because
the profile plugin was absent; after installation, the next attempt completed
and passed all three workbook cases. Both attempts remain in ignored logs.
