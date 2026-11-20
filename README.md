# SpreadsheetBench 任务一与任务二

本仓库提供 SpreadsheetBench v0.1 的任务一首周五题预跑，以及任务二 SkillsBench 技能注册、动态卸载与稳定性验证。研究主框架来自 [LDlornd/research](https://github.com/LDlornd/research)。原始工作簿与完整资源包按框架约定保存在本机 `data/`，不随代码仓库提交。

- [任务一：实验结果与问题分析](REPORT.md)
- [逐题产物与轨迹证据](evidence/ARTIFACTS.md)
- [实验任务相关问题回答](docs/实验任务相关问题回答.md)
- [框架流程说明](docs/框架流程说明.md)
- [SpreadsheetBench 原版主数据集分析](docs/SpreadsheetBench原版主数据集分析.md)
- [适配器与运行说明](datasets/SPREADSHEETBENCH.md)
- [任务二：Skill 注册与热更新报告](task2/REPORT.md)
- [任务二：运行说明与代码入口](task2/README.md)

## 代码接入

按 `research` 的 README 将 `agent-session-analyzer` 放在相邻目录，再将本仓库的 `config/`、`datasets/` 和 `.gitattributes` 中同名路径复制到 `research` 根目录。需要 Python 3.12、`uv` 和 Docker Linux 引擎；Windows 上按[适配器说明](datasets/SPREADSHEETBENCH.md)使用 Linux 宿主容器。

官方 SpreadsheetBench v0.1 资源包保存在 `research/data/spreadsheetbench/raw/`，其中应有原始 `dataset.json` 和 `spreadsheet/`。从 `research` 根目录执行：

```sh
uv run python -m datasets.spreadsheetbench_package data/spreadsheetbench
```

这会生成主框架读取的 `data/spreadsheetbench/dataset.json` 和 `index.json`。原始 912 题、工作簿和生成的资源包均不入 Git。当前配置选择 `12307`、`15380`、`15829`、`13-1`、`17-35`，每题一次。`no-skill` 使用 `config/evaluation/spreadsheetbench.toml`；`with-skill` 使用 `config/evaluation/spreadsheetbench-with-skill.toml`，并要求相邻的 `data/skillsbench/skills/xlsx-recover-data/xlsx/` 已存在。运行前在本机被 Git 忽略的 `research/.env` 中配置 `THINGO_UNI_API_KEY`、`RESEARCH_PROJECT_ID` 和 `RESEARCH_USER_ID`；执行实验会调用付费模型。

早期 OpenHands `no-skill` 五题中，三题有原始有效评分，两题因评分器异常保留 `reward=null`，随后使用保存的输出工作簿离线复评。实验报告区分原始评分与复评，并逐项记录两种 harness 的 skill 条件。正式的 10 题 × 3 轮 × 2 模型 × 2 harness 矩阵尚未运行。

## 仓库架构与任务归属

| 路径 | 归属 | 用途 |
| --- | --- | --- |
| `README.md`、`.gitignore`、`.gitattributes` | 共用 | 总入口、私有数据排除规则、跨平台文本格式 |
| `REPORT.md` | 任务一 | 五题逐例结果、失败轨迹、局限 |
| `config/` | 任务一 | SpreadsheetBench 数据集、环境、OpenHands/DSH 与评估条件配置 |
| `datasets/` | 任务一 | 原版数据转换、trial 适配、Docker 环境与评分脚本 |
| `docs/` | 任务一 | 数据集分析、框架流程和任务相关问题回答 |
| `evidence/` | 任务一 | 脱敏的预跑逐题结果、重放摘录与 trace 索引 |
| `task2/config/` | 任务二 | 注册中心版 `xlsx` 单题代表性实验配置 |
| `task2/evidence/` | 任务二 | 51 技能稳定性、Spring Boot 和 Agent trial 的脱敏摘要 |
| `task2/patches/` | 任务二 | `skill_registry` 与 `rsi-flow-spring-boot` 的本地改动补丁 |
| `task2/*.py`、`task2/README.md`、`task2/REPORT.md` | 任务二 | 固定清单、批量验证、代表性适配、运行说明与报告 |
| `logs/`、`data/` | 本机，不提交 | 原始数据、完整运行记录和逐项检查；由 `.gitignore` 排除 |

## 提交边界

任务一以 `4688f8a` 为结束提交，包括此前的 `config/`、`datasets/`、`docs/`、`evidence/` 和根目录 `REPORT.md`。任务二从该基线之后开始：`git log --oneline 4688f8a..main` 列出的提交只包含 `task2/` 成果与本 README 的目录说明。检查任务一历史可运行 `git log --oneline 4688f8a`；检查任务二差异可运行 `git diff --stat 4688f8a..main`。任务一的 20 个预跑 trial 不计入任务二的 51 技能稳定性结果。

## 本机资源边界

原始 SpreadsheetBench 工作簿、完整 SkillsBench 资源包、完整 trace、模型用量账本和 `.env` 均不公开。任务一使用的通用 `xlsx` 来自独立 SkillsBench 资源包，不是 SpreadsheetBench 原版随题技能；其许可证限制复制和分发，本仓库只记录来源定位、SHA-256 和脱敏验证结果。`research`、`skill_registry`、`rsi-flow-spring-boot` 的任务二接入保留在本地，公开可复现代码见 [任务二补丁](task2/patches/README.md)。
