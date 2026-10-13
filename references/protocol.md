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
| `kind` | string | `strong` 完全匹配 / `weak` 部分匹配 / `none` 无匹配 / `empty` 空输入 / `invalid` 无法理解 |
| `scene_id` | string\|null | 命中场景 id（none/empty/invalid 时为 null） |
| `scene_name` | string\|null | 命中场景名 |
| `matched_keywords` | string[] | 命中的关键词 |
| `candidates[]` | object[] | `kind=none` 时的推荐列表，含 `scene_id` / `name` / `reason` |
| `message` | string | 提示信息 |

**调用方处理约定**：`strong` 直接进入学习；`weak` 必须先向用户确认再复用模板；
`none` 展示 `candidates` 让用户选择或重述；`empty` / `invalid` 提示后允许重试。

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

情境互动的单步推进（无状态：每次请求携带该轮输入）。

- 输入（取开场语）：`{"action": "interact", "scene_id": "coffee_ordering"}`
- 输入（回答一轮）：`{"action": "interact", "scene_id": "coffee_ordering", "user_input": "Hi, could I get a latte?"}`

响应载荷：

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | string | 对话对象（中文角色名） |
| `opening` | string | 开场白（仅首次请求） |
| `ack` | string | 对用户回答的呼应语 |
| `prompt` | string\|null | 下一轮问题；为 null 表示互动结束 |
| `hint` | string | 回答提示 |
| `closing` | string | 收场语（结束时） |
| `done` | boolean | 是否已结束 |
| `rounds` | integer | 已完成轮数 |

> 提示：多轮交互的连贯状态由调用方持有；如需一次性跑完整场，用 `run`。

## 5. action: feedback

表达反馈。

- 输入：`{"action": "feedback", "scene_id": "coffee_ordering", "answers": ["...", "..."]}`

响应载荷：

| 字段 | 类型 | 说明 |
|---|---|---|
| `answers[].answer` | string | 原始回答 |
| `answers[].issues[]` | object[] | `kind` 类别 / `quote` 原文 / `fix` 建议 / `reason` 原因 / `severity`（`issue` 问题，`suggestion` 建议） |
| `praises[]` | string[] | 用得好的地方 |
| `overall` | string | 总体结论 |
| `limitations` | string | **能力局限声明（必须原样呈现给用户）** |

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

返回技能版本：`{"action": "version"}` → `{"ok": true, "skill": "life2english", "version": "1.2.0"}`。

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
