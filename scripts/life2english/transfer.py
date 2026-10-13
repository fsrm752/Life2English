"""迁移练习：生成与当前场景相关但不完全相同的新场景，检验表达迁移能力。

本地规则实现：检查用户在迁移场景中是否复用了本场景学过的句式关键词；
不做「对错」判定，只做复用情况提示（避免误判）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .feedback import has_chinese


@dataclass
class TransferTask:
    scenario: str
    prompt: str
    example: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class TransferResult:
    attempt: str
    reused_keywords: list[str] = field(default_factory=list)
    note: str = ""


def build_transfer(scene: dict) -> TransferTask:
    """生成迁移练习任务。"""
    t = scene["transfer"]
    return TransferTask(
        scenario=t["scenario"],
        prompt=t["prompt"],
        example=t["example"],
        keywords=list(t.get("keywords", [])),
    )


def check_attempt(scene: dict, attempt: str) -> TransferResult:
    """检查迁移练习的尝试，给出复用情况说明。"""
    attempt = (attempt or "").strip()
    keywords = list(scene["transfer"].get("keywords", []))
    low = attempt.lower()
    reused = [k for k in keywords if k.lower() in low]

    if not attempt:
        note = "本环节未作答。"
    elif has_chinese(attempt):
        note = "检测到中文回答：建议用英语再试一次，才能检验表达迁移效果。"
    elif reused:
        note = f"迁移成功：你在新场景里复用了学过的句式（{'、'.join(reused)}）。"
    else:
        note = "完成了一次自主表达。可以对照示例句，看看能否复用本场景学过的句式（如 Could I get ... / I'd like ...）。"

    return TransferResult(attempt=attempt, reused_keywords=reused, note=note)
