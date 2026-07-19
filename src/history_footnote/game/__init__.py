"""🆕 v2.10.9 game 业务域 — 懒加载

P0-1 重构：根目录扁平模块 -> 业务域子包。

懒加载规则：
- 访问 game.X 时，从子模块查找
- 子模块 import 失败（如缺 langchain_core）时 swallow，继续下一个
- 保证基础符号（如 GameState 等无 langchain 依赖的）总能加载
"""
from __future__ import annotations

from typing import Any

_SUBMODULES = ("state", "loop", "loop_display", "loop_events", "loop_identity", "loop_save", "memory", "engine_facade", "sub_facades", "initial_state_resolver", "state_ref_helpers", "drama_manager", "session_manager", "concurrency", "replay",)



def __getattr__(name: str) -> Any:
    """懒加载符号：失败 swallow，避免缺依赖时整个包不可用。"""
    import importlib as _importlib
    if name in _SUBMODULES:
        try:
            mod = _importlib.import_module(f"history_footnote.game.{name}")
            globals()[name] = mod
            return mod
        except Exception:
            raise AttributeError(f"module 'history_footnote.game' cannot load submodule {name!r}")
    try:
        mod = _importlib.import_module(f"history_footnote.game.state")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_display")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_events")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_identity")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_save")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.memory")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.engine_facade")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.sub_facades")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.initial_state_resolver")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.state_ref_helpers")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.drama_manager")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.session_manager")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.concurrency")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.replay")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    raise AttributeError(f"module 'history_footnote.game' has no attribute {name!r}")


def __dir__() -> list[str]:
    import importlib as _importlib
    names = list(_SUBMODULES)
    try:
        mod = _importlib.import_module(f"history_footnote.game.state")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_display")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_events")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_identity")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.loop_save")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.memory")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.engine_facade")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.sub_facades")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.initial_state_resolver")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.state_ref_helpers")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.drama_manager")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.session_manager")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.concurrency")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.game.replay")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    return sorted(set(names))
