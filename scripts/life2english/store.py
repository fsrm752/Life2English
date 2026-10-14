"""模板仓库：加载与管理场景模板数据（scripts/data/scenarios.json）。

模板数据与业务逻辑分离：新增/修改场景只需编辑 JSON 数据文件，不改代码。

数据文件**只有一份**（单一数据源，杜绝双写漂移）：
    scripts/data/scenarios.json      # store.py 位于 scripts/life2english/ → ../data/
开发仓库布局下的兼容导入（根目录 `life2english/` 包）转发到同一份实现，
读到的也是这一个文件。
"""

from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
DEFAULT_DATA_FILE = _HERE.parent / "data" / "scenarios.json"   # scripts/data/


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
