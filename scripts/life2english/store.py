"""模板仓库：加载与管理场景模板数据（data/scenarios.json）。

模板数据与业务逻辑分离：新增/修改场景只需编辑 JSON 数据文件，不改代码。
"""

from __future__ import annotations

import json
from pathlib import Path

# 数据文件查找顺序（兼容两种布局）：
#   1) scripts/data/scenarios.json         —— 技能包内（scripts/life2english/ → ../data/）
#   2) <项目根>/data/scenarios.json         —— 开发仓库布局（life2english/ → ../data/）
_HERE = Path(__file__).resolve().parent
_CANDIDATES = [
    _HERE.parent / "data" / "scenarios.json",          # scripts/data/
    _HERE.parent.parent / "data" / "scenarios.json",   # 项目根/data/
]
DEFAULT_DATA_FILE = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])


class SceneStore:
    """场景模板仓库。"""

    def __init__(self, data_file: Path | str = DEFAULT_DATA_FILE) -> None:
        self.data_file = Path(data_file)
        self._data = self._load()
        self.scenes: list[dict] = self._data["scenes"]
        self.common_en_words: set[str] = {
            w.lower() for w in self._data.get("common_en_words", [])
        }

    def _load(self) -> dict:
        with open(self.data_file, encoding="utf-8") as f:
            return json.load(f)

    def all(self) -> list[dict]:
        """返回全部场景模板。"""
        return list(self.scenes)

    def get(self, scene_id: str) -> dict | None:
        """按 id 取场景模板，不存在返回 None。"""
        for scene in self.scenes:
            if scene["id"] == scene_id:
                return scene
        return None

    def names(self) -> list[str]:
        return [s["name"] for s in self.scenes]
