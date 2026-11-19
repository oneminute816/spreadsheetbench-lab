# SpreadsheetBench v0.1 首周五题预跑报告

## 实验范围与配置

本周从官方 v0.1 的 912 题中定点选取 `12307`、`15380`、`15829`、`13-1`、`17-35`，覆盖条件汇总、文本查表、费用计算、工作表合并和日期筛选。办公场景筛选理由及六个数据集问题见[实验任务相关问题回答](docs/实验任务相关问题回答.md)；[框架流程](docs/框架流程说明.md)和[主数据集分析](docs/SpreadsheetBench原版主数据集分析.md)单独提交。

模型统一为思高国内站的 DeepSeek Flash，每题每条件一次。OpenHands 使用 `terminal`、`think`、`finish`，最多 20 次 Agent 迭代；DSH 使用 `terminal`。两者每题 Agent 总时限均为 600 秒，终端工具超时 120 秒，工作簿容器与评分规则相同。两种 harness 的工具集合及停止条件仍有差异，故不能把本轮五题视为严格的 harness 优劣对照。每种 harness 分别运行 `no-skill` 与 `with-skill`；后者注入 SkillsBench 资源包的通用 `xlsx` skill，原始 `SKILL.md` SHA-256 为 `fa55245ff2b9789a2976b4f7359bd4d1a4400219407bce1f0f4d58cd81ecfd84`。

Agent 只看到题目要求及用例 1 的输入工作簿，需生成 `solution.py` 和 `output.xlsx`。Agent 结束后，评估器才让脚本处理用例 2、3，并把参考答案交给 verifier。LibreOffice 重算后，按题目 `answer_position` 比较计算值；逐例结果为 0/1，三例全对才得到严格分 1。使用可复用脚本的提示和 Agent 架构与官方论文设置不同，以下是本实验基线，不是官方榜单成绩。

## 实验表格：运行结果，失败轨迹记录

### 运行结果

| Harness | 模型 | 通过/有效评分/计划 | 通过率 | 平均 token | 平均用时 | 特色指标 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| OpenHands · no-skill | DeepSeek Flash | 2/3/5 | 66.7% | 363,712 | 170.4 秒 | 原始有效评分覆盖率 3/5；三例全对 2 题；2 题评分缺失 |
| OpenHands · with-skill | DeepSeek Flash | 3/5/5 | 60.0% | 402,829 | 211.2 秒 | 覆盖率 5/5；五题均读取 skill；`17-35` 三例输出缺失 |
| DSH · no-skill | DeepSeek Flash | 4/5/5 | 80.0% | 170,234 | 126.8 秒 | 覆盖率 5/5；`15380` 三例为 [1,0,0] |
| DSH · with-skill | DeepSeek Flash | 4/5/5 | 80.0% | 422,923 | 166.8 秒 | 覆盖率 5/5；五题均读取 skill；`15380` 为 [1,0,0] |

“通过率”分母是原始**有效评分数**，不是计划数；`reward=null` 不算零分。平均 token 和平均用时以各组全部 5 个实际运行 trial 为分母，耗时采用 `result.json.duration_sec`，包含准备、环境、Agent、评分及清理。token 采用 `agent/usage.jsonl` 的逐次 `total_tokens` 求和；四组 20 个 trial 均有用量。DSH 的 `total_tokens` 包含单列的缓存读取 token，OpenHands 的输入 token 中已包含缓存读取量；不要把两者的 `input_tokens` 直接相加比较。平均值仅描述这批运行，不说明 skill 造成了用量变化。

逐题的原始状态、三例结果、token 和耗时如下。符号 `—` 表示原始 trial 没有有效评分，绝非零分；“读 skill”只依据实际终端调用计数。

| Harness / 条件 | 题目 | 原始状态 / 严格分 | 三例 | token | 用时(秒) | 读 skill |
| --- | --- | --- | --- | ---: | ---: | ---: |
| OpenHands / no-skill | `12307` | completed / 1 | 1,1,1 | 279,645 | 154.1 | 不提供 |
| OpenHands / no-skill | `15380` | completed / 0 | 1,0,0 | 137,162 | 111.7 | 不提供 |
| OpenHands / no-skill | `15829` | completed / 1 | 1,1,1 | 218,613 | 169.8 | 不提供 |
| OpenHands / no-skill | `13-1` | error / — | 未产生原始评分 | 780,644 | 217.3 | 不提供 |
| OpenHands / no-skill | `17-35` | error / — | 未产生原始评分 | 402,496 | 199.2 | 不提供 |
| OpenHands / with-skill | `12307` | completed / 1 | 1,1,1 | 535,030 | 244.5 | 是 |
| OpenHands / with-skill | `15380` | completed / 0 | 1,0,0 | 161,895 | 125.5 | 是 |
| OpenHands / with-skill | `15829` | completed / 1 | 1,1,1 | 100,441 | 86.7 | 是 |
| OpenHands / with-skill | `13-1` | completed / 1 | 1,1,1 | 667,040 | 247.0 | 是 |
| OpenHands / with-skill | `17-35` | completed / 0 | 0,0,0 | 549,741 | 352.3 | 是 |
| DSH / no-skill | `12307` | completed / 1 | 1,1,1 | 28,723 | 91.4 | 不提供 |
| DSH / no-skill | `15380` | completed / 0 | 1,0,0 | 31,137 | 99.3 | 不提供 |
| DSH / no-skill | `15829` | completed / 1 | 1,1,1 | 44,155 | 95.6 | 不提供 |
| DSH / no-skill | `13-1` | completed / 1 | 1,1,1 | 438,184 | 179.5 | 不提供 |
| DSH / no-skill | `17-35` | completed / 1 | 1,1,1 | 308,969 | 168.3 | 不提供 |
| DSH / with-skill | `12307` | completed / 1 | 1,1,1 | 83,113 | 98.9 | 是 |
| DSH / with-skill | `15380` | completed / 0 | 1,0,0 | 37,970 | 84.7 | 是 |
| DSH / with-skill | `15829` | completed / 1 | 1,1,1 | 78,192 | 102.4 | 是 |
| DSH / with-skill | `13-1` | completed / 1 | 1,1,1 | 542,091 | 186.3 | 是 |
| DSH / with-skill | `17-35` | completed / 1 | 1,1,1 | 1,373,249 | 361.9 | 是 |

旧 OpenHands `no-skill` 的 `13-1`、`17-35` 原始评分器异常后，用**同一次 Agent 保存的输出工作簿**离线复评，分别得到 [1,1,1] 和严格分 1。复评不调用模型、不覆盖原始 `result.json`，也不计入上表原始有效评分覆盖率。该结果说明产物在修复评分器后可通过，不应把原始缺失评分改写成模型零分。

### 失败轨迹记录

| 任务/配置/轮次 | 失败表现 | Trace 链接及关键步骤 | 涉及模块 | 暂定解释及待验证问题 | 希望补齐的能力 | 成功轨迹或反例 |
| --- | --- | --- | --- | --- | --- | --- |
| `17-35` / OpenHands + DeepSeek Flash + with-skill / 第 1 轮 | 有效严格分 0，三例均缺输出；Agent 达到 20 次迭代上限 | [轨迹摘录](evidence/TRACE_EXCERPTS.md#17-35openhands-with-skill-的可定位失败)：第 1 次终端调用读 skill；第 20 次仍在读 `recalc.py`；未写 `solution.py`；用例 2、3 重放退出码 2 | OpenHands Agent、终端、SpreadsheetBench 适配器 | 可确定产物生成前耗尽迭代；不能仅凭当前 trace 判定是技能内容、任务复杂度还是模型策略导致。需对照同题每轮查看何时开始写脚本及模型在最后数轮看到的工具输出 | 保留逐步工具与产物时间线；在正式对照中明确迭代预算 | 同题 DSH 两个条件均 [1,1,1]；旧 OpenHands no-skill 的保存产物离线复评为 [1,1,1]，但原始评分缺失 |
| `15380` / 两种 harness、两种条件 / 各第 1 轮 | 四条 trial 均为有效严格分 0，三例 [1,0,0] | [轨迹摘录](evidence/TRACE_EXCERPTS.md#15380有效零分与答案配对疑点)：Agent 只见用例 1；重放后用例 2 的 `Sheet3!B3` 期望 FEB、实际 SEP，用例 3 相反 | 原始资源包配对、评分器 | 用例 2/3 的同编号输入 `A3` 与答案 `A3` 月份代码对调，疑似配对问题。仍需核对官方发布包和配对约定；目前不交换答案，也不改原始零分 | 数据集接入时检查同编号输入/答案关键字段的一致性，并记录异常样本 | 四条 trial 的用例 1 均通过；答案 `B3` 与答案自身 `A3` 一致 |
| `13-1`、`17-35` / OpenHands + no-skill / 第 1 轮 | 原始 `reward=null`，评分器未产出 reward 文件 | [轨迹摘录](evidence/TRACE_EXCERPTS.md#13-117-35agent-产物与评分失败)：Agent 已交付脚本和工作簿；用例 2、3 重放退出码 0；verifier 在读取只读空单元格时访问不存在的 `coordinate` | SpreadsheetBench verifier、评估阶段 | 可定位为旧评分器异常；仍需对其他工作表级题检查空单元格及行列坐标处理 | verifier 对 `EmptyCell` 用行列索引定位，异常时保留逐例上下文 | 保存的输出离线复评两题均 [1,1,1]；新 `with-skill` 运行的 `13-1` 正常评分 |
| `12307` / OpenHands + no-skill / 早期接入尝试 | `/verifier/test.sh: not found`，无评分 | [轨迹摘录](evidence/TRACE_EXCERPTS.md#早期接入故障)：评分脚本当时是 CRLF；Agent 阶段已结束 | 任务副本、Linux verifier 启动 | 直接证据指向换行符；未见模型作答错误证据 | 固定脚本 LF 并在接入时检查可执行性 | 修复后同题三例 [1,1,1] |
| `12307` / DSH + no-skill / 早期接入尝试 | Agent 初始化失败，无模型调用、无评分 | [轨迹摘录](evidence/TRACE_EXCERPTS.md#早期接入故障)：`sdk-minimal` 缺 `dsh-research-tools` 插件 | DSH profile 依赖 | 本地依赖缺失已由安装后同题成功验证；其他平台仍需按框架说明准备 profile | 在运行前检查 profile 插件是否存在 | 安装后同题三例 [1,1,1] |

模型实际看到了什么：所有题的 Agent 只见当前题要求与用例 1 输入；`with-skill` 的五题在两个 harness 下都可在工具日志中定位到读取 `/skills/xlsx/SKILL.md` 的成功调用。用例 2、3 和参考答案仅在 Agent 结束后进入评估阶段。上述“读 skill”证据证明正文被送回模型，不证明模型内部依赖了它的某项建议。

## 接口差异、缺失依赖与建议修改位置

| 观察到的事实 | 证据 | 建议位置（本周未改框架核心） |
| --- | --- | --- |
| 原版资源包的 `dataset.json` 是题目列表，`research` 包描述要求对象；原始答案与输入必须在评分阶段隔离 | 转换程序及 `raw/dataset.json`、包内 `dataset.json`/`index.json` | 保持适配层转换与阶段隔离；数据包协议见 `research/datasets/README.md` |
| 原版评分脚本曾把 `proc_path` 指向输入工作簿；本实验需明确比较生成输出 | 原版 `evaluation.py` 与本适配器 `verifier/score.py` | 数据集评分适配器显式接收输出路径；正式复现前核对官方上游版本 |
| Windows 原生运行遇到 BenchFlow 的 `fcntl`；DSH 首次运行缺 profile 插件 | 早期错误日志、Linux 宿主及安装后的成功 trial | `research/README.md` 环境说明、`config/dsh/profiles/sdk-minimal` 依赖准备 |
| 空单元格曾使评分器报错，导致两个原始 trial 缺分 | 原始 `result.json` 的 `evaluate:RewardFileNotFoundError` 与 verifier traceback | 本仓库 `datasets/spreadsheetbench_runtime/verifier/score.py` 已按行列索引读取；框架可考虑保留更直接的 verifier traceback 索引 |
| `no-skill` 与 `with-skill` 的技能来源必须可核对，目录存在不等于实际使用 | `task-info.json` 的 skill 哈希、终端调用中的读取事件 | 本仓库适配器的准备/设置函数；报告分列“可见”和“实际读取” |

## 产物、配置与后续

本仓库的 [配置目录](config/) 保存五题清单、两个 harness 和两种 skill 条件；[适配器](datasets/spreadsheetbench.py)保存工作簿隔离、重放和评分调用逻辑。[逐题证据目录](evidence/trials/)保存原始逐例评分、重放退出码和存在的生成脚本；[证据索引](evidence/ARTIFACTS.md)说明缺失项。完整 `agent/trace/`、`agent/usage.jsonl`、`agent/usage-config.json`、`result.json`、生成工作簿及原始资源包仍在本机 `research/logs/exp/spreadsheetbench/` 与 `research/data/`，没有公开原始会话或工作簿。

本轮五题预跑主要证明接入流程并定位失败。不能据这批单次结果推断 skill 或 harness 的稳定优劣。接入稳定后再固定 10 题、三轮、两模型、两 harness，计划共 120 trial；正式分析应保持相同任务、工具能力、预算和重复次数，并继续分别统计环境失败、缺失评分和合法零分。SpreadsheetBench 2 仅作为后续扩展，本周不做自动修订循环。
