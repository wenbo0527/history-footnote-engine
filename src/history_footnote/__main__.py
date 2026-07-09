"""CLI入口

Usage:
    # 新游戏
    python -m history_footnote run <era_id>

    # 继续最近一次游戏（自动从最新session的auto.json加载）
    python -m history_footnote continue

    # 加载指定存档
    python -m history_footnote load <session_id> [--slot N]

    # 列出所有存档
    python -m history_footnote list-saves [--era <era_id>]

    # 删除存档
    python -m history_footnote delete-save <session_id>

    # 同身份重开
    python -m history_footnote restart <era_id>

    # 列出可用时代包
    python -m history_footnote list-eras
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from history_footnote.storage.save_manager import (
    DEFAULT_SAVE_ROOT,
    SaveManager,
    SaveSession,
)


def load_era_config(era_id: str) -> dict:
    """加载时代包配置"""
    era_path = Path("eras") / era_id / "era.json"
    if not era_path.exists():
        raise FileNotFoundError(f"时代包不存在: {era_path}")
    return json.loads(era_path.read_text(encoding="utf-8"))


def list_eras() -> None:
    """列出所有可用时代包"""
    eras_dir = Path("eras")
    if not eras_dir.exists():
        print("[ERROR] eras/ 目录不存在")
        return

    eras = []
    for p in eras_dir.iterdir():
        if p.is_dir() and not p.name.startswith("_") and not p.name.startswith("."):
            era_json = p / "era.json"
            if era_json.exists():
                try:
                    config = json.loads(era_json.read_text(encoding="utf-8"))
                    eras.append(
                        {
                            "id": config.get("era_id", p.name),
                            "name": config.get("era_name", "未命名"),
                            "version": config.get("version", "?"),
                        }
                    )
                except json.JSONDecodeError as e:
                    print(f"[WARN] {era_json} JSON解析失败: {e}")

    if not eras:
        print("[INFO] 没有找到时代包")
        return

    print("\n=== 可用时代包 ===\n")
    for era in eras:
        print(f"  {era['id']:20} {era['name']:20} (v{era['version']})")
    print()


def make_llm(
    era_config: dict,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    purpose: str = "dm",  # 🆕 v2.7 默认 dm（温度 0，可重放）
) -> Any:
    """构造LLM（v1.1+：多provider支持；v2.7+：按用途控制 temperature）

    Args:
        era_config: 时代包配置（Mock模式需要）
        provider: mock/openai/anthropic/minimax-anthropic/minimax-openai/custom
        model: 模型名（默认用provider的默认模型）
        api_key: API Key（默认从环境变量）
        base_url: 自定义endpoint（仅custom/minimax-*）
    """
    from history_footnote.llm_providers import make_llm_for_purpose
    return make_llm_for_purpose(
        purpose=purpose,  # 🆕 v2.7
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        era_config=era_config,
    )


def ask_character(era_config: dict) -> str:
    """问询角色——Q1性别 + Q2身份

    Returns:
        selected_identity id
    """
    identities = era_config.get("world", {}).get("player_identities", {})
    if not identities:
        # 兼容旧格式
        return ""

    print("\n" + "=" * 60)
    print("【角色创建】")
    print("=" * 60)

    # Q1: 性别
    print("\nQ1: 你是男是女？")
    print("  1) 男")
    print("  2) 女")
    while True:
        choice = input("> ").strip()
        if choice in ("1", "男", "m", "male"):
            gender = "male"
            break
        elif choice in ("2", "女", "f", "female"):
            gender = "female"
            break
        else:
            print("  [提示] 请输入 1 或 2")

    # Q2: 身份
    available = [(k, v) for k, v in identities.items() if v.get("gender") == gender]
    if not available:
        print(f"[ERROR] 没有{('男性' if gender == 'male' else '女性')}可选身份")
        sys.exit(1)

    print(f"\nQ2: 你想当谁？（{len(available)}个{'男性' if gender == 'male' else '女性'}身份）")
    for i, (k, v) in enumerate(available, 1):
        print(f"  {i}) {v.get('label', k)}: {v.get('role', '')}")
    while True:
        choice = input("> ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                return available[idx][0]
        except ValueError:
            pass
        print(f"  [提示] 请输入 1-{len(available)}")


def cmd_run(
    era_id: str,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    skip_character: bool = False,
) -> None:
    """运行新游戏

    Args:
        era_id: 时代包ID
        provider: LLM provider（mock/openai/anthropic/minimax-anthropic/minimax-openai/custom）
        model: 模型名（默认用provider默认）
        api_key: API Key
        base_url: 自定义endpoint
        skip_character: 是否跳过角色创建（用默认身份）
    """
    try:
        config = load_era_config(era_id)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[INFO] 加载时代包: {config.get('era_name', era_id)}")
    from history_footnote.llm_providers import get_provider_info
    info = get_provider_info(provider)
    print(f"[INFO] LLM Provider: {info.get('name', provider)}")
    if model:
        print(f"[INFO] Model: {model}")
    elif info.get("default_model"):
        print(f"[INFO] Model: {info['default_model']} (默认)")

    # 角色创建（v1.1+）
    selected_identity = ""
    if not skip_character and config.get("world", {}).get("player_identities"):
        selected_identity = ask_character(config)
        identity = config["world"]["player_identities"][selected_identity]
        print(f"\n[INFO] 你选择了: {identity.get('label', selected_identity)}")
        gender_cn = "男" if identity.get("gender") == "male" else "女"
        print(f"  性别: {gender_cn} | 角色: {identity.get('role', '')}")

    llm = make_llm(config, provider=provider, model=model, api_key=api_key, base_url=base_url, purpose="character")  # 🆕 v2.7

    from history_footnote.game_loop import GameLoop
    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
        selected_identity=selected_identity,
    )
    print(f"[INFO] 新建session: {game.session.session_id}")
    game.run()


def cmd_continue(
    era_id: str | None = None,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
) -> None:
    """继续最近一次游戏"""
    save_manager = SaveManager(DEFAULT_SAVE_ROOT)
    session = save_manager.find_latest_session(era_id=era_id)

    if session is None:
        if era_id:
            print(f"[ERROR] 找不到{era_id}的存档")
        else:
            print("[ERROR] 没有任何存档可继续")
        sys.exit(1)

    # 加载auto.json
    loaded = save_manager.load_state(session, "auto")
    if loaded is None:
        print(f"[ERROR] {session.session_id} 没有auto.json")
        sys.exit(1)

    print(f"[INFO] 继续session: {session.session_id}")
    print(f"[INFO] 加载回合{loaded.get('round_number')} {loaded.get('current_date')}")

    era_id = loaded.get("era_id", session.era_id)
    config = load_era_config(era_id)
    llm = make_llm(config, provider=provider, model=model, api_key=api_key, base_url=base_url, purpose="dm")  # 🆕 v2.7

    from history_footnote.game_loop import GameLoop
    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
        session=session,
        load_state_data=loaded,
    )
    game.run()


def cmd_load(
    session_id: str,
    slot: str = "auto",
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
) -> None:
    """加载指定session的指定slot"""
    save_manager = SaveManager(DEFAULT_SAVE_ROOT)
    session = save_manager.find_session(session_id)

    if session is None:
        print(f"[ERROR] 找不到session: {session_id}")
        sys.exit(1)

    loaded = save_manager.load_state(session, slot)
    if loaded is None:
        print(f"[ERROR] {session_id} 的 {slot} 没有存档")
        sys.exit(1)

    print(f"[INFO] 加载session: {session_id} slot={slot}")
    print(f"[INFO] 加载回合{loaded.get('round_number')} {loaded.get('current_date')}")

    era_id = loaded.get("era_id", session.era_id)
    config = load_era_config(era_id)
    llm = make_llm(config, provider=provider, model=model, api_key=api_key, base_url=base_url, purpose="dm")  # 🆕 v2.7

    from history_footnote.game_loop import GameLoop
    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
        session=session,
        load_state_data=loaded,
    )
    game.run()


def cmd_list_saves(era_id: str | None = None) -> None:
    """列出所有存档"""
    save_manager = SaveManager(DEFAULT_SAVE_ROOT)
    sessions = save_manager.list_sessions(era_id=era_id)

    if not sessions:
        print("[INFO] 没有存档")
        return

    print(f"\n=== 存档列表{'（' + era_id + '）' if era_id else ''} ===\n")
    for session in sessions:
        print(f"  {session.session_id}")
        print(f"    创建: {session.created_at} | 最近保存: {session.last_saved_at}")
        print(f"    进度: 第{session.current_round}回合 {session.current_date}")
        print(f"    摘要: {session.summary}")
        for name, slot in session.slots.items():
            print(f"      - {name}: 回合{slot.round_number} {slot.current_date}")
        print()


def cmd_delete_save(session_id: str) -> None:
    """删除整个session"""
    save_manager = SaveManager(DEFAULT_SAVE_ROOT)
    if save_manager.delete_session(session_id):
        print(f"[INFO] 已删除: {session_id}")
    else:
        print(f"[ERROR] 找不到session: {session_id}")
        sys.exit(1)


def cmd_restart(
    era_id: str,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
) -> None:
    """同身份重开（创建新的session，state完全重置）"""
    try:
        config = load_era_config(era_id)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[INFO] 同身份重开: {config.get('era_name', era_id)}")
    from history_footnote.llm_providers import get_provider_info
    info = get_provider_info(provider)
    print(f"[INFO] LLM Provider: {info.get('name', provider)}")

    llm = make_llm(config, provider=provider, model=model, api_key=api_key, base_url=base_url, purpose="dm")  # 🆕 v2.7

    from history_footnote.game_loop import GameLoop
    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
    )
    print(f"[INFO] 新session: {game.session.session_id}")
    game.run()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="history-footnote",
        description="历史注脚体验引擎——AI DM历史游戏",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run - 新游戏
    run_parser = subparsers.add_parser("run", help="开始新游戏")
    run_parser.add_argument("era_id", help="时代包ID")
    run_parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "custom"],
        help="LLM provider（默认mock）",
    )
    run_parser.add_argument("--model", default="", help="模型名（默认用provider默认）")
    run_parser.add_argument("--api-key", default="", help="API Key（默认从环境变量）")
    run_parser.add_argument("--base-url", default="", help="自定义endpoint（仅custom/minimax-*）")
    run_parser.add_argument("--skip-character", action="store_true", help="跳过角色创建问询（用默认身份）")

    # continue - 继续最近一次
    cont_parser = subparsers.add_parser("continue", help="继续最近一次游戏")
    cont_parser.add_argument("--era", help="指定时代包ID（可选）")
    cont_parser.add_argument("--provider", default="mock", choices=["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "custom"])
    cont_parser.add_argument("--model", default="")
    cont_parser.add_argument("--api-key", default="")
    cont_parser.add_argument("--base-url", default="")

    # load - 加载指定存档
    load_parser = subparsers.add_parser("load", help="加载指定session和slot")
    load_parser.add_argument("session_id", help="session_id")
    load_parser.add_argument("--slot", default="auto", choices=["auto", "slot1", "slot2", "slot3"], help="存档位")
    load_parser.add_argument("--provider", default="mock", choices=["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "custom"])
    load_parser.add_argument("--model", default="")
    load_parser.add_argument("--api-key", default="")
    load_parser.add_argument("--base-url", default="")

    # list-saves - 列出存档
    list_parser = subparsers.add_parser("list-saves", help="列出所有存档")
    list_parser.add_argument("--era", help="按时代包过滤")

    # delete-save - 删除存档
    del_parser = subparsers.add_parser("delete-save", help="删除整个session")
    del_parser.add_argument("session_id", help="session_id")

    # restart - 同身份重开
    restart_parser = subparsers.add_parser("restart", help="同身份重开")
    restart_parser.add_argument("era_id", help="时代包ID")
    restart_parser.add_argument("--provider", default="mock", choices=["mock", "openai", "anthropic", "minimax-anthropic", "custom"])
    restart_parser.add_argument("--model", default="")
    restart_parser.add_argument("--api-key", default="")
    restart_parser.add_argument("--base-url", default="")

    # list-eras - 列出可用时代包
    subparsers.add_parser("list-eras", help="列出可用时代包")

    # list-providers - 列出可用LLM provider
    subparsers.add_parser("list-providers", help="列出所有支持的LLM provider")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args.era_id, provider=args.provider, model=args.model,
                api_key=args.api_key, base_url=args.base_url, skip_character=args.skip_character)
    elif args.command == "continue":
        cmd_continue(era_id=getattr(args, "era", None), provider=args.provider,
                     model=args.model, api_key=args.api_key, base_url=args.base_url)
    elif args.command == "load":
        cmd_load(args.session_id, slot=args.slot, provider=args.provider,
                 model=args.model, api_key=args.api_key, base_url=args.base_url)
    elif args.command == "list-saves":
        cmd_list_saves(era_id=getattr(args, "era", None))
    elif args.command == "delete-save":
        cmd_delete_save(args.session_id)
    elif args.command == "restart":
        cmd_restart(args.era_id, provider=args.provider, model=args.model,
                    api_key=args.api_key, base_url=args.base_url)
    elif args.command == "list-eras":
        list_eras()
    elif args.command == "list-providers":
        from history_footnote.llm_providers import list_providers, get_provider_info
        print("\n=== 支持的LLM Provider ===\n")
        for p in list_providers():
            info = get_provider_info(p)
            print(f"  {p:25} {info.get('name', p)}")
            print(f"  {'':25} {info.get('description', '')}")
            if info.get("env_vars"):
                print(f"  {'':25} 环境变量: {', '.join(info['env_vars'])}")
            if info.get("default_model"):
                print(f"  {'':25} 默认模型: {info['default_model']}")
            if info.get("default_base_url"):
                print(f"  {'':25} 默认endpoint: {info['default_base_url']}")
            print()


if __name__ == "__main__":
    main()
