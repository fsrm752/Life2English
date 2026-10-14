#!/usr/bin/env python3
"""Life2English · Skill 非交互式调用入口。

这是 Skill 的「程序级调用协议」实现：以 JSON 为输入输出，供智能体 / 上层程序
直接调用，无需交互式终端。交互式 CLI 见 scripts/life2english_cli.py。

调用方式（标准协议：stdin 传入 JSON 请求，stdout 返回 JSON 响应）：

    echo '{"action":"recognize","input":"我想在咖啡店点单"}' | python skill_api.py

或作为模块导入：

    from skill_api import handle
    resp = handle({"action": "task", "scene_id": "coffee_ordering"})

支持的动作（action）：
    list_scenes   列出全部支持的场景（含适用主题）
    recognize     场景识别（strong/weak/none/empty/invalid）
    task          生成学习任务（目标 + 实用表达 + 互动任务）
    interact      情境互动（返回开场问题；可用 user_input 逐步推进）
    feedback      表达反馈（传入回答列表，返回逐条反馈 + 局限声明）
    transfer      迁移练习（生成新场景任务 / 校验一次尝试）
    summary       生成学习总结（传入一次会话的完整记录）
    run           一次性完成整条闭环（非交互，适合自动化演示与验收）

所有输出均为 UTF-8 JSON；顶层字段 ok 表示是否成功，失败时 error 给出原因。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from life2english import feedback as feedback_mod          # noqa: E402
from life2english import scenario as scenario_mod          # noqa: E402
from life2english import summary as summary_mod            # noqa: E402
from life2english import taskgen                           # noqa: E402
from life2english import transfer as transfer_mod          # noqa: E402
from life2english.session import LearningSession           # noqa: E402
from life2english.store import SceneStore                  # noqa: E402

SKILL_VERSION = "1.4.3"

MATCH_LABELS = {
    "strong": "完全匹配",
    "weak": "部分匹配（已确认）",
    "ambiguous": "并列歧义（已确认）",
    "picked": "兜底推荐选择",
}


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------

def _expr_to_dict(e: taskgen.Expression) -> dict:
    return {"en": e.en, "zh": e.zh, "note": e.note}


def _task_to_dict(task: taskgen.LearningTask) -> dict:
    return {
        "scene_id": task.scene_id,
        "scene_name": task.scene_name,
        "difficulty": task.difficulty,
        "situation": task.situation,
        "goal": task.goal,
        "expressions": [_expr_to_dict(e) for e in task.expressions],
        "interactive_task": task.interactive_task,
        "notes": task.notes,
        "common_mistakes": task.common_mistakes,
    }


def _issue_to_dict(issue: feedback_mod.Issue) -> dict:
    return {
        "kind": issue.kind,
        "quote": issue.quote,
        "fix": issue.fix,
        "reason": issue.reason,
        "severity": issue.severity,
    }


# --- 字段安全转换 ---------------------------------------------------------
# 外部调用方（界面 / 智能体）可能传入非字符串类型；此处统一宽松处理，
# 避免退化成难以理解的「内部错误」，同时不改变正常字符串的行为。

def _as_text(value) -> str:
    """把请求字段转为文本：None → ''，非字符串按原值字符串化。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _as_text_list(value) -> list[str] | None:
    """把 answers 字段转为字符串列表；不是列表则返回 None（由调用方报错）。"""
    if value is None:
        return []
    if not isinstance(value, list):
        return None
    return [_as_text(v) for v in value]


# ---------------------------------------------------------------------------
# 各 action 的实现
# ---------------------------------------------------------------------------

def _act_list_scenes(store: SceneStore, _req: dict) -> dict:
    return {
        "scenes": [
            {
                "id": s["id"],
                "name": s["name"],
                "summary": s.get("summary", ""),
                "tags": s.get("tags", []),
                "difficulty": s.get("difficulty", ""),
                "example": s.get("trigger_example", ""),
            }
            for s in store.all()
        ]
    }


def _act_recognize(store: SceneStore, req: dict) -> dict:
    result = scenario_mod.recognize(
        _as_text(req.get("input")), store.all(), store.common_en_words
    )
    return {
        "kind": result.kind,
        "scene_id": result.scene_id,
        "scene_name": result.scene_name,
        "matched_keywords": result.matched_keywords,
        "ambiguous": result.ambiguous,
        "candidates": [
            {"scene_id": c.scene_id, "name": c.name, "reason": c.reason}
            for c in result.candidates
        ],
        "message": result.message,
    }


def _act_task(store: SceneStore, req: dict) -> dict:
    scene = _resolve_scene(store, req)
    task = taskgen.build_task(scene)
    return {"task": _task_to_dict(task)}


def _act_interact(store: SceneStore, req: dict) -> dict:
    """情境互动：保持无状态，由调用方通过 `answers_taken` 回传历史回答。

    - 无 `answers_taken` 且无 `user_input`：返回开场白（第一次调用）；
    - 带 `answers_taken`（此前已完成的回答列表）+ `user_input`：先重放历史把对话
      还原到正确轮次，再记录本轮回答并给出下一轮问题；
    - 带 `answers_taken` 但不带 `user_input`：返回当前待作答的问题（用于恢复现场）。
    """

    def _payload(step: dict | None, ack: str | None = None) -> dict:
        base = {"role": dlg.role_zh, "ack": ack, "rounds": dlg.rounds}
        if step is None:
            return {**base, "prompt": None, "hint": None,
                    "closing": dlg.closing, "done": True}
        return {**base, "prompt": step["prompt"], "hint": step.get("hint", ""),
                "done": False}

    scene = _resolve_scene(store, req)
    dlg = LearningSession(scene).dialogue

    history = _as_text_list(req.get("answers_taken"))
    if history is None:
        raise ValueError("answers_taken 必须是字符串数组，例如 [\"Hi, could I get a latte?\"]")
    for prev in history:
        dlg.record_answer(prev)
        dlg.next_step()

    user_input = _as_text(req.get("user_input")).strip()
    if not user_input:
        if not history:
            return {
                "role": dlg.role_zh,
                "opening": dlg.opening,
                "done": False,
                "rounds": dlg.rounds,
            }
        # 已重放历史但本轮未作答 → 返回当前待回答的问题
        step = dlg.current_step()
        if step is None:
            dlg.end()
        return _payload(step)

    ack = dlg.record_answer(user_input)
    step = dlg.next_step()
    if step is None:
        dlg.end()
    return _payload(step, ack=ack)


def _act_feedback(store: SceneStore, req: dict) -> dict:
    scene = _resolve_scene(store, req)
    answers = _as_text_list(req.get("answers"))
    if answers is None:
        raise ValueError("answers 必须是字符串数组，例如 [\"Hi, could I get a latte, please?\"]")
    report = feedback_mod.evaluate_answers(scene, answers)
    return {
        "answers": [
            {
                "answer": fb.answer,
                "issues": [_issue_to_dict(i) for i in fb.issues],
                # D-09：因「每轮最多 3 条」被截断而未展示的条数，透明化而非静默丢弃
                "suppressed_count": fb.suppressed_count,
            }
            for fb in report.answers
        ],
        "praises": report.praises,
        "overall": report.overall,
        "limitations": report.limitations,
    }


def _act_transfer(store: SceneStore, req: dict) -> dict:
    scene = _resolve_scene(store, req)
    if "attempt" in req:
        result = transfer_mod.check_attempt(scene, _as_text(req.get("attempt")))
        return {
            "result": {
                "attempt": result.attempt,
                "reused_keywords": result.reused_keywords,
                "note": result.note,
            }
        }
    task = transfer_mod.build_transfer(scene)
    return {
        "task": {
            "scenario": task.scenario,
            "prompt": task.prompt,
            "example": task.example,
            "keywords": task.keywords,
        }
    }


def _act_summary(store: SceneStore, req: dict) -> dict:
    """按传入的会话记录生成总结（不虚构未发生的环节）。"""
    scene = _resolve_scene(store, req)
    session = LearningSession(scene, matched_kind=req.get("matched_kind", "strong"))

    answers = _as_text_list(req.get("answers"))
    if answers is None:
        raise ValueError("answers 必须是字符串数组")
    for ans in answers:
        session.dialogue.record_answer(ans)
    if answers:
        session.finish_interaction()
    if "transfer_attempt" in req:
        session.submit_transfer(_as_text(req.get("transfer_attempt")) or None)

    summary = session.build_summary()
    return {
        "sections": [
            {"title": s.title, "lines": s.lines} for s in summary.sections
        ],
        "closing_note": summary.closing_note,
    }


def _act_run(store: SceneStore, req: dict) -> dict:
    """一次性走完整闭环（非交互，便于自动化演示与验收）。"""
    scene = _resolve_scene(store, req)
    session = LearningSession(scene, matched_kind=req.get("matched_kind", "strong"))

    answers = _as_text_list(req.get("answers"))
    if answers is None:
        raise ValueError("answers 必须是字符串数组")
    for ans in answers:
        session.dialogue.record_answer(ans)

    report = session.finish_interaction()
    session.make_transfer()
    session.submit_transfer(
        _as_text(req.get("transfer_attempt")) if "transfer_attempt" in req else None
    )
    summary = session.build_summary()

    return {
        "task": _task_to_dict(session.task),
        "feedback": {
            "answers": [
                {"answer": fb.answer, "issues": [_issue_to_dict(i) for i in fb.issues]}
                for fb in report.answers
            ],
            "praises": report.praises,
            "overall": report.overall,
            "limitations": report.limitations,
        },
        "transfer": {
            "task": {
                "scenario": session.transfer_task.scenario,
                "prompt": session.transfer_task.prompt,
                "example": session.transfer_task.example,
            },
            "result": (
                {
                    "reused_keywords": session.transfer_result.reused_keywords,
                    "note": session.transfer_result.note,
                }
                if session.transfer_result
                else {"skipped": session.transfer_skipped}
            ),
        },
        "summary": {
            "sections": [{"title": s.title, "lines": s.lines} for s in summary.sections],
            "closing_note": summary.closing_note,
        },
    }


# ---------------------------------------------------------------------------
# 分发
# ---------------------------------------------------------------------------

def _resolve_scene(store: SceneStore, req: dict) -> dict:
    """按 scene_id 取场景；缺省时用 input 做一次识别。"""
    scene_id = req.get("scene_id")
    if scene_id:
        scene = store.get(scene_id)
        if scene is None:
            raise ValueError(f"未知场景 scene_id：{scene_id}")
        return scene

    result = scenario_mod.recognize(
        _as_text(req.get("input")), store.all(), store.common_en_words
    )
    if result.scene_id is None:
        raise ValueError(
            f"无法从句输入定位场景（kind={result.kind}）：{result.message or '请提供 scene_id'}"
        )
    scene = store.get(result.scene_id)
    if scene is None:
        raise ValueError(f"识别的场景不存在：{result.scene_id}")
    return scene


ACTIONS = {
    "list_scenes": _act_list_scenes,
    "recognize": _act_recognize,
    "task": _act_task,
    "interact": _act_interact,
    "feedback": _act_feedback,
    "transfer": _act_transfer,
    "summary": _act_summary,
    "run": _act_run,
}


def handle(req: dict) -> dict:
    """处理一次 JSON 请求，返回 JSON 响应字典。

    对畸形请求（请求体非对象、action 缺失或类型错误、未知 action）一律返回
    结构化错误，不向上抛异常 —— 保证界面 / 智能体调用时始终能拿到可读原因。
    """
    if req is None:
        req = {}
    if not isinstance(req, dict):
        return {
            "ok": False,
            "error": f"请求体必须是 JSON 对象，收到：{type(req).__name__}",
            "supported": sorted(ACTIONS),
        }

    action = req.get("action", "")
    if not isinstance(action, str):
        return {
            "ok": False,
            "error": f"action 必须是字符串，收到：{type(action).__name__}",
            "supported": sorted(ACTIONS),
        }
    if action == "version":
        return {"ok": True, "skill": "life2english", "version": SKILL_VERSION}
    if action not in ACTIONS:
        return {
            "ok": False,
            "error": f"未知 action：{action or '(空)'}",
            "supported": sorted(ACTIONS),
        }

    store = SceneStore()
    try:
        payload = ACTIONS[action](store, req)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # 兜底：不向前端抛栈，返回可读原因
        return {"ok": False, "error": f"内部错误：{exc}"}
    return {"ok": True, "action": action, **payload}


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass

    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps(
            {"ok": False, "error": "缺少请求体，请通过 stdin 传入 JSON，例如 "
             '{"action":"list_scenes"}'},
            ensure_ascii=False,
        ))
        return
    try:
        req = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "error": f"JSON 解析失败：{exc}"}, ensure_ascii=False))
        return

    print(json.dumps(handle(req), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
