"""🆕 v2.10.9 llm 业务域 — 懒加载

P0-1 重构：根目录扁平模块 -> 业务域子包。

懒加载规则：
- 访问 llm.X 时，从子模块查找
- 子模块 import 失败（如缺 langchain_core）时 swallow，继续下一个
- 保证基础符号（如 GameState 等无 langchain 依赖的）总能加载
"""
from __future__ import annotations

from typing import Any

_SUBMODULES = ("providers", "wrapper", "cache", "kv_cache", "mock", "api_gateway", "integrations", "monitor", "analytics",)



def __getattr__(name: str) -> Any:
    """懒加载符号：失败 swallow，避免缺依赖时整个包不可用。"""
    import importlib as _importlib
    if name in _SUBMODULES:
        try:
            mod = _importlib.import_module(f"history_footnote.llm.{name}")
            globals()[name] = mod
            return mod
        except Exception:
            raise AttributeError(f"module 'history_footnote.llm' cannot load submodule {name!r}")
    try:
        mod = _importlib.import_module(f"history_footnote.llm.providers")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.wrapper")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.cache")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.kv_cache")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.mock")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.api_gateway")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.integrations")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.monitor")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.analytics")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    raise AttributeError(f"module 'history_footnote.llm' has no attribute {name!r}")


def __dir__() -> list[str]:
    import importlib as _importlib
    names = list(_SUBMODULES)
    try:
        mod = _importlib.import_module(f"history_footnote.llm.providers")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.wrapper")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.cache")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.kv_cache")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.mock")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.api_gateway")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.integrations")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.monitor")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.llm.analytics")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    return sorted(set(names))
