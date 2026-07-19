"""🆕 v2.10.9 saves 业务域 — 懒加载

P0-1 重构：根目录扁平模块 -> 业务域子包。

懒加载规则：
- 访问 saves.X 时，从子模块查找
- 子模块 import 失败（如缺 langchain_core）时 swallow，继续下一个
- 保证基础符号（如 GameState 等无 langchain 依赖的）总能加载
"""
from __future__ import annotations

from typing import Any

_SUBMODULES = ("storage", "resource_cache", "currency", "random_utils", "streaming", "web_server_concurrent", "web_enhancements", "runtime_config",)



def __getattr__(name: str) -> Any:
    """懒加载符号：失败 swallow，避免缺依赖时整个包不可用。"""
    import importlib as _importlib
    if name in _SUBMODULES:
        try:
            mod = _importlib.import_module(f"history_footnote.saves.{name}")
            globals()[name] = mod
            return mod
        except Exception:
            raise AttributeError(f"module 'history_footnote.saves' cannot load submodule {name!r}")
    try:
        mod = _importlib.import_module(f"history_footnote.saves.storage")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.resource_cache")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.currency")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.random_utils")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.streaming")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.web_server_concurrent")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.web_enhancements")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.runtime_config")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    raise AttributeError(f"module 'history_footnote.saves' has no attribute {name!r}")


def __dir__() -> list[str]:
    import importlib as _importlib
    names = list(_SUBMODULES)
    try:
        mod = _importlib.import_module(f"history_footnote.saves.storage")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.resource_cache")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.currency")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.random_utils")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.streaming")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.web_server_concurrent")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.web_enhancements")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.saves.runtime_config")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    return sorted(set(names))
