"""🆕 v2.10.9 rule 业务域 — 懒加载

P0-1 重构：根目录扁平模块 -> 业务域子包。

懒加载规则：
- 访问 rule.X 时，从子模块查找
- 子模块 import 失败（如缺 langchain_core）时 swallow，继续下一个
- 保证基础符号（如 GameState 等无 langchain 依赖的）总能加载
"""
from __future__ import annotations

from typing import Any

_SUBMODULES = ("engine", "action_resolver", "dice", "quest", "ending", "settlement", "option_analyzer", "skill_selector", "input_validator",)



def __getattr__(name: str) -> Any:
    """懒加载符号：失败 swallow，避免缺依赖时整个包不可用。"""
    import importlib as _importlib
    if name in _SUBMODULES:
        try:
            mod = _importlib.import_module(f"history_footnote.rule.{name}")
            globals()[name] = mod
            return mod
        except Exception:
            raise AttributeError(f"module 'history_footnote.rule' cannot load submodule {name!r}")
    try:
        mod = _importlib.import_module(f"history_footnote.rule.engine")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.action_resolver")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.dice")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.quest")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.ending")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.settlement")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.option_analyzer")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.skill_selector")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.input_validator")
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)
            return globals()[name]
    except Exception:
        pass
    raise AttributeError(f"module 'history_footnote.rule' has no attribute {name!r}")


def __dir__() -> list[str]:
    import importlib as _importlib
    names = list(_SUBMODULES)
    try:
        mod = _importlib.import_module(f"history_footnote.rule.engine")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.action_resolver")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.dice")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.quest")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.ending")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.settlement")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.option_analyzer")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.skill_selector")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    try:
        mod = _importlib.import_module(f"history_footnote.rule.input_validator")
        names.extend(n for n in dir(mod) if not n.startswith("_"))
    except Exception:
        pass
    return sorted(set(names))
