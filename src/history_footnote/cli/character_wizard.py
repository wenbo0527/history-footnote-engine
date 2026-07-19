"""🆕 v2.10.9 CLI 角色创建问询

P1-1：从 __main__.py 下沉。
Q1 性别 + Q2 身份，返回选中的 identity id。
"""
from __future__ import annotations

import sys


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