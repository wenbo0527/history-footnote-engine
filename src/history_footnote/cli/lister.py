"""🆕 v2.10.9 CLI 列表展示（eras / saves / providers）

P1-1：从 __main__.py 下沉。
"""
from __future__ import annotations

import json
from pathlib import Path


def list_eras() -> None:
    """列出所有可用时代包

    🆕 v2.10.9：调用 Pydantic schema 校验，schema 错误的 era 会 [WARN] 提示。
    """
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
                    # 🆕 v2.10.9：Pydantic schema 校验（lax，失败 warn 不 block）
                    try:
                        from history_footnote.wiki.era_schema import validate_era_config
                        cfg = validate_era_config(config, strict=False)
                        version = cfg.version
                        era_id = cfg.era_id
                        era_name = cfg.era_name
                    except ValueError as e:
                        print(f"[WARN] {era_json} schema 校验失败: {e}")
                        # schema 错误也允许列出（用兜底值）
                        version = config.get("version", "?")
                        era_id = config.get("era_id", p.name)
                        era_name = config.get("era_name", "未命名")

                    eras.append(
                        {
                            "id": era_id,
                            "name": era_name,
                            "version": version,
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


def list_saves(era_id: str | None = None) -> None:
    """列出所有存档"""
    from history_footnote.storage import DEFAULT_SAVE_ROOT, SaveManager

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


def list_providers() -> None:
    """列出所有支持的 LLM Provider"""
    from history_footnote.llm.providers import get_provider_info, list_providers

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