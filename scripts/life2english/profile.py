"""学习者档案：数据结构、三态掌握判定与导出 / 导入（改进任务书 · 阶段 D）。

设计原则（对齐任务书 §D 与审计报告）：
- **不做任何文件读写**：档案是纯 JSON 结构，由调用方持有 / 传递；
  技能不自动保存任何数据、不虚构保存成功（运行环境不保证持久化能力）。
- **数据最小化**：档案只保存学习表现数据（表达清单、问题类型与片段、
  迁移复用记录），**不保存完整对话原文**（answers 仅在合并当次用于检测，随即丢弃）。
- **三态掌握**（单调升级，不回退）：
    contacted   接触过——本场任务展示 / 学过该表达；
    assisted    提示下能使用——会话内（受提示后）实际用过（近判定，见下）；
    independent 独立迁移使用——在新场景迁移练习中复用（近判定，见下）。
- **轨 B 判定能力有限（如实声明）**：「使用」检测基于**内容词复用**的近似规则，
  不等于语义级掌握评估；检测不到的复杂复用会记为「未使用」。

档案结构（schema v1）::

    {
      "schema_version": "1.0",
      "learner": {"label": null, "note": null},
      "sessions": [
        {"session_id": "s1", "date": null, "scene_id": "...", "scene_name": "...",
         "matched_kind": "strong", "rounds": 4,
         "expressions": ["本场学过的表达"],
         "used_expressions": ["本场检测到被使用的表达"],
         "transferred_expressions": ["迁移中检测到被复用的表达"],
         "issues": [{"kind": "...", "quote": "...", "fix": "...", "severity": "..."}],
         "transfer": {"attempted": true, "reused_keywords": ["..."]}}
      ],
      "items": [
        {"expression": "...", "status": "assisted",
         "evidence": [{"session_id": "s1", "type": "introduced"}]}
      ]
    }

``sessions`` 是**唯一事实源**；``items`` 为派生视图（由 ``rebuild_items`` 重建），
外部修改 items 不会生效——请通过追加会话来更新档案。
"""

from __future__ import annotations

import json
import re
from copy import deepcopy

SCHEMA_VERSION = "1.0"

_STATUS_ORDER = {"contacted": 0, "assisted": 1, "independent": 2}

# 复用检测的停用词：只保留「内容词」参与命中，常见功能词不参与。
_STOPWORDS = {
    # 代词 / 限定词
    "i", "me", "my", "mine", "you", "your", "yours", "we", "our", "ours",
    "he", "him", "his", "she", "her", "hers", "it", "its", "they", "them",
    "their", "theirs", "this", "that", "these", "those", "some", "any",
    "a", "an", "the", "one", "another", "every", "each",
    # 助动词 / 情态 / 高频轻动词
    "am", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "done", "have", "has", "had",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",
    "get", "got", "like", "want", "need", "let", "make", "take", "give",
    "go", "going", "come", "say", "tell", "know", "think",
    # 介词 / 连词 / 副词 / 语气词
    "to", "of", "in", "on", "at", "for", "with", "without", "and", "or",
    "but", "if", "so", "as", "by", "from", "up", "down", "out", "off",
    "about", "into", "over", "under", "again", "then", "than", "too",
    "very", "just", "now", "here", "there", "when", "where", "why", "how",
    "what", "which", "who", "whom", "whose", "not", "no", "yes", "ok", "okay",
    "please", "thanks", "thank", "hello", "hi", "sure",
}

_WORD_RE = re.compile(r"[a-z]+")


# ---------------------------------------------------------------------------
# 档案构造
# ---------------------------------------------------------------------------

def new_profile(learner_label: str | None = None, learner_note: str | None = None) -> dict:
    """新建空档案。"""
    return {
        "schema_version": SCHEMA_VERSION,
        "learner": {"label": learner_label, "note": learner_note},
        "sessions": [],
        "items": [],
    }


def _keywords(expression: str) -> list[str]:
    """提取表达的内容词（小写；去 <3 字母词与停用词；保持出现顺序、去重）。"""
    out: list[str] = []
    for w in _WORD_RE.findall((expression or "").lower()):
        if len(w) < 3 or w in _STOPWORDS or w in out:
            continue
        out.append(w)
    return out


def _trigrams(words: list[str]) -> set[tuple[str, str, str]]:
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}


def detect_usage(expressions: list[str], text: str) -> list[str]:
    """从一段文本中检测哪些表达被「复用」（近似判定，双通道）。

    通道 1 · 内容词：表达提取内容词（去停用词 / 短词）后，
    命中数 ≥ max(1, 向上取整(词数/2)) 视为复用；
    通道 2 · 句式骨架：文本与表达共享 ≥1 个**连续三词片段**（如 ``could i get``）
    视为复用——用于捕捉「换内容词、保句式」的迁移复用。

    两通道任一命中即判定为使用。轨 B 的判定为近似：无法区分「复用所学句式」
    与「学习者本来就会的通用结构」，复杂改写可能检测不到（如实声明）。
    """
    if not text or not expressions:
        return []
    words = _WORD_RE.findall(str(text).lower())
    wordset = set(words)
    tris = _trigrams(words)

    used: list[str] = []
    for expr in expressions:
        kws = _keywords(expr)
        content_ok = False
        if kws:
            need = 1 if len(kws) <= 2 else (len(kws) + 1) // 2
            hits = sum(1 for k in kws if k in wordset)
            content_ok = hits >= need
        expr_words = _WORD_RE.findall((expr or "").lower())
        trigram_ok = bool(tris & _trigrams(expr_words))
        if content_ok or trigram_ok:
            used.append(expr)
    return used


# ---------------------------------------------------------------------------
# 合并会话 / 派生重建
# ---------------------------------------------------------------------------

def _clean_issue(issue) -> dict | None:
    if not isinstance(issue, dict):
        return None
    return {
        "kind": str(issue.get("kind", "")),
        "quote": str(issue.get("quote", "")),
        "fix": str(issue.get("fix", "")),
        "severity": str(issue.get("severity", "issue")),
    }


def _clean_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, str) or isinstance(v, (int, float))]


def apply_session(profile: dict | None, session: dict) -> dict:
    """把一场会话合并进档案，返回**新档案**（不修改入参）。

    `session` 必填 `scene_id`（str）；可选：`session_id` / `date` / `scene_name` /
    `matched_kind` / `rounds` / `expressions` / `issues` / `transfer` /
    `answers` / `transfer_attempt`。

    `answers` 与 `transfer_attempt` 仅用于当次「使用检测」，**不会写入档案**。
    同一 `session_id` 再次合并会替换旧记录（幂等：派生数据随重建保持一致）。

    检测范围 = 本场表达 + 档案中已有表达（**复习检测**：后续会话中再次使用
    历史表达，也会为其追加证据——即「复习结果」的记录方式）。
    """
    if profile is not None:
        ok, errors = validate_profile(profile)
        if not ok:
            raise ValueError("profile 校验失败：" + "；".join(errors))
        base = normalize_profile(profile)
    else:
        base = new_profile()

    if not isinstance(session, dict):
        raise ValueError("session 必须是 JSON 对象")
    scene_id = session.get("scene_id")
    if not isinstance(scene_id, str) or not scene_id.strip():
        raise ValueError("session.scene_id 必须是字符串，例如 \"coffee_ordering\"")

    expressions = [e for e in _clean_str_list(session.get("expressions")) if e.strip()]
    issues = [i for i in (_clean_issue(x) for x in (session.get("issues") or [])) if i]
    transfer_in = session.get("transfer") if isinstance(session.get("transfer"), dict) else {}

    answers_text = " ".join(_clean_str_list(session.get("answers")))
    transfer_attempt = session.get("transfer_attempt")
    transfer_attempt = transfer_attempt if isinstance(transfer_attempt, str) else ""

    # 检测目标 = 本场表达 + 档案中已有表达（复习检测）
    history = [
        it.get("expression")
        for it in (base.get("items") or [])
        if isinstance(it, dict) and isinstance(it.get("expression"), str)
    ]
    targets = expressions + [e for e in history if e and e not in expressions]

    used = detect_usage(targets, answers_text)
    transferred = detect_usage(targets, transfer_attempt) if transfer_attempt.strip() else []

    sid = session.get("session_id")
    if not isinstance(sid, str) or not sid.strip():
        sid = f"s{len(base['sessions']) + 1}"

    rounds = session.get("rounds")
    if not isinstance(rounds, int):
        rounds = len(_clean_str_list(session.get("answers")))

    record = {
        "session_id": sid,
        "date": session.get("date") if isinstance(session.get("date"), str) else None,
        "scene_id": scene_id,
        "scene_name": session.get("scene_name") if isinstance(session.get("scene_name"), str) else "",
        "matched_kind": session.get("matched_kind") if isinstance(session.get("matched_kind"), str) else "",
        "rounds": rounds,
        "expressions": expressions,
        "used_expressions": used,
        "transferred_expressions": transferred,
        "issues": issues,
        "transfer": {
            "attempted": bool(transfer_attempt.strip()),
            "reused_keywords": _clean_str_list(transfer_in.get("reused_keywords")),
        },
    }

    base["sessions"] = [s for s in base["sessions"] if s.get("session_id") != sid]
    base["sessions"].append(record)
    base["items"] = rebuild_items(base["sessions"])
    return base


def rebuild_items(sessions: list[dict]) -> list[dict]:
    """由会话记录重建表达项（sessions 为唯一事实源，items 为派生视图）。"""
    order: list[str] = []
    evidence: dict[str, list[dict]] = {}

    def add(expr: str, type_: str, sid: str) -> None:
        if not expr:
            return
        if expr not in evidence:
            order.append(expr)
            evidence[expr] = []
        rec = {"session_id": sid, "type": type_}
        if rec not in evidence[expr]:
            evidence[expr].append(rec)

    for s in sessions:
        if not isinstance(s, dict):
            continue
        sid = s.get("session_id", "")
        for e in _clean_str_list(s.get("expressions")):
            add(e, "introduced", sid)
        for e in _clean_str_list(s.get("used_expressions")):
            add(e, "used", sid)
        for e in _clean_str_list(s.get("transferred_expressions")):
            add(e, "transfer", sid)

    items: list[dict] = []
    for expr in order:
        types = {r["type"] for r in evidence[expr]}
        status = "contacted"
        if "used" in types:
            status = "assisted"
        if "transfer" in types:
            status = "independent"
        items.append({"expression": expr, "status": status, "evidence": evidence[expr]})
    return items


# ---------------------------------------------------------------------------
# 校验 / 规范化 / 导入导出
# ---------------------------------------------------------------------------

def validate_profile(obj) -> tuple[bool, list[str]]:
    """校验档案结构；返回 (是否通过, 错误列表)。宽松读取：未知字段不报错。"""
    errors: list[str] = []
    if not isinstance(obj, dict):
        return False, ["profile 必须是 JSON 对象"]

    ver = obj.get("schema_version")
    if not isinstance(ver, str) or not ver.strip():
        errors.append("缺少 schema_version")
    elif ver.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        errors.append(
            f"不支持的 schema 主版本：{ver}"
            f"（本实现支持 {SCHEMA_VERSION.split('.')[0]}.x）"
        )

    learner = obj.get("learner")
    if learner is not None and not isinstance(learner, dict):
        errors.append("learner 必须是对象或 null")

    sessions = obj.get("sessions")
    if sessions is not None:
        if not isinstance(sessions, list):
            errors.append("sessions 必须是数组")
        else:
            for idx, s in enumerate(sessions):
                if not isinstance(s, dict):
                    errors.append(f"sessions[{idx}] 必须是对象")
                    continue
                sid = s.get("session_id")
                if not isinstance(sid, str) or not sid.strip():
                    errors.append(f"sessions[{idx}].session_id 缺失或非字符串")

    items = obj.get("items")
    if items is not None and not isinstance(items, list):
        errors.append("items 必须是数组")

    return (not errors), errors


def normalize_profile(obj) -> dict:
    """补默认字段并重建派生数据（items）；不修改已存的会话数据。

    注意：``items`` 会以 ``sessions`` 为准**整体重建**——手工编辑 items 不会生效，
    请通过追加会话来更新档案。
    """
    if obj is None:
        return new_profile()
    if not isinstance(obj, dict):
        raise ValueError("profile 必须是 JSON 对象")

    p = deepcopy(obj)
    p["schema_version"] = SCHEMA_VERSION

    learner = p.get("learner")
    if not isinstance(learner, dict):
        learner = {}
    learner.setdefault("label", None)
    learner.setdefault("note", None)
    p["learner"] = learner

    sessions_in = p.get("sessions")
    if not isinstance(sessions_in, list):
        sessions_in = []

    sessions: list[dict] = []
    for s in sessions_in:
        if not isinstance(s, dict):
            continue
        s = deepcopy(s)
        if not isinstance(s.get("session_id"), str) or not s["session_id"].strip():
            s["session_id"] = f"s{len(sessions) + 1}"
        s.setdefault("date", None)
        s.setdefault("scene_id", "")
        s.setdefault("scene_name", "")
        s.setdefault("matched_kind", "")
        if not isinstance(s.get("rounds"), int):
            s["rounds"] = 0
        s["expressions"] = [e for e in _clean_str_list(s.get("expressions")) if e.strip()]
        s["used_expressions"] = _clean_str_list(s.get("used_expressions"))
        s["transferred_expressions"] = _clean_str_list(s.get("transferred_expressions"))
        s["issues"] = [i for i in (_clean_issue(x) for x in (s.get("issues") or [])) if i]
        transfer = s.get("transfer") if isinstance(s.get("transfer"), dict) else {}
        s["transfer"] = {
            "attempted": bool(transfer.get("attempted")),
            "reused_keywords": _clean_str_list(transfer.get("reused_keywords")),
        }
        sessions.append(s)

    p["sessions"] = sessions
    p["items"] = rebuild_items(sessions)
    return p


def import_text(text: str) -> tuple[dict | None, list[str]]:
    """从 JSON 文本导入档案：解析 → 校验 → 规范化。

    返回 ``(档案, 错误列表)``；失败时档案为 ``None``、错误列表非空。
    """
    if not isinstance(text, str) or not text.strip():
        return None, ["导入内容为空"]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [f"JSON 解析失败：{exc}"]
    ok, errors = validate_profile(obj)
    if not ok:
        return None, errors
    return normalize_profile(obj), []


def export_json(profile: dict) -> str:
    """序列化为可保存 / 可复制的 JSON 文本（UTF-8，中文不转义，缩进 2）。"""
    return json.dumps(profile, ensure_ascii=False, indent=2)


def summarize(profile: dict) -> dict:
    """生成人类可读的档案摘要（不含对话原文）。"""
    sessions = profile.get("sessions", []) if isinstance(profile, dict) else []
    items = profile.get("items", []) if isinstance(profile, dict) else []

    by_status = {"contacted": 0, "assisted": 0, "independent": 0}
    for it in items:
        st = it.get("status") if isinstance(it, dict) else None
        if st in by_status:
            by_status[st] += 1

    counts: dict[str, int] = {}
    for s in sessions:
        for i in s.get("issues", []):
            k = i.get("kind") if isinstance(i, dict) else None
            if k:
                counts[k] = counts.get(k, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

    scenes: list[str] = []
    for s in sessions:
        sid = s.get("scene_id")
        if sid and sid not in scenes:
            scenes.append(sid)

    last = sessions[-1] if sessions else None
    return {
        "sessions_count": len(sessions),
        "expressions_total": len(items),
        "by_status": by_status,
        "top_error_kinds": [{"kind": k, "count": c} for k, c in top],
        "scenes": scenes,
        "last_session": (
            {
                "session_id": last.get("session_id"),
                "scene_id": last.get("scene_id"),
                "date": last.get("date"),
            }
            if last
            else None
        ),
    }
