"""学习总结：汇总本次会话的真实完成情况，不虚构成绩或完成度。

总结内容全部来自本次会话的实际记录（互动轮数、反馈结果、迁移尝试），
未完成的环节如实标注。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SummarySection:
    title: str
    lines: list[str] = field(default_factory=list)


@dataclass
class LearningSummary:
    sections: list[SummarySection] = field(default_factory=list)
    closing_note: str = "本总结基于本次会话实际记录生成，未虚构成绩或完成情况。"


def build_summary(session) -> LearningSummary:  # session: life2english.session.LearningSession
    """根据会话记录生成学习总结。"""
    scene = session.scene
    sections: list[SummarySection] = []

    # 1) 场景与目标
    match_label = {
        "strong": "完全匹配",
        "weak": "部分匹配（已确认）",
        "ambiguous": "并列歧义（已确认）",
        "picked": "兜底推荐选择",
    }.get(session.matched_kind, session.matched_kind)
    goal_lines = [
        f"场景：{scene['name']}（{match_label}）",
        f"学习目标：{session.task.goal}",
    ]
    sections.append(SummarySection(title="场景与目标", lines=goal_lines))

    # 2) 核心表达
    expr_lines = [f"{i + 1}. {e.en}" for i, e in enumerate(session.task.expressions)]
    sections.append(SummarySection(title=f"核心表达（{len(session.task.expressions)} 条）", lines=expr_lines))

    # 3) 实际完成情况
    done_lines: list[str] = [
        "场景识别：完成（%s）" % match_label,
        "学习任务：完成",
    ]
    rounds = session.dialogue.rounds
    if rounds > 0:
        done_lines.append(f"情境互动：完成 {rounds} 轮英语回答")
    else:
        done_lines.append("情境互动：未完成有效英语回答")

    if session.feedback_report is not None and rounds > 0:
        n = session.feedback_report.issue_count
        hard = session.feedback_report.hard_issue_count
        sug = session.feedback_report.suggestion_count
        if n == 0:
            done_lines.append("表达反馈：完成（未检测到问题）")
        elif hard and sug:
            done_lines.append(f"表达反馈：完成（{hard} 处明确问题、{sug} 条改进建议）")
        elif hard:
            done_lines.append(f"表达反馈：完成（检测到 {hard} 处明确问题）")
        else:
            done_lines.append(f"表达反馈：完成（未检测到错误，{sug} 条改进建议）")
    else:
        done_lines.append("表达反馈：未完成（无有效英语回答）")

    if session.transfer_skipped:
        done_lines.append("迁移练习：已跳过（未完成）")
    elif session.transfer_result is not None:
        done_lines.append("迁移练习：完成")
    else:
        done_lines.append("迁移练习：未进行")
    sections.append(SummarySection(title="实际完成情况", lines=done_lines))

    # 4) 需要注意
    attention: list[str] = []
    hard_lines: list[str] = []
    sug_lines: list[str] = []
    if session.feedback_report is not None:
        for ans in session.feedback_report.answers:
            for issue in ans.issues:
                line = f"{issue.quote} → {issue.fix}"
                if issue.severity == "issue":
                    if line not in hard_lines:
                        hard_lines.append(line)
                else:
                    if line not in sug_lines:
                        sug_lines.append(line)
    if hard_lines:
        attention.append("明确问题：" + "；".join(hard_lines))
    if sug_lines:
        attention.append("改进建议：" + "；".join(sug_lines))
    if session.transfer_result is not None and session.transfer_result.reused_keywords == [] and session.transfer_result.attempt:
        attention.append("迁移练习未检测到已学句式的复用，可对照示例句再练一次。")
    if not attention:
        attention = ["本次未检测到明显问题（本地规则范围内）。"]
    sections.append(SummarySection(title="需要注意", lines=attention))

    # 5) 下一步建议
    next_lines = [scene.get("next_steps", "继续保持练习。")]
    sections.append(SummarySection(title="下一步练习建议", lines=next_lines))

    return LearningSummary(sections=sections)
