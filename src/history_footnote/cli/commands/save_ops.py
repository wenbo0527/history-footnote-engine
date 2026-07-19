"""🆕 v2.10.9 cmd_list_saves / cmd_delete_save"""
from __future__ import annotations

import sys

from history_footnote.storage import DEFAULT_SAVE_ROOT, SaveManager


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
    """删除整个 session"""
    save_manager = SaveManager(DEFAULT_SAVE_ROOT)
    if save_manager.delete_session(session_id):
        print(f"[INFO] 已删除: {session_id}")
    else:
        print(f"[ERROR] 找不到session: {session_id}")
        sys.exit(1)