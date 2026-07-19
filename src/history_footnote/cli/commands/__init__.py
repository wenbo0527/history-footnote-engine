"""CLI 子命令集合"""
from history_footnote.cli.commands.run import cmd_run
from history_footnote.cli.commands.cont import cmd_continue
from history_footnote.cli.commands.load import cmd_load
from history_footnote.cli.commands.save_ops import cmd_list_saves, cmd_delete_save
from history_footnote.cli.commands.restart import cmd_restart

__all__ = [
    "cmd_run",
    "cmd_continue",
    "cmd_load",
    "cmd_list_saves",
    "cmd_delete_save",
    "cmd_restart",
]