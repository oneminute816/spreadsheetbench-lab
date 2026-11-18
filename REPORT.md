# SpreadsheetBench v0.1 首周预跑报告

## 1. 数据集测什么

官方 v0.1 资源包包含 912 道电子表格题。本次选取 3 道单元格级题（`12307`、`15380`、`15829`）和 2 道工作表级题（`13-1`、`17-35`），检查 Agent 能否理解自然语言要求、修改工作簿，并把同一解法用于另外两个输入。五题是定点排障样本，不是从 912 题随机抽样。

## 2. 输入、输出和两个例子

每题有三个编号工作簿用例。Agent 只看到题目要求和用例 1 的输入工作簿，需生成 `/workspace/solution.py`（接收输入、输出路径）和 `/workspace/output.xlsx`。Agent 结束后，评估器用该脚本处理用例 2、3，才向评分器提供三个参考答案。答案工作簿从未进入 Agent 作答环境。

- `12307`：根据国家清单和各公司雇员数，填写 `I12:I13`，统计雇员数大于零的国家数。三例都通过。
- `15380`：从 `A3:A14` 的文本提取月份代码，按工作簿内 `codes2` 与 `month` 对照表填写 `B3:B14`。用例 1 通过，用例 2、3 在 `Sheet3!B3` 与参考值不符；其原始文件配对存在下文所述的矛盾。

## 3. 环境与框架支持

使用 `research` 的 trial 调度、BenchFlow Docker 环境、OpenHands SDK 1.53.0 和 trace recorder。任务容器为 Python 3.12，安装 `openpyxl==3.1.5` 与 LibreOffice Calc；LibreOffice 用于重算公式后比较缓存值。Windows 本机无法导入 BenchFlow 所需的 `fcntl`，因此从 Docker Desktop 的 Linux 宿主容器运行。资源包位于 Git 忽略的 `research/data/spreadsheetbench/`，适配器只提交转换代码和配置。

## 4. Agent 工具与实验条件

本轮固定 `deepseek/deepseek-flash`、OpenHands、`no-skill`、每题一次、最多 20 次 Agent 迭代、每题 600 秒，工具为 `terminal`、`think`、`finish`。五题共 88 次模型调用，输入 1,702,605 tokens、输出 115,955 tokens，总耗时 852.1 秒。各题的模型、工具和预算相同；`12307` 在修复脚本换行后另有一次新运行，早先失败尝试仍保留。

## 5. 评分与结果

评分器按原题的 `answer_position` 比较重算后的单元格值，数值按两位小数归一化。逐例通过率为 `通过用例数/3`，严格分仅在三例全对时为 1。`reward=null` 表示未得到有效评分，不能当作零分。表中“复评”仅对原始评分器崩溃的 trial 使用同一次 Agent 保存的输出工作簿，不再调用模型，也不改写原始 `result.json`。

| 题目 | 原始状态/严格分 | 三例结果 | 复评严格分 | 调用数 | 输入/输出 tokens | 耗时(秒) |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `12307` | completed / 1 | 1,1,1 | 不需要 | 20 | 255,479 / 24,166 | 154.1 |
| `15380` | completed / 0 | 1,0,0 | 不需要 | 12 | 128,429 / 8,733 | 111.7 |
| `15829` | completed / 1 | 1,1,1 | 不需要 | 16 | 203,997 / 14,616 | 169.8 |
| `13-1` | error / null | 1,1,1（复评） | 1 | 20 | 744,465 / 36,179 | 217.3 |
| `17-35` | error / null | 1,1,1（复评） | 1 | 20 | 370,235 / 32,261 | 199.2 |

原始 trial 的有效评分覆盖率为 3/5；离线复评后五题都有逐例结果，严格通过 4/5。`12307`、`13-1`、`17-35` 的 Agent 达到 20 次迭代上限，但在此之前已留下可重放的脚本和结果工作簿。这个小样本不能用于估计全数据集通过率，也不能比较模型或 harness 优劣。

## 6. 失败原因与证据

- `12307` 的首次思高路由运行在评分阶段报 `rc=127`，`verifier/test-stdout.txt` 为 `/verifier/test.sh: not found`。脚本当时是 CRLF 换行；改为 LF 并设置 `.gitattributes` 后，新 trial 的 `verifier/cases.json` 为 `[1,1,1]`。首次失败记录保留，未纳入上表五题汇总。
- `13-1`、`17-35` 的原始 `result.json` 均为 `reward=null`，`verifier/test-stdout.txt` 指向只读 `EmptyCell` 没有 `coordinate` 属性。修正评分器为按行列坐标同步遍历后，复评目录中的 `cases.json` 均为 `[1,1,1]`。两题的 `artifacts/spreadsheetbench/replay.json` 显示后两个用例脚本退出码均为 0。
- `15380` 原始 `verifier/cases.json` 报用例 2 的 `Sheet3!B3` 应为 `FEB`、实际 `SEP`，用例 3 则应为 `SEP`、实际 `FEB`。检查官方编号文件发现：用例 2 输入 `A3=2014_09_D2_Reminder_EN`，同编号答案却改成 `A3=2014_02_D2_Reminder_EN`；用例 3 输入是 `02`，同编号答案是 `09`。两个答案中的 `B3` 分别对应答案自身的 `A3`。适配器按相同编号配对，符合资源包文件名；这提示原始用例 2、3 的输入与答案可能错配。当前严格分仍按原始文件为 0，正式统计前应核实官方配对，不擅自交换答案。

## DSH 连通性实验

另用 `deepseek-flash`、DSH、`no-skill` 在 `12307` 上运行一次。首次尝试在 Agent 初始化阶段因 `sdk-minimal` profile 缺少 `dsh-research-tools` 插件而退出，没有模型调用。安装 profile 依赖后，新 trial 正常结束，三个用例均通过，严格分 1.0；6 次模型调用，耗时 91.4 秒。DSH trace 原样记录未缓存输入 2,821、缓存读取 18,971、输出 6,931 tokens，三项合计 28,723 tokens。其工具仅有 `terminal`，结束条件与 OpenHands 不同；这个单题结果只能说明 DSH 已接通，不能据此比较两个 harness。

每个 trial 的 `agent/trace/`、`agent/usage.jsonl`、`agent/usage-config.json`、`artifacts/spreadsheetbench/`、`verifier/` 和 `result.json` 保存在本机 Git 忽略的 `research/logs/exp/spreadsheetbench/`。下一阶段需固定相同任务、工具能力、预算和重复次数，再进行正式对照。正式矩阵为 10 题 × 3 轮 × 2 模型 × 2 harness，共 120 trial，需分别记录有效评分覆盖率和失败类型。
