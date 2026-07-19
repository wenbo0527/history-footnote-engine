"""CLI 入口（薄壳）

🆕 v2.10.9 P1-1：业务逻辑下沉到 history_footnote.cli.*，
本文件只剩 argparse 参数解析 + dispatch（< 100 行）。

Usage:
    python -m history_footnote run <era_id>
    python -m history_footnote continue
    python -m history_footnote load <session_id> [--slot N]
    python -m history_footnote list-saves [--era <era_id>]
    python -m history_footnote delete-save <session_id>
    python -m history_footnote restart <era_id>
    python -m history_footnote list-eras
"""
from __future__ import annotations

import argparse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="history-footnote",
        description="历史注脚体验引擎——AI DM历史游戏",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p = sub.add_parser("run", help="开始新游戏")
    p.add_argument("era_id")
    p.add_argument("--provider", default="mock",
                   choices=["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "custom"])
    p.add_argument("--model", default="")
    p.add_argument("--api-key", default="")
    p.add_argument("--base-url", default="")
    p.add_argument("--skip-character", action="store_true")
    p.add_argument("--skip-schema-validate", action="store_true", help="跳过 era.json schema 校验")
    p.add_argument("--strict-schema-validate", action="store_true", help="严格校验")

    # continue
    p = sub.add_parser("continue", help="继续最近一次游戏")
    p.add_argument("--era")
    p.add_argument("--provider", default="mock",
                   choices=["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "custom"])
    p.add_argument("--model", default="")
    p.add_argument("--api-key", default="")
    p.add_argument("--base-url", default="")

    # load
    p = sub.add_parser("load", help="加载指定session和slot")
    p.add_argument("session_id")
    p.add_argument("--slot", default="auto", choices=["auto", "slot1", "slot2", "slot3"])
    p.add_argument("--provider", default="mock",
                   choices=["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "custom"])
    p.add_argument("--model", default="")
    p.add_argument("--api-key", default="")
    p.add_argument("--base-url", default="")

    # list-saves
    p = sub.add_parser("list-saves", help="列出所有存档")
    p.add_argument("--era")

    # delete-save
    p = sub.add_parser("delete-save", help="删除整个session")
    p.add_argument("session_id")

    # restart
    p = sub.add_parser("restart", help="同身份重开")
    p.add_argument("era_id")
    p.add_argument("--provider", default="mock",
                   choices=["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "custom"])
    p.add_argument("--model", default="")
    p.add_argument("--api-key", default="")
    p.add_argument("--base-url", default="")

    sub.add_parser("list-eras", help="列出可用时代包")
    sub.add_parser("list-providers", help="列出所有支持的LLM provider")
    return parser


def _dispatch(args: argparse.Namespace) -> None:
    """把 args 派发到 cli/* 业务函数"""
    from history_footnote.cli import (
        cmd_run, cmd_continue, cmd_load, cmd_restart,
        cmd_list_saves, cmd_delete_save, list_eras,
    )

    if args.command == "run":
        cmd_run(
            args.era_id, provider=args.provider, model=args.model,
            api_key=args.api_key, base_url=args.base_url,
            skip_character=args.skip_character,
            validate_schema=not args.skip_schema_validate,
            strict_schema=args.strict_schema_validate,
        )
    elif args.command == "continue":
        cmd_continue(
            era_id=getattr(args, "era", None), provider=args.provider,
            model=args.model, api_key=args.api_key, base_url=args.base_url,
        )
    elif args.command == "load":
        cmd_load(
            args.session_id, slot=args.slot, provider=args.provider,
            model=args.model, api_key=args.api_key, base_url=args.base_url,
        )
    elif args.command == "list-saves":
        cmd_list_saves(era_id=getattr(args, "era", None))
    elif args.command == "delete-save":
        cmd_delete_save(args.session_id)
    elif args.command == "restart":
        cmd_restart(
            args.era_id, provider=args.provider, model=args.model,
            api_key=args.api_key, base_url=args.base_url,
        )
    elif args.command == "list-eras":
        list_eras()
    elif args.command == "list-providers":
        from history_footnote.cli.lister import list_providers
        list_providers()


def main() -> None:
    """CLI 主入口（仅 argparse + dispatch）"""
    parser = _build_parser()
    args = parser.parse_args()
    _dispatch(args)


if __name__ == "__main__":
    main()