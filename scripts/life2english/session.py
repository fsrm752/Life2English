"""学习会话编排：把各模块串联为「识别后」的完整学习闭环。

流程（对应任务书核心闭环）：
    学习任务生成 → 情境互动 → 表达反馈 → 迁移练习 → 学习总结
（场景识别由 scenario 模块完成，识别结果作为本会话的输入。）
"""

from __future__ import annotations

from . import dialogue as dialogue_mod
from . import feedback as feedback_mod
from . import summary as summary_mod
from . import taskgen
from . import transfer as transfer_mod

MATCH_LABELS = {"strong": "完全匹配", "weak": "部分匹配（已确认）", "picked": "兜底推荐选择"}


class LearningSession:
    """一次完整的学习会话（对应一个场景）。"""

    def __init__(self, scene: dict, matched_kind: str = "strong") -> None:
        self.scene = scene
        self.matched_kind = matched_kind
        self.task = taskgen.build_task(scene)
        self.dialogue = dialogue_mod.DialogueSession(scene)

        self.feedback_report: feedback_mod.FeedbackReport | None = None
        self.transfer_task: transfer_mod.TransferTask | None = None
        self.transfer_result: transfer_mod.TransferResult | None = None
        self.transfer_skipped = False
        self.summary: summary_mod.LearningSummary | None = None

    # -- 情境互动 -----------------------------------------------------------

    def finish_interaction(self) -> feedback_mod.FeedbackReport:
        """结束互动并生成表达反馈。"""
        self.feedback_report = feedback_mod.evaluate_answers(self.scene, self.dialogue.answers)
        return self.feedback_report

    # -- 迁移练习 -----------------------------------------------------------

    def make_transfer(self) -> transfer_mod.TransferTask:
        self.transfer_task = transfer_mod.build_transfer(self.scene)
        return self.transfer_task

    def submit_transfer(self, attempt: str | None) -> None:
        """提交迁移练习尝试；attempt 为 None 表示跳过。"""
        if attempt is None:
            self.transfer_skipped = True
            return
        self.transfer_result = transfer_mod.check_attempt(self.scene, attempt)

    # -- 总结 ---------------------------------------------------------------

    def build_summary(self) -> summary_mod.LearningSummary:
        self.summary = summary_mod.build_summary(self)
        return self.summary
