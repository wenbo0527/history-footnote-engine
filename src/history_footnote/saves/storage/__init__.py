"""存档存储子包

迁移历史：v2.10.9 P0-1 重构，从 history_footnote.storage/ 迁至 history_footnote.saves.storage/
"""
from history_footnote.saves.storage.save_manager import (  # noqa: F401
    DEFAULT_SAVE_ROOT,
    SESSION_ID_PATTERN,
    SaveManager,
    SaveSession,
    SaveSlot,
)