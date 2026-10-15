# Life2English 输入输出协议

本文件是 SKILL.md 引用的协议参考。定义 Life2English 作为 Skill 被 **智能体 / 程序** 调用时的
输入输出契约（JSON over stdin/stdout）。

- 入口：`scripts/skill_api.py`
- 输入：stdin 传入一个 JSON 对象
- 输出：stdout 返回一个 JSON 对象，`ok` 表示成功，失败时 `error` 给出原因
- 编码：UTF-8（脚本内部已 `reconfigure`，Windows 亦一致）

## 0. 通用响应结构

```json
{ "ok": true, "action": "<动作名>", "...": "该动作的载荷" }
```

失败时：

```json
{ "ok": false, "error": "可读的错误原因" }
```

未知 action 时额外返回 `supported`（支持的动作列表）。

## 1. action: list_scenes

列出全部支持的场景。

- 输入：`{"action": "list_scenes"}`

响应载荷：

| 字段 | 类型 | 说明 |
|---|---|---|
| `scenes[].id` | string | 场景唯一标识（scene_id） |
| `scenes[].name` | string | 场景中文名 |
| `scenes[].summary` | string | 一句话说明 |
| `scenes[].tags` | string[] | 主题/意图标签 |
| `scenes[].difficulty` | string | 难度（入门 / 入门-进阶 / 进阶） |
| `scenes[].example` | string | 触发示例句 |

## 2. action: recognize

场景识别。

- 输入：`{"action": "recognize", "input": "<用户的一句话描述>"}`

响应载荷：

| 字段 | 类型 | 说明 |
|---|---|---|
| `kind` | string | `strong` 完全匹配 / `weak` 部分匹配 / `ambiguous` 多场景并列 / `none` 无匹配 / `empty` 空输入 / `invalid` 无法理解 |
| `scene_id` | string\|null | 命中场景 id（ambiguous/none/empty/invalid 时为 null） |
| `scene_name` | string\|null | 命中场景名（ambiguous/none/empty/invalid 时为 null） |
| `matched_keywords` | string[] | 命中的关键词 |
| `ambiguous` | string[] | `kind=ambiguous` 时并列的场景 id 列表（保持模板定义顺序） |
| `candidates[]` | object[] | `ambiguous` / `none` 时的候选列表，含 `scene_id` / `name` / `reason` |
| `message` | string | 提示信息 |

**调用方处理约定**：`strong` 直接进入学习；`weak` 必须先向用户确认再复用模板；
`ambiguous` 展示 `candidates`（`ambiguous` 字段给出并列场景 id），请用户明确选择一个再进入学习，
**不要替用户默认取第一个**；`none` 展示 `candidates` 让用户选择或重述；
`empty` / `invalid` 提示后允许重试。

## 3. action: task

生成学习任务。

- 输入：`{"action": "task", "scene_id": "coffee_ordering"}`
  （也可用 `input` 代替 `scene_id`，内部会先做一次识别）

响应载荷 `task`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `scene_id` / `scene_name` | string | 场景标识与名称 |
| `difficulty` | string | 难度 |
| `situation` | string | 情境描述 |
| `goal` | string | 学习目标 |
| `expressions[]` | object[] | 实用表达，含 `en` / `zh` / `note` |
| `interactive_task` | string | 互动任务说明 |
| `notes[]` | string[] | 注意事项 |
| `common_mistakes[]` | string[] | 常见错误（❌ 错误 → ✅ 正确形式） |

## 4. action: interact

情境互动的单步推进（**无状态**：服务端不保存会话，多轮状态由调用方持有）。

- 输入（取开场语）：`{"action": "interact", "scene_id": "coffee_ordering"}`
- 输入（回答第 N 轮）：`{"action": "interact", "scene_id": "coffee_ordering",
  "answers_taken": ["<第 1 轮回答>", "…", "<第 N-1 轮回答>"], "user_input": "<第 N 轮回答>"}`

`answers_taken` 是**此前已完成的回答列表**（不含本轮）。服务端先重放该历史把对话还原到
正确轮次，再记录 `user_input` 并给出下一轮问题——因此**每次请求都必须带上完整历史**。

两轮调用示例（同一场景连续两次请求）：

```jsonc
// 第 1 轮：无历史，user_input 即本轮回答
{ "action": "interact", "scene_id": "coffee_ordering",
  "answers_taken": [], "user_input": "Hi, could I get a latte, please?" }
// 第 2 轮：把第 1 轮回答放入 answers_taken
{ "action": "interact", "scene_id": "coffee_ordering",
  "answers_taken": ["Hi, could I get a latte, please?"], "user_input": "Medium, please." }
```

响应载荷：

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | string | 对话对象（中文角色名） |
| `opening` | string | 开场白（仅首次请求，无 `answers_taken` 且无 `user_input` 时） |
| `ack` | string | 对用户回答的呼应语（作答时为字符串，取开场/恢复时为 null） |
| `prompt` | string\|null | 下一轮问题；为 null 表示互动结束 |
| `hint` | string\|null | 回答提示 |
| `closing` | string | 收场语（结束时） |
| `done` | boolean | 是否已结束 |
| `rounds` | integer | 已完成轮数（含 `answers_taken` 重放的轮数） |

> 提示：`answers_taken` 为空且 `user_input` 为空 → 返回开场白；
> `answers_taken` 非空但 `user_input` 为空 → 返回当前待作答的问题（用于恢复现场）。
> 如需一次性跑完整场，用 `run`。

## 5. action: feedback

表达反馈。

- 输入：`{"action": "feedback", "scene_id": "coffee_ordering", "answers": ["...", "..."]}`

响应载荷：

| 字段 | 类型 | 说明 |
|---|---|---|
| `answers[].answer` | string | 原始回答 |
| `answers[].issues[]` | object[] | `kind` 类别 / `quote` 原文 / `fix` 建议 / `reason` 原因 / `severity`（`issue` 问题，`suggestion` 建议） |
| `answers[].suppressed_count` | integer | 因「每轮最多 3 条」被截断、未展示的条数；>0 时应告知用户「另有 N 条未列出」 |
| `praises[]` | string[] | 用得好的地方 |
| `overall` | string | 总体结论；`answers` 全部为空白或非文本时明确说明「没有有效的英语回答记录」，**不给出肯定评价** |
| `limitations` | string | **能力局限声明（必须原样呈现给用户）** |

> 元素类型：`answers` 内的非字符串元素会被宽松转换为文本（`null` → `""`、`123` → `"123"`），
> 不会中断整次调用；转换后不含任何英文字母或汉字的条目**不计入「有效回答」**，
> 因此 `overall` 不会对这类输入输出「整体表达清晰」。
>
> **与「三类问题」（SKILL.md §4）的对应**：`kind` 是具体类型标签——拼写 / 大小写 / 冠词 /
> 语法·X 等对应①**错误**；`中式表达` / `用法` 等对应②**不自然**方向；`礼貌表达` 等对应
> ③**语境不当**方向；`severity=suggestion` 统一表示「建议」而非「判错」。
> 本地引擎仅覆盖可确定的规则类型，不做语义级判断。

## 6. action: transfer

迁移练习。

- 生成任务：`{"action": "transfer", "scene_id": "coffee_ordering"}`
- 校验尝试：`{"action": "transfer", "scene_id": "coffee_ordering", "attempt": "..."}`

响应载荷：生成时返回 `task`（`scenario` / `prompt` / `example` / `keywords`）；
校验时返回 `result`（`attempt` / `reused_keywords` / `note`）。

## 7. action: summary

按会话记录生成学习总结（不虚构未发生的环节）。

- 输入：`{"action": "summary", "scene_id": "coffee_ordering", "matched_kind": "strong", "answers": ["..."], "transfer_attempt": "..."}`

响应载荷：`sections[]`（`title` / `lines`）+ `closing_note`。

## 8. action: run（整条闭环，一步到位）

非交互式完成「学习任务 → 表达反馈 → 迁移练习 → 学习总结」，适合自动化演示与验收。

- 输入：

```json
{
  "action": "run",
  "scene_id": "coffee_ordering",
  "matched_kind": "strong",
  "answers": ["Hi, could I get a medium latte, please?", "For here, please."],
  "transfer_attempt": "Could I get a bubble tea with less sugar, please?"
}
```

- 响应载荷：`task` + `feedback` + `transfer` + `summary`（结构同上各节）。

## 9. action: version

返回技能版本：`{"action": "version"}` → `{"ok": true, "skill": "life2english", "version": "1.4.3"}`。

## 10. action: profile_export

合并本场会话为学习者档案并导出（**纯 JSON，由调用方保存；技能不做任何持久化**）。

- 输入：

```json
{
  "action": "profile_export",
  "scene_id": "coffee_ordering",
  "session_id": "s1",
  "date": "2026-10-15",
  "matched_kind": "strong",
  "answers": ["Hi, could I get a latte, please?"],
  "transfer_attempt": "Could I get a bubble tea, please?",
  "profile": null
}
```

- `profile`（可选）：上一次导出的档案 JSON；省略则新建档案。
  同一 `session_id` 再次合并会**替换**旧记录（幂等，不会重复计数）。
- `session_id` / `date`（可选）：由调用方提供；不提供时 `date` 为 `null`（**不虚构时间**）。
- `answers` / `transfer_attempt` 仅用于「使用检测」，**不会写入档案**（数据最小化）。

响应载荷：

| 字段 | 类型 | 说明 |
|---|---|---|
| `profile` | object | 更新后的完整档案（结构见下「档案 schema」） |
| `summary` | object | 摘要：会话数 / 表达数 / 三态分布 / 高频错误 / 场景列表 / 最近会话 |
| `note` | string | 保存责任说明（技能不做自动持久化，请调用方保存） |

## 11. action: profile_import

校验并读入外部档案（不合并、不保存）。

- 输入（二选一）：
  - `{"action": "profile_import", "profile_text": "<档案 JSON 字符串>"}`
  - `{"action": "profile_import", "profile": { … }}`
- 响应：`import_ok=true` 时附规范化后的 `profile` 与 `summary`；
  `import_ok=false` 时附 `errors[]`（可读的校验原因列表）——这属于**校验结果**，非系统错误；
  两个输入都缺失时返回 `ok=false`。

**档案 schema（1.0）**：

- 顶层：`schema_version` / `learner`（label、note）/ `sessions[]` / `items[]`；
- `sessions[]`（**唯一事实源**）：`session_id` / `date` / `scene_id` / `scene_name` /
  `matched_kind` / `rounds` / `expressions[]`（本场学过）/ `used_expressions[]`（检测到被使用）/
  `transferred_expressions[]`（检测到被迁移复用）/ `issues[]` / `transfer`；
- `items[]`（**派生视图**，由 `sessions` 重建；手工编辑不生效）：
  `expression` / `status` / `evidence[]`（`session_id` + `type`）；
- 三态掌握：`contacted`（接触过）→ `assisted`（提示下使用）→ `independent`（独立迁移使用），
  **单调升级**；判定为**近似**（内容词与句式骨架的复用检测），不等于语义级掌握评估。

## 错误处理

| 场景 | 响应 |
|---|---|
| 请求体为空 | `{"ok": false, "error": "缺少请求体..."}` |
| JSON 非法 | `{"ok": false, "error": "JSON 解析失败：..."}` |
| 未知 action | `{"ok": false, "error": "未知 action：...", "supported": [...]}` |
| 未知 scene_id | `{"ok": false, "error": "未知场景 scene_id：..."}` |
| 无法由 input 定位场景 | `{"ok": false, "error": "无法从句输入定位场景..."}` |

## 模块级 API（进程内调用）

除协议外，也可直接导入核心包：

```python
import sys; sys.path.insert(0, "scripts")
from life2english.store import SceneStore
from life2english.scenario import recognize
from life2english.session import LearningSession

store = SceneStore()
res = recognize("我想在咖啡店点单", store.all(), store.common_en_words)
session = LearningSession(store.get(res.scene_id), matched_kind=res.kind)
```
