# SpreadsheetBench v0.1 baseline

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
configuration selects task `12307`, a cell-level question with three cases.

The trial shows OpenHands only the first input workbook. It must create
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

The preview should show task `12307` and `planned_trials: 1`. Remove `--plan`
only when `.env` contains a valid `DEEPSEEK_API_KEY`,
`RESEARCH_PROJECT_ID=research`, and `RESEARCH_USER_ID=your-id`; running the trial
calls a paid model. Use a new experiment name to preserve earlier attempts.
The existing `cost_tracking = true` and recorder settings import trace usage
into `agent/usage.jsonl` and `logs/model-usage.sqlite3`. Check the ledger from
the research root with:

```sh
uv run --no-sync python -m research_llm logs/model-usage.sqlite3 research --user 'your-id'
```

The first Linux attempt, `spreadsheetbench-12307-openhands-linux`, reached the
Agent but received HTTP 401 from DeepSeek because the configured key was
invalid. Its `reward` is null; the ledger records one failed call with missing
usage and unknown cost. Never commit `.env` or the resource package.

## First single-task result

All attempts used task `12307`, one `no-skill` trial, and the same model and
dataset. The original 912 tasks and workbooks remain outside Git.

| Attempt | Stage reached | Result | Model accounting |
| --- | --- | --- | --- |
| `spreadsheetbench-12307-openhands` | Environment | Windows BenchFlow import failed: `fcntl` unavailable | No model call |
| `spreadsheetbench-12307-openhands-linux` | Agent | DeepSeek rejected the first request with HTTP 401; reward unknown | 1 failed call; usage and cost unknown |
| `spreadsheetbench-12307-openhands-linux-2` | Evaluation | Three cases passed; pass fraction 1.0; strict reward 1.0 | 13 completed calls; estimated CNY 0.06342848 |

For the successful attempt, `answer_position` was `I12:I13`. The Agent produced
`solution.py` and `output.xlsx`; the evaluator replayed the script on cases 2
and 3. `verifier/cases.json` reports `[1, 1, 1]`, and the trial's `result.json`
reports `status=completed`, `reward=1.0`, and no errors. The trace, usage log,
usage configuration, script, and workbook outputs are in the ignored local
experiment directory under `logs/exp/spreadsheetbench/`. This is one selected
task, so it establishes that the baseline can run end to end; it does not
estimate performance over all 912 tasks. The 13 completed calls used 101,248
input tokens and 11,964 output tokens, including 87,424 cached input tokens.
The Agent needed 98.49 seconds and evaluation 28.69 seconds in this run. The 401
request remains in the ledger as an unpriced call and is not included in the CNY
estimate.
