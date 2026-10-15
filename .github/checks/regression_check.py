#!/usr/bin/env python3
"""发布侧程序回归测试（GitHub Actions 调用）。

与 package_check.py 分工互补：
  - package_check.py —— 静态结构检查 + 最小协议冒烟（frontmatter / 引用 / 数据完整性 / 编译）；
  - 本脚本 —— **行为回归**（功能级）：协议字段契约、跨操作一致性（run 与分步等价）、
    错误路径与结构化错误、数据层边界（损坏数据行为）、档案往返、边界输入抽样。

自包含在发布仓库内、零第三方依赖；任何检查失败 → 退出码 1（CI 正确判负）。
教学质量的 LLM 评估不在本脚本（也无法在 CI 无人值守环境完成），见仓库 README 说明。

用法（仓库根执行）：
    python .github/checks/regression_check.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import skill_api  # type: ignore  # noqa: E402

PASSED = 0
FAILED = 0
FAILURES: list[str] = []

SID = "coffee_ordering"
ANS = ["Hi, could I get a latte, please?", "For here, please."]
TA = "Could I get a bubble tea, please?"


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        FAILURES.append(f"{name}（{detail}）" if detail else name)


def h(req: dict) -> dict:
    """进程内调用 handle。"""
    return skill_api.handle(req)


def keys_of(d) -> set:
    return set(d) if isinstance(d, dict) else set()


def call_via_stdin(payload: str) -> dict | None:
    """通过 stdin/stdout 真实协议通道调用 skill_api.py。"""
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "skill_api.py")],
        input=payload, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return json.loads(proc.stdout)
    except Exception:  # noqa: BLE001
        check(f"通道调用 stdout 为 JSON（payload={payload[:40]!r}）", False,
              f"stdout={proc.stdout[:100]!r}")
        return None


# ===========================================================================
# A. 协议回归（主路径 + 字段契约）
# ===========================================================================

def test_protocol_regression() -> None:
    r = h({"action": "version"})
    check("version：ok + skill + 版本", r.get("ok") is True
          and r.get("skill") == "life2english" and r.get("version"), str(r))

    r = h({"action": "list_scenes"})
    scenes = r.get("scenes") or []
    check("list_scenes：非空 + 字段契约", bool(scenes) and keys_of(scenes[0]) >=
          {"id", "name", "summary", "tags", "difficulty", "example"}, str(r)[:120])

    for label, text, kind in [
        ("strong", "我想在咖啡店点单", "strong"),
        ("empty", "", "empty"),
        ("invalid", "asdfghjkl", "invalid"),
        ("none", "我想在健身房退卡", "none"),
    ]:
        r = h({"action": "recognize", "input": text})
        check(f"recognize[{label}]：kind 正确", r.get("ok") is True and r.get("kind") == kind,
              str(r)[:140])
    r = h({"action": "recognize", "input": "我想在咖啡店点单"})
    check("recognize：命中场景为 coffee_ordering", r.get("scene_id") == SID, str(r)[:120])
    check("recognize：字段契约", keys_of(r) >=
          {"kind", "scene_id", "scene_name", "matched_keywords", "ambiguous",
           "candidates", "message"}, str(keys_of(r)))

    r = h({"action": "task", "scene_id": SID})
    t = r.get("task") or {}
    check("task：字段契约", r.get("ok") is True and keys_of(t) >=
          {"scene_id", "scene_name", "difficulty", "situation", "goal", "expressions",
           "interactive_task", "notes", "common_mistakes"}, str(keys_of(t)))
    check("task：expressions 5 条且含 en/zh/note",
          len(t.get("expressions") or []) == 5
          and all(keys_of(e) >= {"en", "zh", "note"} for e in t["expressions"]))

    r = h({"action": "interact", "scene_id": SID})
    check("interact：开场含 role/opening", r.get("ok") is True and bool(r.get("opening")))

    r = h({"action": "feedback", "scene_id": SID, "answers": ["Hi, i want a coffe"]})
    check("feedback：字段契约", r.get("ok") is True and keys_of(r) >=
          {"answers", "praises", "overall", "limitations"}, str(keys_of(r)))
    fb0 = (r.get("answers") or [{}])[0]
    check("feedback：answers 含 suppressed_count",
          "suppressed_count" in fb0, str(keys_of(fb0)))
    check("feedback：检出拼写/大小写问题", any(
        i.get("kind") in {"拼写", "大小写"} for i in fb0.get("issues", [])), str(fb0)[:160])
    r_trunc = h({"action": "feedback", "scene_id": SID, "answers": [
        "hello i want a coffe with extra suger and i go to school by bus every day yesterday"]})
    fb_trunc = (r_trunc.get("answers") or [{}])[0]
    check("feedback：截断透明化（issues≤3 且 suppressed_count>0）",
          len(fb_trunc.get("issues") or []) <= 3 and fb_trunc.get("suppressed_count", 0) > 0,
          str(fb_trunc)[:160])

    r = h({"action": "transfer", "scene_id": SID})
    check("transfer：生成载荷字段契约", keys_of(r.get("task") or {}) >=
          {"scenario", "prompt", "example", "keywords"}, str(keys_of(r.get("task") or {})))
    r = h({"action": "transfer", "scene_id": SID, "attempt": TA})
    check("transfer：校验载荷字段契约", keys_of(r.get("result") or {}) >=
          {"attempt", "reused_keywords", "note"}, str(keys_of(r.get("result") or {})))

    r = h({"action": "summary", "scene_id": SID, "answers": ANS, "transfer_attempt": TA})
    check("summary：字段契约", r.get("ok") is True and keys_of(r) >=
          {"sections", "closing_note"}, str(keys_of(r)))

    r = h({"action": "run", "scene_id": SID, "answers": ANS, "transfer_attempt": TA})
    check("run：四段载荷", r.get("ok") is True and keys_of(r) >=
          {"task", "feedback", "transfer", "summary"}, str(keys_of(r))[:140])

    r = h({"action": "profile_export", "scene_id": SID, "answers": ANS,
           "transfer_attempt": TA})
    check("profile_export：档案与摘要", r.get("ok") is True
          and keys_of(r.get("profile") or {}) >= {"schema_version", "learner", "sessions", "items"}
          and (r.get("summary") or {}).get("sessions_count") == 1, str(r)[:140])
    prof = r.get("profile") or {}
    r2 = h({"action": "profile_import",
            "profile_text": json.dumps(prof, ensure_ascii=False)})
    check("profile_import：往返校验通过", r2.get("ok") is True and r2.get("import_ok") is True,
          str(r2)[:140])
    check("档案隐私：不保存对话原文",
          '"answers"' not in json.dumps(prof, ensure_ascii=False))


# ===========================================================================
# B. 跨操作一致性（run vs 分步）
# ===========================================================================

def test_cross_action_consistency() -> None:
    run = h({"action": "run", "scene_id": SID, "answers": ANS, "transfer_attempt": TA})
    check("run 成功", run.get("ok") is True, str(run)[:140])

    task = h({"action": "task", "scene_id": SID}).get("task") or {}
    check("一致性：run.task == task", run.get("task") == task)

    fb = h({"action": "feedback", "scene_id": SID, "answers": ANS})
    fb_seg = {k: fb.get(k) for k in ("answers", "praises", "overall", "limitations")}
    check("一致性：run.feedback == feedback（含 suppressed_count）",
          run.get("feedback") == fb_seg)

    gen = h({"action": "transfer", "scene_id": SID}).get("task") or {}
    check("一致性：run.transfer.task == transfer 生成载荷（含 keywords）",
          (run.get("transfer") or {}).get("task") == gen)

    ver = h({"action": "transfer", "scene_id": SID, "attempt": TA}).get("result") or {}
    check("一致性：run.transfer.result == transfer 校验载荷（含 attempt）",
          (run.get("transfer") or {}).get("result") == ver)

    sm = h({"action": "summary", "scene_id": SID, "answers": ANS, "transfer_attempt": TA})
    check("一致性：run.summary == summary",
          run.get("summary") == {k: sm.get(k) for k in ("sections", "closing_note")})

    run_skip = h({"action": "run", "scene_id": SID, "answers": ANS})
    check("一致性：run 跳过迁移 → skipped 标记",
          (run_skip.get("transfer") or {}).get("result") == {"skipped": True})


# ===========================================================================
# C. 错误路径（结构化错误，不抛栈）
# ===========================================================================

def test_error_paths() -> None:
    r = h({"action": "no_such_action"})
    check("未知 action → ok=false + supported",
          r.get("ok") is False and bool(r.get("supported")), str(r)[:140])

    r = h({"action": "task", "scene_id": "no_such_scene"})
    check("未知 scene_id → ok=false + error",
          r.get("ok") is False and bool(r.get("error")), str(r)[:140])

    r = h({"action": "task"})
    check("缺 scene_id 且无 input → ok=false", r.get("ok") is False, str(r)[:140])

    r = h({"action": "feedback", "scene_id": SID, "answers": "not a list"})
    check("answers 非数组 → ok=false + 可读原因",
          r.get("ok") is False and "answers" in str(r.get("error", "")), str(r)[:140])

    r = h([1, 2])  # type: ignore[arg-type]
    check("非 dict 请求 → ok=false", r.get("ok") is False, str(r)[:140])

    r = h({})
    check("空请求 → ok=false", r.get("ok") is False, str(r)[:140])

    # 数据损坏：结构化错误而非抛栈；version 不受影响
    original = skill_api.SceneStore

    class BrokenStore:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            raise FileNotFoundError("simulated: scenarios.json missing")

    skill_api.SceneStore = BrokenStore  # type: ignore[assignment]
    try:
        r1 = h({"action": "list_scenes"})
        r2 = h({"action": "version"})
    finally:
        skill_api.SceneStore = original  # type: ignore[assignment]
    check("数据损坏 → ok=false + 可读原因（非抛栈）",
          r1.get("ok") is False and "场景数据加载失败" in str(r1.get("error", "")), str(r1)[:140])
    check("数据损坏时 version 仍可用", r2.get("ok") is True and bool(r2.get("version")))

    # 通道层（stdin/stdout）
    r = call_via_stdin("not json")
    if r is not None:
        check("通道：非法 JSON → ok=false", r.get("ok") is False, str(r)[:140])
    r = call_via_stdin("")
    if r is not None:
        check("通道：空 stdin → ok=false", r.get("ok") is False, str(r)[:140])
    r = call_via_stdin(json.dumps({"action": "version"}))
    if r is not None:
        check("通道：正常请求 → ok=true", r.get("ok") is True, str(r)[:140])


# ===========================================================================
# D. 数据层边界（临时文件；不触碰真实数据）
# ===========================================================================

def test_store_boundaries() -> None:
    from life2english.store import SceneStore  # noqa: PLC0415

    try:
        store = SceneStore()
        n_scenes = len(store.all())
        real_ok = n_scenes > 0
        real_detail = ""
    except Exception as exc:  # noqa: BLE001
        real_ok, n_scenes = False, 0
        real_detail = f"{type(exc).__name__}: {exc}"
    check("真实 scenarios.json 正常加载", real_ok, real_detail or f"{n_scenes} 个场景")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        def expect(exc_type, name: str, filename: str) -> None:
            try:
                SceneStore(td / filename)
                check(name, False, "未抛出预期异常")
            except exc_type:
                check(name, True)
            except Exception as exc:  # noqa: BLE001
                check(name, False, f"实际 {type(exc).__name__}")

        expect(FileNotFoundError, "数据文件缺失 → FileNotFoundError", "missing.json")
        (td / "bad.json").write_text("{not json", encoding="utf-8")
        expect(json.JSONDecodeError, "JSON 损坏 → JSONDecodeError", "bad.json")
        (td / "nokey.json").write_text("{}", encoding="utf-8")
        expect(KeyError, "缺 scenes 键 → KeyError", "nokey.json")
        (td / "empty.json").write_text('{"scenes": []}', encoding="utf-8")
        s0 = SceneStore(td / "empty.json")
        check("空场景列表可用（all 空 / get 空）", s0.all() == [] and s0.get("x") is None)
        (td / "dup.json").write_text(
            '{"scenes": [{"id": "a", "name": "A"}, {"id": "a", "name": "B"}]}',
            encoding="utf-8")
        s1 = SceneStore(td / "dup.json")
        check("重复 ID：get 确定性取首个", (s1.get("a") or {}).get("name") == "A")


# ===========================================================================
# E. 边界输入抽样（不崩溃 + 不产生虚假结论）
# ===========================================================================

def test_boundary_inputs() -> None:
    for label, text in [
        ("纯 emoji", "😀🎉"),
        ("纯符号", "!@#$%^&*()"),
        ("超长输入", "我想在咖啡店点单，" * 400),
        ("控制字符", "咖\x00啡\x07点单"),
        ("中英混排", "我想 order 一杯 coffee"),
    ]:
        r = h({"action": "recognize", "input": text})
        check(f"recognize 不崩溃：{label}",
              isinstance(r, dict) and r.get("ok") is True
              and r.get("kind") in {"strong", "weak", "ambiguous", "none", "empty", "invalid"},
              str(r)[:120])

    r = h({"action": "feedback", "scene_id": SID, "answers": [None, 123, "👍", ""]})
    check("feedback 容忍非文本元素且不给虚假结论",
          r.get("ok") is True and "没有有效" in str(r.get("overall", "")), str(r)[:140])
    for fb in r.get("answers", []):
        check("feedback 每条 issue 含 kind/fix",
              all(i.get("kind") and i.get("fix") for i in fb.get("issues", [])))

    r = h({"action": "interact", "scene_id": SID, "answers_taken": "hi"})
    check("interact answers_taken 类型错误 → 结构化错误",
          r.get("ok") is False and "answers_taken" in str(r.get("error", "")), str(r)[:140])


# ===========================================================================
# F. 档案回归
# ===========================================================================

def test_profile_regression() -> None:
    r = h({"action": "profile_export", "scene_id": SID, "answers": ANS,
           "transfer_attempt": TA, "session_id": "ci1", "date": "2026-10-16"})
    check("profile_export 成功", r.get("ok") is True, str(r)[:140])
    prof = r.get("profile") or {}

    r2 = h({"action": "profile_import", "profile": prof})
    check("profile_import 对象通道", r2.get("import_ok") is True, str(r2)[:140])

    r3 = h({"action": "profile_import", "profile": {"schema_version": "9.0"}})
    check("不支持的主版本被拒（import_ok=false + errors）",
          r3.get("ok") is True and r3.get("import_ok") is False and bool(r3.get("errors")),
          str(r3)[:140])

    r4 = h({"action": "profile_import"})
    check("profile_import 缺输入 → ok=false", r4.get("ok") is False, str(r4)[:140])

    p1 = prof
    p2 = h({"action": "profile_export", "scene_id": "campus_canteen",
            "profile": p1, "answers": ["Could I get a set meal, please?"],
            "session_id": "ci2"})
    check("档案合并：会话累积", (p2.get("profile") or {}).get("sessions")
          and len(p2["profile"]["sessions"]) == 2, str(p2)[:140])


# ===========================================================================
# G. 确定性
# ===========================================================================

def test_determinism() -> None:
    payload = {"action": "run", "scene_id": SID, "answers": ANS, "transfer_attempt": TA}
    a = h(payload)
    b = h(payload)
    check("同请求两次结果一致", json.dumps(a, sort_keys=True, ensure_ascii=False)
          == json.dumps(b, sort_keys=True, ensure_ascii=False))


# ===========================================================================
def run_section(label: str, fn) -> None:
    """执行一节；未预期异常（如数据损坏引发的实现级异常）记为失败而非中断。"""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        check(f"[{label}] 段执行抛出未预期异常（应被实现捕获或以断言形式判负）",
              False, f"{type(exc).__name__}: {exc}")


def main() -> int:
    print("=" * 66)
    print("Life2English · 发布侧程序回归测试（CI）")
    print("=" * 66)

    run_section("A", test_protocol_regression)
    run_section("B", test_cross_action_consistency)
    run_section("C", test_error_paths)
    run_section("D", test_store_boundaries)
    run_section("E", test_boundary_inputs)
    run_section("F", test_profile_regression)
    run_section("G", test_determinism)

    print("-" * 66)
    if FAILURES:
        print("失败项：")
        for name in FAILURES:
            print(f"  - {name}")
    print(f"结果：{PASSED} 通过 / {FAILED} 失败")
    print("=" * 66)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
