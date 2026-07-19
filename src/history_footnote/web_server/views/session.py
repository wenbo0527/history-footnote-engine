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
    #
    # 🆕 v2.10.9 P2-2：原代码用 `from history_footnote.web_server.routers.input import _context_aware_voices`
    # 会造成 views → routers 的反向依赖（循环）。改成 inline 简化版"零 LLM 成本" 关键字匹配。
    # 等价于 routers/input.py 的 _fallback_keyword_voices()（注释里明确说 v2.3 仅在 LLM 失败时
    # 才用这个 fallback；存档加载场景无需 LLM，直接走关键字匹配）。
    if not game.state.last_voice_options:
        try:
            last = (game.state.narrative_history or [])[-1] if game.state.narrative_history else None
            if last:
                voices = _load_fallback_voices(last.get("narrative", ""))
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


# ============================================================
# 🆕 v2.10.9 P2-2: 打破 views → routers 反向依赖
#
# 原代码：views/session.py 在存档加载时 import routers/input.py 的
# _context_aware_voices()，造成 views 反向依赖 routers（循环依赖风险）。
#
# 修复：在 views 层 inline 一个简化版"零 LLM 成本" 关键字匹配，
# 逻辑等价于 routers/input.py._fallback_keyword_voices()。
# 注释里说存档加载场景"零 LLM 成本"，所以这个简化版完全够用。
# ============================================================

def _load_fallback_voices(narr_text: str) -> list:
    """存档加载时的 fallback voice_options（关键字匹配，零 LLM 成本）

    等价于 routers/input.py._fallback_keyword_voices()。
    🆕 v2.10.9 P2-2：复制一份到 views 层避免反向依赖。

    Args:
        narr_text: 最近的叙事文本

    Returns:
        list[dict]: 2-3 个 voice_options
    """
    if not narr_text:
        return []

    context_voices = []
    # 钱 / 税相关 → 算盘声
    if any(k in narr_text for k in ("银", "钱", "税", "束脩")):
        context_voices.append({
            "voice_id": "voice_accountant",
            "voice_name": "算盘声",
            "intent_text": "再盘算盘算，看能不能借到银子或换条活路",
        })
    # 官府 / 里长 → 本分
    if any(k in narr_text for k in ("官", "里长", "朝廷", "赵里长")):
        context_voices.append({
            "voice_id": "voice_compliance",
            "voice_name": "本分",
            "intent_text": "照官府说的办，别给家里招祸",
        })
    # 织布相关 → 手艺人
    if any(k in narr_text for k in ("织", "布", "丝", "织机")):
        context_voices.append({
            "voice_id": "voice_craft",
            "voice_name": "手艺人的骄傲",
            "intent_text": "把活儿做好，名声立住了自然有客来",
        })
    # 市场相关 → 生意经
    if any(k in narr_text for k in ("牙行", "王掌柜", "客商")):
        context_voices.append({
            "voice_id": "voice_market",
            "voice_name": "生意经",
            "intent_text": "问问价、比比货，总不吃亏",
        })

    # 兜底：3 个通用选项
    base_voices = [
        {"voice_id": "voice_observed", "voice_name": "先看再看", "intent_text": "不急，先把眼前事理清楚"},
        {"voice_id": "voice_action", "voice_name": "动手试", "intent_text": "先动起来，做了再说"},
        {"voice_id": "voice_ask", "voice_name": "问问人", "intent_text": "这事得问个懂行的人"},
    ]

    # 合并去重，最多 3 个
    seen = set()
    merged = []
    for v in context_voices + base_voices:
        if v["voice_id"] in seen:
            continue
        seen.add(v["voice_id"])
        merged.append(v)
        if len(merged) >= 3:
            break
    return merged
