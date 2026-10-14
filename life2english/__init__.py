"""life2english 包（开发仓库兼容入口）。

技能包的**唯一实现**位于 `scripts/life2english/`。本包仅为开发仓库布局提供兼容
导入（保持旧的 `from life2english.xxx import ...` 写法可用），指向同一份实现，
避免两份代码各自演化产生漂移。

技能包内的标准写法：
    import sys; sys.path.insert(0, "scripts")
    from life2english.store import SceneStore
"""

from __future__ import annotations

import sys
from pathlib import Path

_IMPL = Path(__file__).resolve().parent.parent / "scripts"
if str(_IMPL) not in sys.path:
    sys.path.insert(0, str(_IMPL))

# 让包内子模块解析到 scripts/life2english 下的真实实现
__path__ = [str(_IMPL / "life2english")]  # type: ignore[var-annotated]

__version__ = "1.4.3"
__all__ = [
    "store",
    "scenario",
    "taskgen",
    "feedback",
    "dialogue",
    "transfer",
    "summary",
    "session",
    "model_api",
]
