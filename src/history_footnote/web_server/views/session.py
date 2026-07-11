"""🆕 v1.7.29 Session 视图层

_session_get / _session_set / _session_pop — 内存中 session 池的薄包装
_get_or_load_session(sid) — 优先从 pool 取；找不到从存档读
_new_session(era_id, identity, gender, custom_character) — 启动新游戏
"""
from __future__ import annotations

import logging
from pathlib import Path

from history_footnote.concurrency import SESSION_POOL
from history_footnote.resource_cache import (
    get_save_manager as get_save_manager_cached,
    load_era_config,
)
from history_footnote.game_loop import GameLoop
from history_footnote.storage.save_manager import DEFAULT_SAVE_ROOT

logger = logging.getLogger(__name__)


def _storage_root_for_account() -> Path:
    """🆕 v1.7.30 账户系统的存储根目录
    默认使用 saves/（与现有 SaveManager 共用）
    后续可改为专门的 accounts_root
    """
    return Path(DEFAULT_SAVE_ROOT)


def session_get(sid: str):
    """从全局 SESSION_POOL 拿（避免直接暴露池）"""
    return SESSION_POOL.get(sid)


def session_set(sid: str, game) -> None:
    SESSION_POOL.add(sid, game)


def session_pop(sid: str) -> None:
    SESSION_POOL.remove(sid)


def _get_or_load_session(session_id: str | None) -> GameLoop | None:
    """获取session，不存在则从存档加载"""
    if not session_id:
        return None
    entry = session_get(session_id)
    if entry is not None:
        return entry[0]

    save_manager = get_save_manager_cached()
    session = save_manager.find_session(session_id)
    if session is None:
        return None

    loaded = save_manager.load_state(session, "auto")
    if loaded is None:
        return None

    config = load_era_config(session.era_id)
    from history_footnote.llm_wrapper import get_wrapped_llm
    llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
    game = GameLoop(
        era_id=session.era_id,
        era_config=config,
        llm_model=llm,
        session=session,
        load_state_data=loaded,
    )

    # 🆕 v1.7.32 修复：存档加载后从最近 narrative 派生 voice_options。
    # 否则玩家跨页面 / 跨重启进入游戏后，脑海中的声音是空的（"暂无选项"）。
    # 复用 /api/input 路径的轻量级 _context_aware_voices（关键字匹配，零 LLM 成本）
    if not game.state.last_voice_options:
        try:
            from history_footnote.web_server.routers.input import _context_aware_voices
            last = (game.state.narrative_history or [])[-1] if game.state.narrative_history else None
            if last:
                voices = _context_aware_voices(last.get("narrative", ""))
                if voices:
                    game.state.last_voice_options = voices
                    logger.info(f"[load] 注入 {len(voices)} voice_options (context-aware from saved narrative)")
        except Exception as e:
            logger.exception(f"[load] 注入 voice_options 失败: {e}")

    session_set(session_id, game)
    return game


def new_session(era_id: str, identity: str, gender: str,
                custom_character: dict | None = None) -> GameLoop:
    """创建新 session"""
    config = load_era_config(era_id)
    from history_footnote.llm_wrapper import get_wrapped_llm
    llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
        selected_identity=identity,
        custom_character=custom_character,
    )
    if gender:
        game.state.player_gender = gender
    session_set(game.session.session_id, game)
    return game
