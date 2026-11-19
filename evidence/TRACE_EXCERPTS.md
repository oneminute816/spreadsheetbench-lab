# 失败轨迹与技能读取摘录

本文件仅摘录可复核的事件顺序、命令和评分结果。原始 trace、完整工具输出和工作簿保存在本机各 trial 目录，公开报告不把这些内容改写成模型成功或失败的结论。

## `15380`：有效零分与答案配对疑点

OpenHands `no-skill` 的 `agent/tool-calls.jsonl` 中，第 1–6 次终端调用检查用例 1 的工作簿结构与月份映射；第 7 次写入 `/workspace/solution.py`，后续调用检查生成结果。Agent 当时只见用例 1 的输入和题目要求。评估器后来用脚本处理用例 2、3，`verifier/cases.json` 给出 `[1,0,0]`：用例 2 的 `Sheet3!B3` 期望 `FEB`、实际 `SEP`，用例 3 期望 `SEP`、实际 `FEB`。

检查原始编号文件时，用例 2 输入 `A3=2014_09_D2_Reminder_EN`，同编号答案 `A3=2014_02_D2_Reminder_EN`；用例 3 输入的月份代码为 `02`，同编号答案为 `09`。两份答案的 `B3` 对应答案自身的 `A3`。新运行的 OpenHands `with-skill` 仍在相同单元格产生相同方向的差异；其第 1 次终端调用已经读取 skill。现有证据支持“同编号输入与答案可能错配”，尚需核对官方发布包的配对约定，不能擅自交换答案或把这个零分直接归咎于模型。

## `13-1`、`17-35`：Agent 产物与评分失败

早期 OpenHands `no-skill` 两题都生成了 `solution.py` 和输出工作簿。`artifacts/spreadsheetbench/replay.json` 记录用例 2、3 的脚本退出码为 0。随后 verifier 读取只读空单元格时访问 `EmptyCell.coordinate`，`verifier/test-stdout.txt` 记录异常，未产生 reward 文件；原始 `result.json` 分别保留 `status=error`、`reward=null`、`errors[].stage=evaluate`。使用同一批已保存的输出离线复评后，两题的三例均通过。复评是独立补充证据，不修改原始 trial 分数。

## `12307`：技能确实可见且被读取

OpenHands 与 DSH 的 `with-skill` 首题，`task-info.json` 都记录 `xlsx`、容器路径 `/skills/xlsx/SKILL.md` 和原始 `SKILL.md` 的 SHA-256 `fa55245ff2b9789a2976b4f7359bd4d1a4400219407bce1f0f4d58cd81ecfd84`。两者的第 1 次终端工具调用分别执行 `cat /skills/xlsx/SKILL.md` 与 `cat /skills/xlsx/SKILL.md && ...`，返回成功。两条 trial 的 `verifier/cases.json` 均为 `[1,1,1]`。这证明技能正文被展示给模型，不证明模型内部一定依赖了其中某条建议。

## `17-35`：OpenHands with-skill 的可定位失败

`17-35__with-skill__001` 的 OpenHands trace 中，第 1 步 `tool.call`（事件 `a3a1cf84fec24e5e95f5adcaa4c8d715`）执行 `cat /skills/xlsx/SKILL.md` 并检查工作目录；第 19 步（事件 `82f2a13c961d402094fd1fde3594350b`）仍在临时文件上试验公式；第 20 步（事件 `57a35bce1c384feaace5258e9fb609f0`）执行 `sed -n 40,200p /skills/xlsx/recalc.py`。随后 `run.finished` 事件 `87b4d98eebfc4b958f2db17dcbeb02d3` 的结束原因是 `max_iterations`。Agent 未写出 `/workspace/solution.py` 或 `/workspace/output.xlsx`。`artifacts/spreadsheetbench/replay.json` 显示用例 2、3 因找不到 `solution.py` 而退出码为 2；`verifier/cases.json` 的三例结果为 `[0,0,0]`，原因均是 `output file missing`，因此本次严格分 0 是有效评分。

模型看到了用例 1 工作簿、题目要求和技能正文，未看到用例 2、3 或参考答案。轨迹能证明迭代预算在产物生成前耗尽；尚不能仅凭轨迹判断是技能内容分散了注意力、任务复杂度、提示策略还是其他模型决策造成。下一次验证应固定同题与工具预算，比较是否在写出脚本之前消耗了多少轮，并逐步检查最后几次工具调用的目的。

## 早期接入故障

初次 OpenHands `12307` 思高路由运行在评分阶段出现 `/verifier/test.sh: not found`，检查发现脚本为 CRLF 换行；改为 LF 后，同题新 trial 的三例均通过。DSH 首次 `12307` 尝试在 Agent 初始化阶段缺少 `sdk-minimal` profile 的 `dsh-research-tools` 插件，未发生模型调用；安装 profile 依赖后新 trial 通过。这两项属于环境或依赖故障，不计为模型零分。
