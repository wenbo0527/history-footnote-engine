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
    # 🆕 v1.7.30: 账户隔离
    account_id: str = ""  # 空 = 旧版/未登录
    # 🆕 v2.7+: 冷存档标记（30 天未活动 → 标 archived，移到 _archive/）
    archived: bool = False
    archived_at: str = ""

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "era_id": self.era_id,
            "created_at": self.created_at,
            "last_saved_at": self.last_saved_at,
            "current_round": self.current_round,
            "current_date": self.current_date,
            "summary": self.summary,
            "account_id": self.account_id,    # 🆕 v1.7.30
            "archived": self.archived,         # 🆕 v2.7+
            "archived_at": self.archived_at,   # 🆕 v2.7+
            "slots": {name: s.to_dict() for name, s in self.slots.items()},
        }

    @classmethod
    def from_dict(cls, data: dict, dir_path: Path) -> "SaveSession":
        """🆕 v1.7.30: 从 dict 反序列化（兼容旧存档）"""
        return cls(
            session_id=data.get("session_id", ""),
            era_id=data.get("era_id", "wanli1587"),
            created_at=data.get("created_at", ""),
            last_saved_at=data.get("last_saved_at", ""),
            current_round=int(data.get("current_round", 0)),
            current_date=data.get("current_date", ""),
            summary=data.get("summary", ""),
            account_id=data.get("account_id", ""),   # 旧存档 = 空
            archived=bool(data.get("archived", False)),         # 🆕 v2.7+
            archived_at=data.get("archived_at", ""),            # 🆕 v2.7+
            dir_path=dir_path,
            slots={},
        )


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

    def find_session(self, session_id: str, include_archived: bool = False) -> SaveSession | None:
        """根据session_id查找会话

        🆕 v1.6.2 安全加固：先用 SESSION_ID_PATTERN 校验格式
        防止 path traversal（如 session_id='../../etc'）
        🆕 v2.7+ 健壮性：meta.json 缺关键字段时返回 None（不抛 KeyError）
        🆕 v2.7+ include_archived=True 时也会查 _archive/ 下的会话
        """
        if not session_id or not SESSION_ID_PATTERN.match(session_id):
            return None
        dir_path = self.save_root / session_id
        if not dir_path.is_dir() and include_archived:
            # 试试 _archive/
            dir_path = self.archive_root() / session_id
        if not dir_path.is_dir():
            return None
        meta_path = dir_path / "meta.json"
        if not meta_path.exists():
            return None

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        # 🆕 v2.7+ 关键字段缺失时跳过（不抛 KeyError）
        if "session_id" not in meta or "era_id" not in meta or "created_at" not in meta:
            return None

        session = SaveSession(
            session_id=meta["session_id"],
            era_id=meta["era_id"],
            created_at=meta["created_at"],
            last_saved_at=meta.get("last_saved_at", meta["created_at"]),
            current_round=meta.get("current_round", 0),
            current_date=meta.get("current_date", ""),
            summary=meta.get("summary", ""),
            # 🆕 v1.7.30: 读 account_id
            account_id=meta.get("account_id", ""),
            # 🆕 v2.7+: 冷存档标记
            archived=bool(meta.get("archived", False)),
            archived_at=meta.get("archived_at", ""),
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

    def list_sessions(
        self,
        era_id: str | None = None,
        account_id: str | None = None,
        include_archived: bool = False,
    ) -> list[SaveSession]:
        """列出所有会话（可选按 era_id / account_id 过滤）

        🆕 v1.7.30: account_id 过滤
        - account_id=None → 列出所有（管理员/调试用）
        - account_id='default' → 列出 account_id=='' 的旧存档 + 'default' 的
        - account_id=具体值 → 只列该账户
        🆕 v2.7+: include_archived=False 时自动过滤冷存档
        """
        if not self.save_root.exists():
            return []

        sessions = []
        # 🆕 v2.7+ include_archived=True 时也查 _archive/ 下的会话
        roots = [self.save_root]
        if include_archived:
            archive_root = self.archive_root()
            if archive_root.exists():
                roots.append(archive_root)
        for root in roots:
            for p in root.iterdir():
                if not p.is_dir():
                    continue
                m = SESSION_ID_PATTERN.match(p.name)
                if not m:
                    continue
                if era_id and m.group(1) != era_id:
                    continue
                session = self.find_session(p.name, include_archived=(root != self.save_root))
                if session:
                    # 账户过滤
                    if account_id is not None:
                        if account_id == 'default':
                            # default 看到：所有无账户（account_id==''）+ account_id=='default' 的
                            if session.account_id and session.account_id != 'default':
                                continue
                        elif account_id == '__all__':
                            # 管理员：所有
                            pass
                        else:
                            # 具体账户：只看自己的
                            if session.account_id != account_id:
                                continue
                    # 🆕 v2.7+: 冷存档过滤（默认隐藏）
                    if not include_archived and session.archived:
                        continue
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

    # === 🆕 v2.7+ 冷存档 ===

    # 冷存档子目录（与正式存档物理隔离，方便审计/恢复）
    ARCHIVE_SUBDIR_NAME = "_archive"

    def archive_root(self) -> "Path":
        """冷存档根目录: saves/_archive/"""
        return self.save_root / self.ARCHIVE_SUBDIR_NAME

    def archive_inactive_sessions(self, within_days: int = 30) -> int:
        """🆕 v2.7+ 把 N 天未活动的存档标 archived 并移到 _archive/

        Args:
            within_days: last_saved_at 距今超过此值视为冷存档

        Returns: 实际标记/移动的 session 数量

        设计：
        - 只读 + 写 meta，不删 slot 文件（用户数据绝对安全）
        - 移到 saves/_archive/<session_id>/（不分子目录——按 account_id 隔离不必要，
          因为 archived 不可见；如需可后续加 _archive/<account_id>/）
        - 重复跑幂等：archived 已是 True 的跳过；移动前检查目标是否存在
        """
        if not self.save_root.exists():
            return 0

        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=within_days)
        moved = 0

        archive_dir = self.archive_root()
        archive_dir.mkdir(parents=True, exist_ok=True)

        for p in self.save_root.iterdir():
            if not p.is_dir():
                continue
            if p.name == self.ARCHIVE_SUBDIR_NAME:
                continue
            m = SESSION_ID_PATTERN.match(p.name)
            if not m:
                continue
            session = self.find_session(p.name)
            if not session:
                continue
            if session.archived:
                continue  # 已归档，跳过

            # 解析 last_saved_at
            last = _parse_iso(session.last_saved_at)
            if last and last < cutoff:
                # 标 archived
                session.archived = True
                session.archived_at = datetime.now().isoformat(timespec="seconds")
                self._write_meta(session)

                # 移动到 _archive/（shutil.move 跨盘也 OK）
                import shutil
                target = archive_dir / p.name
                if target.exists():
                    # 目标已存在 → 不覆盖（避免数据冲突），只标 archived 不移动
                    continue
                try:
                    shutil.move(str(p), str(target))
                    # 更新 dir_path 引用
                    session.dir_path = target
                except OSError:
                    # 移动失败 → 回滚 archived 标记
                    session.archived = False
                    session.archived_at = ""
                    self._write_meta(session)
                    continue
                moved += 1
        return moved

    def unarchive_session(self, session_id: str) -> bool:
        """🆕 v2.7+ 复活冷存档（把 _archive/ 下的 session 移回 saves/）

        触发场景：
        - 管理员误判恢复
        - 玩家主动请求（v2.8+ UI）
        """
        # 先在 _archive/ 找
        archive_dir = self.archive_root() / session_id
        if archive_dir.is_dir():
            session = self.find_session(session_id, include_archived=True)
            if not session:
                return False
            target = self.save_root / session_id
            if target.exists():
                return False
            import shutil
            try:
                shutil.move(str(archive_dir), str(target))
            except OSError:
                return False
            session.archived = False
            session.archived_at = ""
            session.dir_path = target
            self._write_meta(session)
            return True
        return False

    def list_archived_sessions(
        self, account_id: str | None = None
    ) -> list[SaveSession]:
        """🆕 v2.7+ 列出 _archive/ 下的会话（管理员面板用）"""
        archive_dir = self.archive_root()
        if not archive_dir.exists():
            return []
        sessions = []
        for p in archive_dir.iterdir():
            if not p.is_dir():
                continue
            session = self.find_session(p.name, include_archived=True)
            if not session:
                continue
            if account_id is not None and account_id != "__all__":
                if session.account_id != account_id:
                    continue
            sessions.append(session)
        sessions.sort(key=lambda s: s.archived_at or s.last_saved_at, reverse=True)
        return sessions

    def migrate_account_id(self, old_id: str, new_id: str) -> int:
        """🆕 v2.7+ 迁移存档 owner：把 meta.json / 所有 slot.json 中
        account_id == old_id 改成 new_id。

        触发场景：游客（account_id='guest_xxx'）注册成功 → 把他的存档迁到新账户。

        Returns: 迁移的 session 数量
        """
        if not old_id or not new_id or old_id == new_id:
            return 0
        if not self.save_root.exists():
            return 0
        moved = 0
        for p in self.save_root.iterdir():
            if not p.is_dir():
                continue
            if p.name == self.ARCHIVE_SUBDIR_NAME:
                continue
            meta_path = p / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if meta.get("account_id") != old_id:
                continue
            # 更新 meta.json
            meta["account_id"] = new_id
            try:
                meta_path.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except OSError:
                continue
            # 同步更新每个 slot.json 里的 account_id（如果有）
            for slot_name in ("auto", "slot1", "slot2", "slot3"):
                slot_path = p / f"{slot_name}.json"
                if not slot_path.exists():
                    continue
                try:
                    slot_data = json.loads(slot_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if slot_data.get("account_id") == old_id:
                    slot_data["account_id"] = new_id
                    try:
                        slot_path.write_text(
                            json.dumps(slot_data, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                    except OSError:
                        pass
            moved += 1
        return moved

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
        # 🆕 v1.7.30: 同步 account_id（从 state_data）
        if not session.account_id and state_data.get("account_id"):
            session.account_id = state_data["account_id"]
        # 🆕 v2.7+: 玩家主动保存 → 复活（如果之前被冷存档）
        if session.archived:
            session.archived = False
            session.archived_at = ""
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
            "account_id": session.account_id,    # 🆕 v1.7.30
            "archived": session.archived,        # 🆕 v2.7+
            "archived_at": session.archived_at,  # 🆕 v2.7+
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


# ============================================================
# 模块级工具函数
# ============================================================

def _parse_iso(iso_str: str):
    """把 ISO 时间字符串解析为 datetime（无 tz 当作本地时间）"""
    if not iso_str:
        return None
    try:
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return None
