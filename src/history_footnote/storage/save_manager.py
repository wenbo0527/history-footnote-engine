"""存档管理

设计参考：设计文档v1.0.md 第七章"存档与重开机制设计" + 核心交付物合集v3.0.md 第七章

存档目录结构：
    saves/
    └── wanli1587_20260703_150200/   # 一个session的目录（session_id=时代id_时间戳）
        ├── auto.json                # 自动存档（每回合覆盖）
        ├── slot1.json               # 手动存档位1
        ├── slot2.json
        ├── slot3.json
        └── meta.json                # 元信息（创建时间/当前回合/摘要）

Phase 1 范围：
- 自动存档（每回合）
- 3个手动存档位
- 同身份重开
- 列出/删除存档
- 读档到指定存档位
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# 默认存档根目录
DEFAULT_SAVE_ROOT = Path("saves")

# Session ID 格式：{era_id}_{timestamp}
SESSION_ID_PATTERN = re.compile(r"^([a-z0-9_]+)_(\d{8}_\d{6})$")


@dataclass
class SaveSlot:
    """一个存档位的信息"""

    name: str  # "auto" / "slot1" / "slot2" / "slot3"
    path: Path
    round_number: int
    current_date: str
    saved_at: str
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SaveSession:
    """一个游戏会话的存档组"""

    session_id: str
    era_id: str
    created_at: str
    last_saved_at: str
    current_round: int
    current_date: str
    summary: str
    dir_path: Path
    slots: dict[str, SaveSlot] = field(default_factory=dict)  # name -> SaveSlot

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "era_id": self.era_id,
            "created_at": self.created_at,
            "last_saved_at": self.last_saved_at,
            "current_round": self.current_round,
            "current_date": self.current_date,
            "summary": self.summary,
            "slots": {name: s.to_dict() for name, s in self.slots.items()},
        }


class SaveManager:
    """存档管理器

    核心职责：
    - 创建/恢复/删除游戏会话
    - 在指定slot写入存档
    - 列出所有存档
    - 序列化/反序列化GameState
    """

    def __init__(self, save_root: Path = DEFAULT_SAVE_ROOT):
        self.save_root = save_root

    # === 会话管理 ===

    def create_session(self, era_id: str) -> SaveSession:
        """创建新会话（生成session_id和目录）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"{era_id}_{timestamp}"
        dir_path = self.save_root / session_id
        dir_path.mkdir(parents=True, exist_ok=True)

        now = datetime.now().isoformat(timespec="seconds")
        session = SaveSession(
            session_id=session_id,
            era_id=era_id,
            created_at=now,
            last_saved_at=now,
            current_round=0,
            current_date="",
            summary="新游戏",
            dir_path=dir_path,
        )
        self._write_meta(session)
        return session

    def find_session(self, session_id: str) -> SaveSession | None:
        """根据session_id查找会话

        🆕 v1.6.2 安全加固：先用 SESSION_ID_PATTERN 校验格式
        防止 path traversal（如 session_id='../../etc'）
        """
        if not session_id or not SESSION_ID_PATTERN.match(session_id):
            return None
        dir_path = self.save_root / session_id
        if not dir_path.is_dir():
            return None
        meta_path = dir_path / "meta.json"
        if not meta_path.exists():
            return None

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        session = SaveSession(
            session_id=meta["session_id"],
            era_id=meta["era_id"],
            created_at=meta["created_at"],
            last_saved_at=meta.get("last_saved_at", meta["created_at"]),
            current_round=meta.get("current_round", 0),
            current_date=meta.get("current_date", ""),
            summary=meta.get("summary", ""),
            dir_path=dir_path,
        )

        # 扫描所有slots
        for slot_name in ["auto", "slot1", "slot2", "slot3"]:
            slot_path = dir_path / f"{slot_name}.json"
            if slot_path.exists():
                try:
                    data = json.loads(slot_path.read_text(encoding="utf-8"))
                    session.slots[slot_name] = SaveSlot(
                        name=slot_name,
                        path=slot_path,
                        round_number=data.get("round_number", 0),
                        current_date=data.get("current_date", ""),
                        saved_at=data.get("saved_at", ""),
                        summary=data.get("summary", ""),
                    )
                except json.JSONDecodeError:
                    continue

        return session

    def find_latest_session(self, era_id: str | None = None) -> SaveSession | None:
        """查找最新的会话（可选按era_id过滤）"""
        if not self.save_root.exists():
            return None

        candidates = []
        for p in self.save_root.iterdir():
            if not p.is_dir():
                continue
            m = SESSION_ID_PATTERN.match(p.name)
            if not m:
                continue
            if era_id and m.group(1) != era_id:
                continue
            candidates.append(p)

        if not candidates:
            return None

        # 按目录名（包含时间戳）排序，取最新
        candidates.sort(key=lambda p: p.name, reverse=True)
        return self.find_session(candidates[0].name)

    def list_sessions(self, era_id: str | None = None) -> list[SaveSession]:
        """列出所有会话（可选按era_id过滤）"""
        if not self.save_root.exists():
            return []

        sessions = []
        for p in self.save_root.iterdir():
            if not p.is_dir():
                continue
            m = SESSION_ID_PATTERN.match(p.name)
            if not m:
                continue
            if era_id and m.group(1) != era_id:
                continue
            session = self.find_session(p.name)
            if session:
                sessions.append(session)

        # 按最后保存时间倒序
        sessions.sort(key=lambda s: s.last_saved_at, reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """删除整个会话（所有slot一起删）"""
        dir_path = self.save_root / session_id
        if not dir_path.is_dir():
            return False
        import shutil
        shutil.rmtree(dir_path)
        return True

    # === 存档读写 ===

    def save_state(
        self,
        session: SaveSession,
        slot_name: str,
        state_data: dict,
        summary: str = "",
    ) -> SaveSlot:
        """保存状态到指定slot

        Args:
            session: 目标会话
            slot_name: "auto" / "slot1" / "slot2" / "slot3"
            state_data: 完整的状态数据（GameState.to_dict() + 其他）
            summary: 存档摘要

        Returns:
            写入的SaveSlot信息
        """
        if slot_name not in ("auto", "slot1", "slot2", "slot3"):
            raise ValueError(f"非法slot名: {slot_name}")

        # 给state_data补充存档元信息
        state_data = dict(state_data)
        state_data["saved_at"] = datetime.now().isoformat(timespec="seconds")
        state_data["summary"] = summary

        slot_path = session.dir_path / f"{slot_name}.json"
        slot_path.write_text(
            json.dumps(state_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 更新session元信息
        session.last_saved_at = datetime.now().isoformat(timespec="seconds")
        session.current_round = state_data.get("round_number", session.current_round)
        session.current_date = state_data.get("current_date", session.current_date)
        session.summary = summary or session.summary
        if slot_name not in session.slots:
            session.slots[slot_name] = SaveSlot(
                name=slot_name,
                path=slot_path,
                round_number=state_data.get("round_number", 0),
                current_date=state_data.get("current_date", ""),
                saved_at=state_data["saved_at"],
                summary=summary,
            )
        else:
            session.slots[slot_name].round_number = state_data.get("round_number", 0)
            session.slots[slot_name].current_date = state_data.get("current_date", "")
            session.slots[slot_name].saved_at = state_data["saved_at"]
            session.slots[slot_name].summary = summary

        self._write_meta(session)
        return session.slots[slot_name]

    def load_state(self, session: SaveSession, slot_name: str) -> dict | None:
        """从指定slot读取状态"""
        if slot_name not in session.slots:
            return None
        slot_path = session.dir_path / f"{slot_name}.json"
        if not slot_path.exists():
            return None
        return json.loads(slot_path.read_text(encoding="utf-8"))

    def _write_meta(self, session: SaveSession) -> None:
        """写meta.json"""
        meta = {
            "session_id": session.session_id,
            "era_id": session.era_id,
            "created_at": session.created_at,
            "last_saved_at": session.last_saved_at,
            "current_round": session.current_round,
            "current_date": session.current_date,
            "summary": session.summary,
        }
        meta_path = session.dir_path / "meta.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # === 游戏内指令辅助 ===

    def make_initial_state_from_load(
        self,
        era_config: dict,
        loaded_data: dict,
    ) -> dict:
        """从load_state的data构造GameState参数

        Args:
            era_config: 时代包配置
            loaded_data: load_state()的返回值

        Returns:
            可直接传给 GameState(**kwargs) 的dict
        """
        from history_footnote.game_state import make_initial_state

        # 用make_initial_state获取初始结构（保证字段完整性）
        # 然后用loaded_data覆盖
        base_state = make_initial_state(
            era_id=loaded_data.get("era_id", era_config.get("era_id", "")),
            config=era_config,
        )
        base_dict = base_state.to_dict()

        # 用loaded_data覆盖
        for key, value in loaded_data.items():
            if key in base_dict:
                base_dict[key] = value

        return base_dict
