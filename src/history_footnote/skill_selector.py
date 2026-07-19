"""🆕 v2.10.9 module alias shim: history_footnote.skill_selector -> history_footnote.rule.skill_selector

P0-1 重构：根目录扁平模块 -> 业务域子包。
本 shim 通过 sys.modules alias 让 `from history_footnote.skill_selector import X`
（含 _private 符号）等价于 `from history_footnote.rule.skill_selector import X`。

新 import 路径（推荐）：`from history_footnote.rule.skill_selector import ...`
"""
from __future__ import annotations

import sys as _sys

_target = "history_footnote.rule.skill_selector"
_mod = _sys.modules.get(_target)
if _mod is None:
    import importlib as _importlib
    _mod = _importlib.import_module(_target)
_sys.modules[__name__] = _mod
