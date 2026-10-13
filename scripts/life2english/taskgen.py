"""学习任务生成：从场景模板组装学习目标、实用表达与互动任务。

阶段一为模板驱动（本地预设内容），不调用外部模型。
未来模型接入点：见 life2english.model_api。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Expression:
    en: str
    zh: str
    note: str = ""


@dataclass
class LearningTask:
    scene_id: str
    scene_name: str
    difficulty: str
    goal: str
    expressions: list[Expression] = field(default_factory=list)
    interactive_task: str = ""
    notes: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    situation: str = ""


def build_task(scene: dict) -> LearningTask:
    """根据场景模板生成学习任务。"""
    return LearningTask(
        scene_id=scene["id"],
        scene_name=scene["name"],
        difficulty=scene.get("difficulty", ""),
        goal=scene.get("goal", ""),
        expressions=[
            Expression(en=e["en"], zh=e["zh"], note=e.get("note", ""))
            for e in scene.get("expressions", [])
        ],
        interactive_task=scene.get("interactive_task", ""),
        notes=list(scene.get("notes", [])),
        common_mistakes=list(scene.get("common_mistakes", [])),
        situation=scene.get("summary", ""),
    )
