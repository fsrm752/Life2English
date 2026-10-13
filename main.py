#!/usr/bin/env python3
"""Life2English 命令行入口（兼容入口）。

技能包的标准入口是 `scripts/life2english_cli.py`；本文件保留在项目根目录，
便于从根目录直接运行，行为完全一致：

    python main.py                      # 交互式学习
    python scripts/life2english_cli.py  # 等价（技能包内的标准入口）
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "scripts" / "life2english_cli.py"

if __name__ == "__main__":
    sys.path.insert(0, str(_TARGET.parent))
    runpy.run_path(str(_TARGET), run_name="__main__")
