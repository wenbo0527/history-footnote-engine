"""🆕 v2.10.9 CLI 子包

P1-1 重构：把 __main__.py 中的业务逻辑下沉到 cli/。
- cli/era_loader.py — load_era_config + Pydantic era 校验
- cli/character_wizard.py — ask_character（CLI 角色创建问询）
- cli/lister.py — list_eras / list_saves / list_providers
- cli/commands/run.py / continue.py / load.py / restart.py / save_ops.py
- cli/main.py — 仅 argparse 参数解析 + dispatch（目标 < 100 行）

100% 向后兼容：__main__.py 把所有公开符号 re-export，老脚本无需修改。
"""
from __future__ import annotations

from history_footnote.cli.era_loader import load_era_config
from history_footnote.cli.character_wizard import ask_character
from history_footnote.cli.lister import list_eras
from history_footnote.cli.commands.run import cmd_run
from history_footnote.cli.commands.cont import cmd_continue
from history_footnote.cli.commands.load import cmd_load
from history_footnote.cli.commands.save_ops import cmd_list_saves, cmd_delete_save
from history_footnote.cli.commands.restart import cmd_restart

__all__ = [
    "load_era_config",
    "ask_character",
    "list_eras",
    "cmd_run",
    "cmd_continue",
    "cmd_load",
    "cmd_list_saves",
    "cmd_delete_save",
    "cmd_restart",
]