"""🆕 v2.10.9 events 业务域 — 懒加载

P0-1 重构：根目录扁平模块 -> 业务域子包。

懒加载规则：
- 访问 events.X 时，从子模块查找
- 子模块 import 失败（如缺 langchain_core）时 swallow，继续下一个
- 保证基础符号（如 GameState 等无 langchain 依赖的）总能加载
"""
from __future__ import annotations

from typing import Any

_SUBMODULES = ("bus", "handlers", "parser", "fate",)



def __getattr__(name: str) -> Any:
    """懒加载符号：失败 swallow，避免缺依赖时整个包不可用。"""
    import importlib as _importlib
    if name in _SUBMODULES:
        try:
            mod = _importlib.import_module(f"history_footnote.events.{name}")
            globals()[name] = mod
            return mod
        except Exception:
            raise AttributeError(f"module 'history_footnote.events' cannot load submodule {name!r}")
    # 优先 events.fate.cards（因为 fate_cards 原始模块重定向到 .fate.cards）
    try:
        fate_cards_mod = _importlib.import_module("history_footnote.events.fate.cards")
        if hasattr(fate_cards_mod, name):
            globals()[name] = getattr(fate_cards_mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.events.bus")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.events.handlers")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.events.parser")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.events.fate")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    raise AttributeError(f"module 'history_footnote.events' has no attribute {name!r}")


def __dir__() -> list[str]:
    import importlib as _importlib
    names = list(_SUBMODULES)
    try:
        mod = _importlib.import_module(f"history_footnote.events.bus")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.events.handlers")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.events.parser")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.events.fate")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
        fc = _importlib.import_module("history_footnote.events.fate.cards")
        names.extend(n for n in dir(fc) if not n.startswith("_"))
    except Exception:
        pass
    return sorted(set(names))
