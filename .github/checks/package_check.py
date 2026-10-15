#!/usr/bin/env python3
"""发布侧基础自检（GitHub Actions 调用）。

对**技能本体**（发布范围）做最小但关键的静态检查 + 协议冒烟。与开发侧
`tests/` 套件（运行于开发工作区、覆盖完整）分工互补：本脚本**自包含在发布
仓库内**、零第三方依赖（若环境已装 PyYAML 则用其做权威解析，否则退回内置
严格子集校验），只覆盖发布面最关键的检查项。

检查项：
  1. SKILL.md frontmatter 可解析 + 必填字段与格式；
  2. SKILL.md 的 @ 引用目标存在；
  3. scripts/data/scenarios.json 结构（场景必需字段 / 表达含 en·zh / id 唯一）；
  4. references/protocol.md 记录全部实际 action（对齐 skill_api.ACTIONS）；
  5. 关键能力边界声明存在（如实声明类）；
  6. 技能本体 Python 文件可编译；
  7. 协议冒烟：skill_api.py 的 recognize / run 两个真实请求。

用法（仓库根执行）：
    python .github/checks/package_check.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PASSED = 0
FAILED = 0
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
    else:
        FAILED += 1
        FAILURES.append(f"{name}（{detail}）" if detail else name)


# ---------------------------------------------------------------------------
# frontmatter 解析：PyYAML 优先，缺失时退回内置严格子集校验
# ---------------------------------------------------------------------------
def parse_frontmatter(block: str) -> tuple[dict | None, str]:
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None

    if yaml is not None:
        try:
            data = yaml.safe_load(block)
        except Exception as exc:  # noqa: BLE001 —— 解析失败按检查项报出
            return None, f"PyYAML 解析失败：{exc}"
        if not isinstance(data, dict):
            return None, f"解析结果不是映射：{type(data).__name__}"
        return {str(k): v for k, v in data.items()}, "PyYAML"

    # 严格子集：逐行 key: value；未加引号的值不得含「: 」「 #」或以 YAML 指示符开头
    data: dict[str, str] = {}
    for i, line in enumerate(block.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            return None, f"第 {i} 行含制表符"
        m = re.match(r"^([A-Za-z0-9_-]+):\s?(.*)$", line)
        if not m:
            return None, f"第 {i} 行不是 key: value 形式：{line[:40]!r}"
        key, value = m.group(1), m.group(2).strip()
        if key in data:
            return None, f"第 {i} 行键名重复：{key}"
        if value and value[0] not in "\"'" and (
            ": " in value or value.endswith(":") or " #" in value
            or value[0] in "!&*?|>%@`"
        ):
            return None, f"第 {i} 行未加引号的值含 YAML 特殊序列：{value[:40]!r}"
        if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
            value = value[1:-1]
        data[key] = value
    return (data, "内置严格子集") if data else (None, "未解析到任何字段")


# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 66)
    print("Life2English · 发布侧基础自检（CI）")
    print("=" * 66)

    # 1) SKILL.md frontmatter
    skill_path = ROOT / "SKILL.md"
    check("SKILL.md 存在", skill_path.is_file(), str(skill_path))
    skill_md = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", skill_md, re.S)
    check("SKILL.md 含 YAML frontmatter（--- 包裹）", m is not None)
    fm: dict | None = None
    if m:
        fm, engine = parse_frontmatter(m.group(1))
        check(f"frontmatter 可解析〔{engine}〕", fm is not None, str(engine))
    if fm:
        for f in ("name", "description", "category", "version"):
            check(f"frontmatter 含必填字段 {f}", bool(fm.get(f)), f"值={fm.get(f)!r}")
        check("version 形如 x.y.z",
              bool(re.fullmatch(r"\d+\.\d+\.\d+", str(fm.get("version", "")))),
              f"version={fm.get('version')!r}")
        check("name 标识合法（小写字母 / 数字 / -）",
              bool(re.fullmatch(r"[a-z0-9-]+", str(fm.get("name", "")))),
              f"name={fm.get('name')!r}")

    # 2) @ 引用可解析
    refs = re.findall(r"@(references/[\w./-]+|templates/[\w./-]+|scripts/[\w./-]+)", skill_md)
    check("SKILL.md 含 @ 子资源引用", len(refs) > 0, f"引用数={len(refs)}")
    for r in sorted(set(refs)):
        check(f"@ 引用可解析：{r}", (ROOT / r).is_file(), f"缺失 {(ROOT / r)}")

    # 3) 场景数据
    data: dict = {}
    scen_path = ROOT / "scripts" / "data" / "scenarios.json"
    check("scripts/data/scenarios.json 存在", scen_path.is_file(), str(scen_path))
    if scen_path.is_file():
        try:
            data = json.loads(scen_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            check("scenarios.json 可解析", False, str(exc))
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    check("scenarios.json 含场景（>0）", len(scenes) > 0, f"{len(scenes)} 个")
    required_scene_fields = ["id", "name", "summary", "goal", "expressions",
                             "interactive_task", "dialogue", "transfer",
                             "notes", "common_mistakes"]
    incomplete = []
    for s in scenes:
        missing = [f for f in required_scene_fields if not s.get(f)]
        if missing:
            incomplete.append((s.get("id", "?"), missing))
    check(f"全部 {len(scenes)} 个场景字段完备", not incomplete, f"缺失：{incomplete}")
    ids = [s.get("id") for s in scenes]
    check("scene_id 唯一", len(ids) == len(set(ids)), f"{len(ids)} vs {len(set(ids))}")
    bad_expr = [s.get("id") for s in scenes
                if any(not (e.get("en") and e.get("zh")) for e in s.get("expressions", []))]
    check("每条实用表达含英文例句与中文释义", not bad_expr, f"异常：{bad_expr}")

    # 4) 协议 action 对齐
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import skill_api  # type: ignore  # noqa: E402
        actions = sorted(skill_api.ACTIONS)
        check("skill_api.ACTIONS 非空", bool(actions), f"{len(actions)} 个")
        protocol = (ROOT / "references" / "protocol.md").read_text(encoding="utf-8")
        for a in actions:
            check(f"protocol.md 记录 action：{a}", a in protocol)
        check("protocol.md 记录 version 返回", "version" in protocol)
    except Exception as exc:  # noqa: BLE001
        check("skill_api 可导入", False, f"{type(exc).__name__}: {exc}")

    # 5) 关键能力边界声明（如实声明类，缺失意味着发布物说谎）
    for b in ("不能动态生成", "无法可靠判断", "不自动保存", "不调用外部 API", "不虚构"):
        check(f"SKILL.md 含边界声明「{b}」", b in skill_md)

    # 6) 技能本体 Python 文件可编译
    py_files: list[Path] = []
    for t in (ROOT / "main.py", ROOT / "life2english", ROOT / "scripts"):
        if t.is_dir():
            py_files += [p for p in t.rglob("*.py") if "__pycache__" not in p.parts]
        elif t.is_file():
            py_files.append(t)
    check("技能本体含 Python 文件（>0）", len(py_files) > 0, f"{len(py_files)} 个")
    for f in sorted(py_files):
        rel = f.relative_to(ROOT).as_posix()
        try:
            compile(f.read_bytes(), rel, "exec")
            check(f"可编译：{rel}", True)
        except SyntaxError as exc:
            check(f"可编译：{rel}", False, f"{exc.msg}（第 {exc.lineno} 行）")

    # 7) 协议冒烟（真实执行 skill_api.py 的 stdin/stdout 通道）
    smoke_cases = [
        ("recognize", {"action": "recognize", "input": "我想在咖啡店点单"},
         lambda d: d.get("ok") is True and d.get("kind") == "strong"),
        ("run", {"action": "run", "scene_id": "campus_canteen",
                 "answers": ["Could I get a set meal, please?"],
                 "transfer_attempt": "Could I get a bubble tea, please?"},
         lambda d: d.get("ok") is True
         and all(k in d for k in ("task", "feedback", "transfer", "summary"))),
    ]
    for name, req, pred in smoke_cases:
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "scripts" / "skill_api.py")],
            input=json.dumps(req), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        try:
            resp = json.loads(proc.stdout)
        except Exception:  # noqa: BLE001
            check(f"协议冒烟：{name}", False, f"stdout 非 JSON：{proc.stdout[:80]!r}")
            continue
        check(f"协议冒烟：{name}", proc.returncode == 0 and pred(resp),
              f"resp={json.dumps(resp, ensure_ascii=False)[:100]}")

    # 汇总
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
