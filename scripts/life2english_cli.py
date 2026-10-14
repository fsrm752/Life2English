#!/usr/bin/env python3
"""Life2English 命令行入口：生活场景驱动的英语学习 Skill。

运行方式：
    python main.py

一次学习会话的完整流程：
    描述场景 → 场景识别 → 学习任务 → 情境互动 → 表达反馈 → 迁移练习 → 学习总结

阶段一为本地模拟版本（本地规则 + 预设模板），不调用外部 API、不产生费用。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许从项目根目录直接运行（python main.py）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from life2english.scenario import recognize                        # noqa: E402
from life2english.session import LearningSession                    # noqa: E402
from life2english.store import SceneStore                           # noqa: E402

RULE = "━" * 62
THIN_RULE = "-" * 62

QUIT_WORDS = {"退出", "返回", "quit", "exit", "q", "退出程序", "退出学习"}
DONE_WORDS = {"done", "结束", "完成", "end", "退出练习", "不练了", "先不练了"}
SKIP_WORDS = {"跳过", "skip", "略过", "pass"}
REDO_WORDS = {"重答", "重新回答", "重答一次", "redo", "retry", "再答一次"}


def _setup_encoding() -> None:
    """Windows 控制台 / 管道模式下强制 UTF-8 输入输出。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass
    if sys.stdin:
        try:
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass


def read_input(prompt: str) -> str | None:
    """读取一行输入；EOF / Ctrl+C 返回 None（视为退出信号）。"""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def _shorten(text: str, limit: int = 40) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


# ---------------------------------------------------------------------------
# 各环节渲染
# ---------------------------------------------------------------------------

def show_banner(store: SceneStore) -> None:
    print(RULE)
    print("  Life2English · 生活场景驱动的英语学习")
    print(RULE)
    print("本地模拟版本：使用预设场景模板与本地规则，不调用外部 API，不产生费用。")
    print("支持场景：" + " / ".join(store.names()))
    print(RULE)


def show_task(session: LearningSession) -> None:
    task = session.task
    print()
    print(RULE)
    print(f"  学习任务 · {task.scene_name}" + (f"（难度：{task.difficulty}）" if task.difficulty else ""))
    print(RULE)
    if task.situation:
        print("【情境】")
        print(f"  {task.situation}")
        print()
    print("【学习目标】")
    print(f"  {task.goal}")
    print()
    print(f"【实用表达】（{len(task.expressions)} 条）")
    for i, expr in enumerate(task.expressions, 1):
        print(f"  {i}. {expr.en}")
        print(f"     {expr.zh}")
        if expr.note:
            print(f"     · {expr.note}")
    print()
    print("【互动任务】")
    print(f"  {task.interactive_task}")
    if task.notes:
        print()
        print("【注意事项】")
        for note in task.notes:
            print(f"  · {note}")
    if task.common_mistakes:
        print()
        print("【常见错误】")
        for m in task.common_mistakes:
            print(f"  · {m}")


def run_interaction(session: LearningSession) -> None:
    dlg = session.dialogue
    print()
    print(RULE)
    print("  情境互动")
    print(RULE)
    print(f"现在我是「{dlg.role_zh}」。请用英语和我对话。")
    print("（输入 done/结束 可提前结束；输入 重答 可撤回上一次回答重说）")
    print()
    print(f"{dlg.role_zh}：{dlg.opening}")

    last_prompt = dlg.opening
    while True:
        line = read_input("\n你 > ")
        if line is None:
            dlg.end()
            break
        text = line.strip()
        if text.lower() in DONE_WORDS:
            print("（已结束互动练习）")
            dlg.end()
            break
        if text.lower() in REDO_WORDS:
            if dlg.retract_last():
                print(f"（已撤回上一次回答，请重新回答）")
                print(f"{dlg.role_zh}：{last_prompt}")
            else:
                print("（还没有可撤回的回答，请直接作答）")
            continue
        if not text:
            print("（没有输入内容：请用英语回答，或输入 done 结束练习）")
            continue

        ack = dlg.record_answer(text)
        step = dlg.next_step()
        print(f"{dlg.role_zh}：{ack}")
        if step is None:
            dlg.end()
            break
        print(f"{dlg.role_zh}：{step['prompt']}")
        last_prompt = step["prompt"]
        hint = step.get("hint")
        if hint:
            print(f"（提示：{hint}）")

    print()
    print(f"{dlg.role_zh}：{dlg.closing}")


def show_feedback(session: LearningSession) -> None:
    report = session.feedback_report
    print()
    print(RULE)
    print("  表达反馈")
    print(RULE)
    if report is None:
        print("  未进行反馈（本环节未执行）。")
        return
    print("（[问题] = 明确错误；[建议] = 让表达更自然的可选改进）")
    print()
    for i, fb in enumerate(report.answers, 1):
        print(f'【回答 {i}】"{fb.answer}"')
        if not fb.issues:
            print("  · 未检测到问题（本地规则范围内）。")
        for issue in fb.issues:
            if issue.severity == "suggestion":
                tag = f"建议·{issue.kind}"
            else:
                tag = f"问题·{issue.kind}"
            print(f"  · [{tag}] {issue.quote} → {issue.fix}")
            print(f"    —— {issue.reason}")
        print()
    if report.praises:
        print("【做得好】")
        for p in report.praises:
            print(f"  · {p}")
        print()
    print(f"【总体】{report.overall}")
    print(f"【局限说明】{report.limitations}")


def run_transfer(session: LearningSession) -> None:
    task = session.make_transfer()
    print()
    print(RULE)
    print("  迁移练习")
    print(RULE)
    print(f"【新场景】{task.scenario}")
    print(f"  {task.prompt}")
    print(f"  （示例：{task.example}）")
    print("  （输入「跳过」可跳过本环节）")

    line = read_input("\n你 > ")
    if line is None:
        session.submit_transfer(None)
        return
    text = line.strip()
    if text.lower() in SKIP_WORDS:
        session.submit_transfer(None)
        print("→ 已跳过迁移练习（本环节记为未完成）。")
        return
    session.submit_transfer(text)
    result = session.transfer_result
    if result:
        print(f"→ {result.note}")


def show_summary(session: LearningSession) -> None:
    summary = session.build_summary()
    print()
    print(RULE)
    print("  学习总结")
    print(RULE)
    for section in summary.sections:
        print(f"【{section.title}】")
        for line in section.lines:
            print(f"  - {line}")
        print()
    print(summary.closing_note)


# ---------------------------------------------------------------------------
# 单次学习会话
# ---------------------------------------------------------------------------

def run_once(store: SceneStore) -> None:
    """识别场景并完成一次完整学习闭环。"""
    scene: dict | None = None
    matched_kind = "strong"

    # ---- 场景输入与识别 ----
    while scene is None:
        text = read_input("\n请用一句话描述你想练习的生活场景（例如：我想在咖啡店点单；输入 退出 返回主菜单）\n> ")
        if text is None:
            return
        raw = text.strip()
        if raw.lower() in QUIT_WORDS:
            return

        result = recognize(raw, store.all(), store.common_en_words)

        if result.kind == "strong":
            scene = store.get(result.scene_id)
            matched_kind = "strong"
            print(f"\n>>> 已识别场景：「{result.scene_name}」（完全匹配）")

        elif result.kind == "weak":
            print(f"\n>>> 你的描述可能与「{result.scene_name}」相关（只匹配到部分关键词）。")
            confirm = read_input(f"    是否用它开始练习？[y] 开始 / [n] 重新描述 / [退出] 返回主菜单 > ")
            if confirm is None:
                return
            c = confirm.strip().lower()
            if c in {"y", "yes", "是", "确认", "开始"}:
                scene = store.get(result.scene_id)
                matched_kind = "weak"
                print(f">>> 好的，开始练习「{result.scene_name}」。")
            elif c in QUIT_WORDS:
                return
            else:
                print(">>> 请重新描述你的场景。")

        elif result.kind == "ambiguous":
            print("\n>>> 你的描述可能同时指向多个场景，请确认想练哪一个：")
            for i, cand in enumerate(result.candidates, 1):
                print(f"      {i}) {cand.name} —— {cand.reason}")
            choice = read_input(
                "    输入编号选择场景；或输入「重试」重新描述、「退出」返回主菜单 > "
            )
            if choice is None:
                return
            c = choice.strip().lower()
            if c in QUIT_WORDS:
                return
            if c in {"重试", "重新描述", "retry", "r"}:
                print(">>> 好的，请重新描述你的场景。")
                continue
            if c.isdigit() and 1 <= int(c) <= len(result.candidates):
                selected = result.candidates[int(c) - 1]
                scene = store.get(selected.scene_id)
                matched_kind = "ambiguous"
                print(f">>> 好的，开始练习「{selected.name}」。")
            else:
                print(">>> 输入无效，请重新描述你的场景。")

        elif result.kind == "none":
            print(f"\n>>> 暂不支持「{_shorten(raw)}」这个具体场景。")
            print("    目前可以练习的最接近场景：")
            for i, cand in enumerate(result.candidates, 1):
                print(f"      {i}) {cand.name} —— {cand.reason}")
            choice = read_input(
                "    输入编号选择场景练习；或输入「重试」重新描述、「退出」返回主菜单 > "
            )
            if choice is None:
                return
            c = choice.strip().lower()
            if c in QUIT_WORDS:
                return
            if c in {"重试", "重新描述", "retry", "r"}:
                print(">>> 好的，请重新描述你的场景。")
                continue
            if c.isdigit() and 1 <= int(c) <= len(result.candidates):
                selected = result.candidates[int(c) - 1]
                scene = store.get(selected.scene_id)
                matched_kind = "picked"
                print(f">>> 好的，开始练习「{selected.name}」。")
            else:
                print(">>> 输入无效，请重新描述你的场景。")

        elif result.kind == "empty":
            print("\n>>> 输入是空的。请描述一个生活场景（例如：我想在咖啡店点单）。")

        else:  # invalid
            print("\n>>> 抱歉，我没有理解这个描述。")
            print("    请用一句中文或英文描述你的生活场景（例如：我想在咖啡店点单）。")

    # ---- 完整学习闭环 ----
    assert scene is not None
    session = LearningSession(scene, matched_kind=matched_kind)
    show_task(session)
    run_interaction(session)
    session.finish_interaction()
    show_feedback(session)
    run_transfer(session)
    show_summary(session)

    read_input("\n（回车返回主菜单）")


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------

def main() -> None:
    _setup_encoding()
    store = SceneStore()
    show_banner(store)

    while True:
        choice = read_input("\n主菜单：[1] 开始学习  [2] 退出\n> ")
        if choice is None:
            break
        c = choice.strip().lower()
        if c == "1":
            run_once(store)
        elif c in {"2"} | QUIT_WORDS:
            break
        else:
            print("请输入 1 或 2。")

    print("\n感谢使用 Life2English，再见！")


if __name__ == "__main__":
    main()
