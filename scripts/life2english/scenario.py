"""场景识别：把用户的自然语言描述映射到已支持的场景模板。

本地规则实现（阶段一不调用外部模型）：
- 关键词命中计分：core 关键词命中计 3 分，extra 关键词命中计 1 分；
- 强匹配（最高分 >= 3）：直接进入学习任务；
- 弱匹配（0 < 最高分 < 3，即只命中扩展词）：必须经用户确认后才复用模板，
  避免「仅凭关键词相似硬套模板」；
- 无匹配（0 分）：明确告知暂不支持，推荐最接近的 2-3 个可用场景；
- 空输入 / 无法理解的输入：返回明确的提示类型，由调用方引导用户重试。

匹配结果类型（RecognitionResult.kind）：
    strong  — 完全匹配
    weak    — 部分匹配（待用户确认）
    none    — 无适用模板（附带推荐）
    empty   — 空输入
    invalid — 无法理解的输入
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CORE_WEIGHT = 3
EXTRA_WEIGHT = 1
STRONG_THRESHOLD = 3  # 最高分达到阈值视为强匹配

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_EN_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z']*")

# 意图线索 → 场景标签。用于「无匹配」时推荐最接近的场景。
INTENT_RULES: list[tuple[list[str], list[str]]] = [
    (["退卡", "退费", "办卡", "办理", "工作人员", "店员", "前台", "客服", "投诉", "咨询", "服务"], ["日常服务", "店员沟通"]),
    (["买", "购物", "超市", "商店", "衣服", "买单", "结账", "消费"], ["消费", "店员沟通"]),
    (["朋友", "认识", "社交", "聊天", "交流", "一起"], ["社交"]),
    (["上课", "课程", "老师", "同学", "作业", "考试", "学习"], ["校园"]),
    (["吃", "餐", "饭", "外卖", "食堂"], ["餐饮"]),
    (["玩", "娱乐", "游戏", "音乐", "剧", "演出"], ["娱乐"]),
    (["介绍", "说明", "展示", "分享", "讲讲"], ["介绍", "介绍自己"]),
]


@dataclass
class Candidate:
    """推荐/待确认场景候选。"""

    scene_id: str
    name: str
    reason: str


@dataclass
class RecognitionResult:
    """场景识别结果。"""

    kind: str  # strong | weak | none | empty | invalid
    scene_id: str | None = None
    scene_name: str | None = None
    matched_keywords: list[str] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    message: str = ""


def _has_meaningful_content(raw: str, common_en_words: set[str]) -> bool:
    """判断输入是否「可理解」：含中文字符，或至少含一个常见英语单词。

    「asdfghjkl」这类不含中文、也不含任何常见英文词的输入视为无法理解。
    """
    if _CJK_RE.search(raw):
        return True
    words = _EN_WORD_RE.findall(raw)
    if not words:
        return False
    return any(w.lower() in common_en_words for w in words)


def _score_scene(raw_low: str, scene: dict) -> tuple[int, list[str]]:
    """计算某个场景的命中分与命中关键词。"""
    hits: list[str] = []
    score = 0
    for kw in scene.get("core_keywords", []):
        if kw.lower() in raw_low:
            score += CORE_WEIGHT
            hits.append(kw)
    for kw in scene.get("extra_keywords", []):
        if kw.lower() in raw_low:
            score += EXTRA_WEIGHT
            hits.append(kw)
    return score, hits


def recommend(raw: str, scenes: list[dict], top_n: int = 3) -> list[Candidate]:
    """无匹配时推荐最接近的场景。

    规则：从输入中提取意图标签，与场景 tags 求交集，交集大者排前；
    并列或全零时按模板定义顺序补齐，保证始终给出可选择项。
    """
    input_tags: set[str] = set()
    for triggers, tags in INTENT_RULES:
        if any(t in raw for t in triggers):
            input_tags.update(tags)

    scored: list[tuple[int, int, dict, list[str]]] = []
    for order, scene in enumerate(scenes):
        common = sorted(input_tags & set(scene.get("tags", [])))
        scored.append((len(common), order, scene, common))

    scored.sort(key=lambda item: (-item[0], item[1]))

    candidates: list[Candidate] = []
    for overlap, _, scene, common in scored[:top_n]:
        if overlap > 0:
            reason = f"与你的描述接近（同属：{'、'.join(common)}）"
        else:
            reason = "当前支持的基础场景之一"
        candidates.append(Candidate(scene_id=scene["id"], name=scene["name"], reason=reason))
    return candidates


def recognize(
    text: str,
    scenes: list[dict],
    common_en_words: set[str] | None = None,
) -> RecognitionResult:
    """识别用户输入对应的场景。"""
    raw = (text or "").strip()
    if not raw:
        return RecognitionResult(kind="empty", message="输入为空，请描述一个生活场景。")

    if not _has_meaningful_content(raw, common_en_words or set()):
        return RecognitionResult(kind="invalid", message="无法理解该输入，请换一种描述方式。")

    raw_low = raw.lower()
    best_score = 0
    best_scene: dict | None = None
    best_hits: list[str] = []
    for scene in scenes:
        score, hits = _score_scene(raw_low, scene)
        if score > best_score:
            best_score = score
            best_scene = scene
            best_hits = hits

    if best_scene is not None and best_score >= STRONG_THRESHOLD:
        return RecognitionResult(
            kind="strong",
            scene_id=best_scene["id"],
            scene_name=best_scene["name"],
            matched_keywords=best_hits,
        )

    if best_scene is not None and best_score > 0:
        return RecognitionResult(
            kind="weak",
            scene_id=best_scene["id"],
            scene_name=best_scene["name"],
            matched_keywords=best_hits,
        )

    return RecognitionResult(
        kind="none",
        candidates=recommend(raw, scenes),
        message="暂不支持该具体场景。",
    )
