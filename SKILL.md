---
name: life2english
display_name: Life2English 生活场景英语
display_name_en: Life2English Scenario Coach
description: 生活场景驱动的英语学习技能。当用户想练习某个真实生活/校园场景下的英语表达（如咖啡店点单、食堂点餐、课堂提问、社团招新自我介绍、宿舍室友沟通、兼职面试、和外国同学聊电影、介绍大学生活），想模拟英语对话做情景练习，或想要针对日常场景表达的英语反馈与学习总结时，使用本技能完成「场景识别 → 学习任务 → 情境互动 → 表达反馈 → 迁移练习 → 学习总结」的完整学习闭环。
description_zh: 把一句真实生活/校园场景描述，变成一次完整的英语学习闭环：识别场景、生成学习任务、情景对话、表达反馈、迁移练习与学习总结。
description_en: Turn a real-life or campus scenario description into a complete English learning loop: scenario recognition, task generation, role-play dialogue, expression feedback, transfer practice, and a learning summary.
category: education
version: 1.2.0
author: Life2English
---

# Life2English · 生活场景驱动的英语学习

把「你想练习的那个场景」变成一次完整英语学习：**学表达 → 开口练 → 得反馈 → 做迁移 → 有总结**。

## 何时使用

- 用户描述了一个生活/校园场景，想练习该场景下的英语表达；
- 用户想模拟英语对话（角色扮演）并获得表达反馈；
- 用户想基于真实场景制定/完成一次英语口语练习与复盘。

## 支持的主题与场景（8 个）

| 主题 | 场景 | scene_id |
|---|---|---|
| 校园生活 | 介绍大学生活 | `campus_life` |
| 校园生活 | 宿舍生活与舍友沟通 | `dorm_life` |
| 校园生活 | 社团招新与自我介绍 | `club_recruitment` |
| 学习生活 | 课堂提问与答疑 | `class_question` |
| 生活助手 | 咖啡店点单 | `coffee_ordering` |
| 生活助手 | 食堂点餐与沟通 | `campus_canteen` |
| 生活助手 | 与外国同学讨论电影 | `movie_talk` |
| 实习就业 | 兼职面试与工作沟通 | `part_time_job` |

不在列表中的场景走**兜底流程**：明确告知暂不支持 → 推荐最接近的 2–3 个场景 → 由用户选择或重新描述（不做关键词硬套）。

## 三种调用方式

### 1. 可视化界面（推荐用于演示）

```bash
python scripts/web_server.py            # 默认 http://127.0.0.1:8770，自动打开浏览器
```

Windows 可直接双击项目根目录的 `启动演示界面.bat`。
界面从上到下为 ①描述场景 → ②学习任务 → ③情境互动 → ④表达反馈 → ⑤迁移练习 → ⑥学习总结，
侧栏列出全部支持的场景。

> 界面**只调用协议层**（`skill_api.py`），不含任何业务逻辑实现；
> 界面、命令行、智能体三条入口共用同一套逻辑。

### 2. 交互式（面向学习者）

```bash
python scripts/life2english_cli.py    # 等价入口：python main.py
```

按提示完成：主菜单 `1` 开始 → 描述场景 → 学习任务 → 情境互动（英语回答，`done` 提前结束，
`重答` 撤回上一条）→ 表达反馈 → 迁移练习（`跳过` 可略过）→ 学习总结。

### 3. 非交互式协议（面向智能体 / 程序）

以 JSON 进 JSON 出，见 [@references/protocol.md](references/protocol.md)：

```bash
echo '{"action":"recognize","input":"我想在咖啡店点单"}' | python scripts/skill_api.py
echo '{"action":"run","scene_id":"campus_canteen","answers":["Could I get a set meal, please?"]}' \
  | python scripts/skill_api.py
```

支持的 action：`list_scenes` / `recognize` / `task` / `interact` / `feedback` / `transfer` / `summary` / `run` / `version`。

## 输出结构（固定六段）

1. **场景识别结果**：匹配类型（完全/部分/兜底推荐）+ 场景名；
2. **学习任务**：情境、学习目标、5 条实用表达（英文例句 + 中文释义 + 用法提示）、互动任务、注意事项、常见错误；
3. **情境互动**：系统扮演交流对象的多轮问答（每轮问题 + 回答提示）；
4. **表达反馈**：逐句反馈（类别 → 原文 → 建议 → 原因）+ 做得好的地方 + 总体结论 + **能力局限声明**；
5. **迁移练习**：新场景 + 任务提示 + 示例 + 复用情况检查；
6. **学习总结**：场景与目标 / 核心表达 / 实际完成情况 / 需要注意 / 下一步建议。

## 能力边界（必须如实告知用户）

- **本地模拟实现**：使用预设场景模板 + 本地规则，**不调用外部 API、不产生费用、不需要密钥**；
- 表达反馈覆盖拼写、大小写、a/an、主谓一致、名词数、词性、时态提示、常见中式表达与搭配等**有限类型**（问题与建议分级展示）；语义通顺度、复杂语法、地道性**无法可靠判断**，界面中同步声明，不得夸大；
- 情境互动的对话应答为**模板化**，不是真实 AI 对话；
- 仅支持上文 8 个场景，其余走兜底推荐；
- 已为将来接入真实语言模型预留接口 `scripts/life2english/model_api.py`（默认纯本地）。

## 参考与模板

- [@references/protocol.md](references/protocol.md) —— 输入输出协议（JSON 字段级说明）
- [@references/scenarios.md](references/scenarios.md) —— 场景模板库总览（关键词、表达、对话结构）
- [@templates/learning_task.md](templates/learning_task.md) —— 学习任务输出模板
