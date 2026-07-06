"""🆕 v1.7.29 Session 视图层

_session_get / _session_set / _session_pop — 内存中 session 池的薄包装
_get_or_load_session(sid) — 优先从 pool 取；找不到从存档读
_new_session(era_id, identity, gender, custom_character) — 启动新游戏
"""
from __future__ import annotations

import logging

from history_footnote.concurrency import SESSION_POOL
from history_footnote.resource_cache import (
    get_save_manager as get_save_manager_cached,
    load_era_config,
)
from history_footnote.game_loop import GameLoop


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
