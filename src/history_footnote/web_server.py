"""轻量Web体验入口——基于Python标准库http.server

提供：
- GET / → 体验主页（HTML+JS）
- POST /api/start → 创建新session
- POST /api/input → 玩家输入
- GET /api/state → 当前状态
- GET /api/archives → 列出存档
- POST /api/continue → 继续最近session
- POST /api/load → 加载指定session
"""
from __future__ import annotations

import json
import logging
import time  # 🆕 v1.6.2 P1 C2：SSE streaming
import sys
import threading
import uuid  # 🆕 v1.6.2 安全：错误响应 ID
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from datetime import datetime

# 让本模块在src/history_footnote/下可以独立运行
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")

from history_footnote.llm_providers import make_llm  # noqa: E402
from history_footnote.game_loop import GameLoop  # noqa: E402
from history_footnote.storage.save_manager import (  # noqa: E402
    DEFAULT_SAVE_ROOT,
    SaveManager,
    SaveSession,
)
# 🆕 v1.6+ 并发支持：复用全局 SessionPool
from history_footnote.concurrency import SESSION_POOL, LLM_THROTTLE, SAVE_QUEUE, SessionLock
# 🆕 v1.6.2 P0 优化：全局资源缓存（避免每回合重复 json.loads + LLM 构造）
from history_footnote.resource_cache import (
    load_era_config,
    get_llm,
    get_save_manager as get_save_manager_cached,
    warm_era_configs,
    clear_all_caches,
)
# 🆕 v1.6.2 P2 优化：限流 + 监控 + Tool 结果缓存
from history_footnote.web_enhancements import (
    GLOBAL_RATE_LIMITER,
    LLM_RATE_LIMITER,
    GLOBAL_METRICS,
    TOOL_RESULT_CACHE,
    setup_keepalive,
    record_request_metrics,
)


# 全局 session 池（v1.6+ 改用 SessionPool）
# 旧版 _SESSIONS dict 已被 SESSION_POOL 替代
def _session_get(sid): return SESSION_POOL.get(sid)
def _session_set(sid, game): return SESSION_POOL.add(sid, game)
def _session_pop(sid): SESSION_POOL.remove(sid)


def _format_state(game: GameLoop) -> dict:
    """序列化当前游戏状态供前端展示"""
    s = game.state
    recent_narr = []
    for nh in s.narrative_history[-3:]:
        recent_narr.append({
            "round": nh.get("round"),
            "summary": nh.get("summary", ""),
            "narrative": nh.get("narrative", ""),
        })
    return {
        "session_id": game.session.session_id,
        "era_id": game.era_id,
        "era_name": game.era_config.get("era_name", game.era_id),
        "round_number": s.round_number,
        "current_date": s.current_date,
        "action_points_current": s.action_points_current,
        "action_points_max": s.action_points_max,
        "selected_identity": s.selected_identity,
        "player_gender": s.player_gender,
        "unlocked_insights": sorted(s.unlocked_insights),
        "triggered_events": sorted(s.triggered_events),
        "variables": dict(s.variables),
        "value_shifts": dict(s.value_shifts),
        "recent_narratives": recent_narr,
        # 🐛 v1.5.1 P0 Bug #1 修复：暴露 custom_character 给前端
        "custom_character": getattr(s, "custom_character", {}),
        # 🐛 v1.5.1 P1 Issue 5 修复：暴露 last_voice_options 给前端
        "last_voice_options": list(getattr(s, "last_voice_options", []) or []),
    }


def _detect_intent_for_response(player_input: str, dm_response: dict) -> str:
    """🐛 v1.5.1 P1 Issue 6 修复：统一意图判定

    优先用 dm_skills._detect_intent_type（规则判定，更可靠），
    LLM 返回的 intent_type 仅作 fallback。
    """
    try:
        from history_footnote.dm_skills import _detect_intent_type
        rule_intent = _detect_intent_type(player_input)
        if rule_intent and rule_intent != "action":
            # 规则判定为 describe/inquire → 比 LLM 更可靠
            return rule_intent
    except Exception:
        pass
    # Fallback: LLM 返回的 intent_type
    return dm_response.get("intent_type", "action")


def _get_or_load_session(session_id: str | None) -> GameLoop | None:
    """获取session，不存在则从存档加载"""
    if not session_id:
        return None
    entry = _session_get(session_id)
    if entry is not None:
        return entry[0]

    save_manager = get_save_manager_cached()  # 🆕 v1.6.2 P0 A3: SaveManager 单例
    session = save_manager.find_session(session_id)
    if session is None:
        return None

    loaded = save_manager.load_state(session, "auto")
    if loaded is None:
        return None

    config = load_era_config(session.era_id)  # 🆕 v1.6.2 P0 A1: 缓存版
    llm = get_llm(provider="minimax-anthropic", era_config=config)  # 🆕 v1.6.2 P0 A2: LLM 缓存
    game = GameLoop(
        era_id=session.era_id,
        era_config=config,
        llm_model=llm,
        session=session,
        load_state_data=loaded,
    )
    _session_set(session_id, game)
    return game


def _new_session(era_id: str, identity: str, gender: str, custom_character: dict | None = None) -> GameLoop:
    """创建新session"""
    config = load_era_config(era_id)  # 🆕 v1.6.2 P0 A1: 缓存版
    llm = get_llm(provider="minimax-anthropic", era_config=config)  # 🆕 v1.6.2 P0 A2: LLM 缓存
    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
        selected_identity=identity,
        custom_character=custom_character,  # 🐛 v1.5.1 P0 Bug #1 修复
    )
    if gender:
        game.state.player_gender = gender
    _session_set(game.session.session_id, game)
    return game


# HTML首页（带引导界面、回合交互、状态面板）
INDEX_HTML = """<!DOCTYPE html>
<!-- v1.3.1 -->
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#f5f0e1">
<title>历史注脚·万历十五年</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  /* 🆕 v1.6.2 移动端适配：使用 dvh（dynamic viewport height）解决 iOS Safari URL 栏遮挡 */
  html, body { height: 100%; }
  body {
    font-family: "Songti SC", "SimSun", "Source Han Serif SC", serif;
    background: #f5f0e1;
    color: #2c2416;
    height: 100vh;
    height: 100dvh; /* 移动端动态高度（适配 iOS Safari URL 栏） */
    overflow: hidden;
    -webkit-text-size-adjust: 100%; /* 防止 iOS Safari 自动放大字体 */
  }
  .layout {
    display: grid;
    grid-template-columns: 1fr 320px;
    grid-template-rows: 1fr;
    height: 100vh;
    height: 100dvh; /* 🆕 v1.6.2 移动端 */
  }
  .main {
    overflow-y: auto;
    padding: 24px 32px;
    background: linear-gradient(180deg, #f5f0e1 0%, #ede4cc 100%);
    -webkit-overflow-scrolling: touch; /* 🆕 v1.6.2 iOS 弹性滚动 */
  }
  .sidebar {
    background: #2c2416;
    color: #d8c89c;
    padding: 20px;
    overflow-y: auto;
    border-left: 2px solid #8b6f47;
    -webkit-overflow-scrolling: touch; /* 🆕 v1.6.2 iOS 弹性滚动 */
  }
  .action-point-bar {
    display: flex;
    align-items: center;
    gap: 4px;
    margin: 6px 0;
  }
  .ap-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #c4a878;
    border: 1px solid #5a4a30;
  }
  .ap-dot.filled { background: #f0d8a0; box-shadow: 0 0 4px #f0d8a0; }
  .ap-label { color: #c4a878; font-size: 11px; margin-left: 4px; }
  .player-echo {
    color: #8b6f47;
    font-style: italic;
    border-left: 3px solid #c4a878;
    padding: 4px 10px;
    margin: 8px 0 4px;
    background: rgba(196, 168, 120, 0.1);
  }
  .action-tag {
    display: inline-block;
    background: #4a3820;
    color: #f0d8a0;
    padding: 3px 10px;
    margin: 6px 0;
    border-radius: 12px;
    font-size: 12px;
  }
  .action-tag.inquire { background: #2c4a3e; }
  .month-marker {
    text-align: center;
    color: #8b6f47;
    font-weight: bold;
    margin: 16px 0;
    padding: 8px;
    background: rgba(139, 111, 71, 0.1);
    border-top: 1px dashed #8b6f47;
    border-bottom: 1px dashed #8b6f47;
  }
  /* 🆕 v1.5+ DE 风格：内在声音选项 */
  .voice-options {
    background: linear-gradient(180deg, rgba(60,48,24,0.05) 0%, rgba(60,48,24,0.15) 100%);
    border: 2px solid #8b6f47;
    border-radius: 4px;
    padding: 16px;
    margin: 20px 0;
  }
  .voice-options-header {
    color: #8b6f47;
    font-weight: bold;
    font-size: 14px;
    margin-bottom: 12px;
    text-align: center;
    letter-spacing: 2px;
  }
  .voice-options-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 10px;
  }
  .voice-option-btn {
    background: rgba(255, 250, 235, 0.9);
    border: 1px solid #8b6f47;
    border-radius: 4px;
    padding: 12px 14px;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .voice-option-btn:hover {
    background: #f5e6c8;
    border-color: #c4a878;
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(139, 111, 71, 0.2);
  }
  .voice-option-btn .voice-name {
    color: #5a3e1f;
    font-weight: bold;
    font-size: 14px;
  }
  .voice-option-btn .voice-intent {
    color: #6b5b3f;
    font-size: 13px;
    line-height: 1.5;
  }
  .voice-option-btn.free-input {
    background: rgba(139, 111, 71, 0.08);
    border-style: dashed;
  }
  .voice-option-btn.free-input:hover {
    background: rgba(139, 111, 71, 0.18);
  }
  /* 🆕 v1.6+ Tab 式 UX：其他选项按钮样式（更柔和，引导用） */
  .voice-option-btn.other {
    background: rgba(60, 48, 24, 0.06);
    border-style: dashed;
    border-color: #b8a578;
    opacity: 0.85;
  }
  .voice-option-btn.other:hover {
    background: rgba(139, 111, 71, 0.15);
    border-color: #8b6f47;
    opacity: 1;
  }
  .voice-option-btn.other .voice-name {
    color: #8b6f47;
    font-style: italic;
  }
  /* 🆕 v1.6+ Tab 式 UX：自由发挥提示区 */
  .free-input-banner {
    background: linear-gradient(180deg, rgba(139,111,71,0.12) 0%, rgba(139,111,71,0.05) 100%);
    border-left: 3px solid #8b6f47;
    border-right: 1px solid #8b6f47;
    border-top: 1px solid #8b6f47;
    border-bottom: none;
    padding: 10px 14px;
    margin-top: 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-size: 13px;
  }
  .free-input-banner-text {
    color: #5a3e1f;
    font-weight: bold;
  }
  .free-input-cancel {
    background: transparent;
    border: 1px solid #8b6f47;
    color: #8b6f47;
    padding: 4px 10px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    transition: all 0.15s;
  }
  .free-input-cancel:hover {
    background: #8b6f47;
    color: #f5e6c8;
  }
  /* 🆕 v1.5+ 描述类提示 */
  .describe-tag {
    display: inline-block;
    background: #4a3e7a;
    color: #f0e8c0;
    padding: 3px 10px;
    margin: 6px 0;
    border-radius: 12px;
    font-size: 12px;
  }
  .sidebar h3 {
    font-size: 14px;
    color: #c4a878;
    margin-top: 16px;
    margin-bottom: 6px;
  }
  .sidebar .stat-line {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    font-size: 13px;
  }
  .sidebar .stat-line .label { color: #a08858; }
  .sidebar .stat-line .val { color: #f0d8a0; font-weight: bold; }
  .sidebar .insight-tag {
    display: inline-block;
    background: #4a3820;
    color: #f0d8a0;
    padding: 2px 8px;
    margin: 2px;
    border-radius: 3px;
    font-size: 12px;
  }
  .narrative {
    background: rgba(255, 250, 235, 0.7);
    border-left: 4px solid #8b6f47;
    padding: 16px 20px;
    margin: 16px 0;
    border-radius: 2px;
    line-height: 1.9;
    font-size: 16px;
    white-space: pre-wrap;
  }
  .narrative .round-tag {
    color: #8b6f47;
    font-size: 13px;
    font-weight: bold;
    margin-bottom: 8px;
  }
  .input-area {
    background: rgba(255, 250, 235, 0.9);
    border: 1px solid #8b6f47;
    border-radius: 4px;
    padding: 16px;
    margin: 20px 0;
    position: sticky;
    bottom: 0;
    z-index: 5;
    /* 🆕 v1.6.2：背景半透明 + backdrop-filter 让底部输入区更优雅 */
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
  }
  .input-area textarea {
    width: 100%;
    min-height: 70px;
    border: 1px solid #c4a878;
    background: #fff;
    font-family: inherit;
    font-size: 15px;
    padding: 8px;
    border-radius: 3px;
    resize: vertical;
  }
  .input-area .row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 8px;
  }
  .input-area button {
    background: #8b6f47;
    color: #f5f0e1;
    border: none;
    padding: 8px 24px;
    font-size: 14px;
    font-family: inherit;
    cursor: pointer;
    border-radius: 3px;
  }
  .input-area button:hover { background: #a08858; }
  .input-area button:disabled { background: #c4a878; cursor: not-allowed; }
  .input-area .hint { color: #8b6f47; font-size: 12px; }
  .start-screen {
    text-align: center;
    padding: 40px 20px;
  }
  .start-screen h1 {
    font-size: 42px;
    color: #2c2416;
    margin-bottom: 12px;
    letter-spacing: 4px;
  }
  .start-screen .subtitle {
    color: #5a4a30;
    font-size: 18px;
    margin-bottom: 32px;
  }
  .start-screen .era-desc {
    max-width: 600px;
    margin: 0 auto 32px;
    line-height: 1.8;
    text-align: left;
    color: #3c3018;
  }
  .form-group {
    max-width: 500px;
    margin: 16px auto;
    text-align: left;
  }
  .form-group label {
    display: block;
    color: #5a4a30;
    font-size: 14px;
    margin-bottom: 4px;
  }
  .form-group select, .form-group input {
    width: 100%;
    padding: 8px 12px;
    font-size: 15px;
    border: 1px solid #8b6f47;
    background: #fff;
    border-radius: 3px;
    font-family: inherit;
  }
  .btn-primary {
    background: #8b6f47;
    color: #f5f0e1;
    border: none;
    padding: 12px 36px;
    font-size: 16px;
    font-family: inherit;
    cursor: pointer;
    border-radius: 3px;
    margin: 8px;
  }
  .btn-primary:hover { background: #a08858; }
  .btn-secondary {
    background: transparent;
    color: #8b6f47;
    border: 1px solid #8b6f47;
    padding: 12px 36px;
    font-size: 16px;
    font-family: inherit;
    cursor: pointer;
    border-radius: 3px;
    margin: 8px;
  }
  .btn-secondary:hover { background: #ede4cc; }
  .archive-item {
    background: #3c3018;
    padding: 10px;
    margin: 8px 0;
    border-radius: 3px;
    font-size: 12px;
    cursor: pointer;
    border: 1px solid transparent;
  }
  .archive-item:hover { border-color: #c4a878; }
  .archive-item .ar-session { color: #f0d8a0; font-weight: bold; }
  .archive-item .ar-meta { color: #a08858; margin-top: 3px; }
  .loading {
    display: inline-block;
    color: #8b6f47;
    font-size: 13px;
  }
  .error {
    color: #c0504d;
    background: #f0d8a0;
    padding: 8px;
    border-radius: 3px;
    margin: 8px 0;
  }
  .event-tag {
    display: inline-block;
    background: #6b4423;
    color: #f0d8a0;
    padding: 2px 8px;
    margin: 2px;
    border-radius: 3px;
    font-size: 11px;
  }

  /* ============================================================ */
  /* 🆕 v1.6.2 移动端适配（响应式断点）                              */
  /* ============================================================ */

  /* 平板（≤1024px）：侧边栏变窄 */
  @media (max-width: 1024px) {
    .layout {
      grid-template-columns: 1fr 240px;
    }
    .sidebar { padding: 16px 12px; }
    .sidebar h3 { font-size: 14px; }
  }

  /* 手机横屏（≤768px）：侧边栏移到底部，主内容区独占 */
  @media (max-width: 768px) {
    .layout {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr auto;
      grid-template-areas:
        "main"
        "sidebar";
    }
    .main {
      grid-area: main;
      padding: 16px;
    }
    .sidebar {
      grid-area: sidebar;
      max-height: 35vh;        /* 侧边栏最多占屏幕 35% */
      border-left: none;
      border-top: 2px solid #8b6f47;
      padding: 12px;
    }
    /* 隐藏侧边栏内次要内容（保留：回合/日期/身份/Session/行动点）*/
    .sidebar .sidebar-secondary { display: none; }

    /* 字号适配 */
    .main { font-size: 15px; line-height: 1.7; }
    .round-tag { font-size: 14px; padding: 6px 10px; }
    .voice-options-header { font-size: 13px; letter-spacing: 1px; }
    .voice-option-btn { padding: 10px 12px; }
    .voice-option-btn .voice-name { font-size: 14px; }
    .voice-option-btn .voice-intent { font-size: 12px; }
    .input-area { padding: 12px; margin: 12px 0; }
    .input-area textarea { font-size: 16px; min-height: 60px; }  /* 16px 防 iOS 缩放 */
    .input-area button { padding: 10px 20px; font-size: 15px; min-height: 44px; min-width: 44px; }  /* 44px 触屏目标 */
    .input-area .hint { font-size: 11px; }
    .stat-line { font-size: 13px; padding: 3px 0; }
    .ap-dot { width: 12px; height: 12px; }
    .ap-label { font-size: 11px; }
    .start-screen h2 { font-size: 22px; }
    .archive-item { padding: 12px; }
    .ar-session { font-size: 14px; }
    .ar-meta { font-size: 12px; }
  }

  /* 手机竖屏（≤480px）：极致压缩 */
  @media (max-width: 480px) {
    .layout {
      grid-template-rows: 1fr auto;
    }
    .main {
      padding: 12px;
      font-size: 14px;
    }
    .sidebar {
      max-height: 30vh;
      padding: 10px;
      font-size: 12px;
    }
    .voice-options-grid {
      grid-template-columns: 1fr;  /* 选项全部堆叠为单列 */
      gap: 8px;
    }
    .input-area { padding: 10px; }
    .input-area textarea { min-height: 50px; font-size: 16px; }
    .input-area .row { flex-wrap: wrap; gap: 6px; }
    .input-area button {
      width: 100%;
      min-height: 44px;
      font-size: 15px;
    }
    .round-tag { font-size: 13px; padding: 4px 8px; }
  }

  /* 🆕 v1.6.2 iOS 键盘弹出时自适应 */
  /* 当 input-area 获得焦点时，确保它在可视区域内 */
  .input-area:focus-within {
    position: relative;
    z-index: 10;
  }

  /* ============================================================ */
  /* 🆕 v1.6.3 剧情回顾（按钮 + 弹层）                             */
  /* ============================================================ */
  .recap-btn {
    position: fixed;
    top: 16px;
    right: 16px;
    background: rgba(60, 48, 24, 0.92);
    color: #f5f0e1;
    border: 2px solid #8b6f47;
    border-radius: 24px;
    padding: 8px 16px;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    z-index: 50;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
  }
  .recap-btn:hover {
    background: rgba(90, 72, 36, 0.95);
    transform: translateY(-1px);
  }
  .recap-modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 100;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }
  .recap-modal {
    background: #f5f0e1;
    color: #2c2416;
    border: 2px solid #8b6f47;
    border-radius: 8px;
    max-width: 700px;
    width: 100%;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }
  .recap-header {
    padding: 16px 20px;
    border-bottom: 1px solid #c4a878;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  .recap-header h2 {
    margin: 0;
    color: #5a3e1f;
    font-size: 20px;
  }
  .recap-meta {
    flex: 1;
    color: #8b6f47;
    font-size: 12px;
  }
  .recap-close {
    background: none;
    border: none;
    color: #5a3e1f;
    font-size: 28px;
    cursor: pointer;
    line-height: 1;
    padding: 0 8px;
  }
  .recap-close:hover { color: #a08858; }
  .recap-body-content {
    padding: 16px 20px;
    overflow-y: auto;
    flex: 1;
    -webkit-overflow-scrolling: touch;
  }
  .recap-body-content section { margin-bottom: 24px; }
  .recap-body-content h3 {
    color: #5a3e1f;
    font-size: 15px;
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 1px dashed #c4a878;
  }
  .recap-entry {
    margin: 8px 0;
    padding: 8px 12px;
    background: rgba(255, 250, 235, 0.7);
    border-left: 3px solid #8b6f47;
    border-radius: 3px;
  }
  .recap-entry summary {
    cursor: pointer;
    color: #5a3e1f;
    font-weight: bold;
    user-select: none;
    padding: 4px 0;
  }
  .recap-entry summary:hover { color: #a08858; }
  .recap-entry[open] {
    background: rgba(255, 250, 235, 0.95);
  }
  .recap-body {
    padding: 8px 0 4px;
    line-height: 1.7;
    color: #2c2416;
    font-size: 14px;
  }
  .recap-archive-item {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 6px 12px;
    margin: 4px 0;
    background: rgba(255, 250, 235, 0.5);
    border-left: 2px solid #c4a878;
    border-radius: 3px;
    font-size: 13px;
  }
  .recap-round {
    color: #8b6f47;
    font-weight: bold;
    min-width: 70px;
    font-size: 12px;
  }
  .recap-summary {
    color: #5a4a30;
    line-height: 1.5;
  }
  .recap-empty {
    color: #8b6f47;
    font-style: italic;
    padding: 12px;
    text-align: center;
  }

  /* 移动端优化 */
  @media (max-width: 768px) {
    .recap-btn {
      top: auto;
      bottom: calc(env(safe-area-inset-bottom, 0) + 90px); /* 在 input-area 上方 */
      right: 12px;
      font-size: 12px;
      padding: 6px 12px;
    }
    .recap-modal-overlay {
      padding: 0;
      align-items: stretch;
    }
    .recap-modal {
      max-width: 100%;
      max-height: 100vh;
      max-height: 100dvh;
      border-radius: 0;
      border-left: none;
      border-right: none;
    }
    .recap-header {
      position: sticky;
      top: 0;
      background: #f5f0e1;
      z-index: 1;
    }
    .recap-entry {
      font-size: 13px;
    }
    .recap-body {
      font-size: 13px;
    }
  }

  /* ============================================================ */
  /* 🆕 v1.6.6 侧边栏动作按钮 + 名词表 + tooltip 高亮              */
  /* ============================================================ */
  .sidebar-actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #5a4a30;
  }
  .sidebar-action-btn {
    background: rgba(196, 168, 120, 0.2);
    color: #f0d8a0;
    border: 1px solid #8b6f47;
    border-radius: 4px;
    padding: 10px 12px;
    font-family: inherit;
    font-size: 13px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
  }
  .sidebar-action-btn:hover {
    background: rgba(196, 168, 120, 0.4);
    border-color: #c4a878;
  }

  /* 名词高亮（首次出现） */
  .term-new {
    color: #a08858;
    border-bottom: 1.5px dashed #c4a878;
    cursor: help;
    position: relative;
    padding: 1px 2px;
    border-radius: 2px;
    transition: background 0.2s;
  }
  .term-new:hover {
    background: rgba(196, 168, 120, 0.25);
  }
  .term-new::after {
    content: " ?";
    font-size: 10px;
    color: #c4a878;
    font-weight: bold;
    vertical-align: super;
  }

  /* Tooltip 弹层 */
  .term-tooltip {
    position: absolute;
    background: #2c2416;
    color: #f0d8a0;
    padding: 10px 12px;
    border-radius: 6px;
    border: 1px solid #8b6f47;
    max-width: 280px;
    font-size: 12px;
    line-height: 1.5;
    z-index: 200;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    pointer-events: none;
  }
  .term-tooltip .term-name {
    color: #f0d8a0;
    font-weight: bold;
    font-size: 14px;
    margin-bottom: 4px;
  }
  .term-tooltip .term-cat {
    color: #c4a878;
    font-size: 11px;
    font-weight: normal;
    margin-left: 6px;
  }
  .term-tooltip .term-def {
    color: #d8c89c;
    font-size: 12px;
    margin-bottom: 4px;
  }
  .term-tooltip .term-example {
    color: #a08858;
    font-style: italic;
    font-size: 11px;
    margin-top: 4px;
  }
  .term-tooltip .term-related {
    color: #c4a878;
    font-size: 11px;
    margin-top: 4px;
  }

  /* 名词表弹层（复用 recap-modal 样式） */
  .glossary-search {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid #8b6f47;
    border-radius: 4px;
    font-family: inherit;
    font-size: 14px;
    background: #fff;
    margin-bottom: 12px;
  }
  .glossary-search:focus {
    outline: none;
    border-color: #5a3e1f;
  }
  .glossary-list {
    display: grid;
    gap: 12px;
    grid-template-columns: 1fr;
  }
  @media (min-width: 600px) {
    .glossary-list {
      grid-template-columns: 1fr 1fr;
    }
  }
  .glossary-item {
    padding: 10px;
    background: rgba(255, 250, 235, 0.7);
    border-left: 3px solid #8b6f47;
    border-radius: 3px;
  }
  .glossary-item .term-name {
    color: #5a3e1f;
    font-weight: bold;
    margin-right: 6px;
  }
  .glossary-item .term-cat {
    color: #a08858;
    font-size: 11px;
  }
  .glossary-item .term-def {
    color: #2c2416;
    font-size: 13px;
    margin-top: 4px;
    line-height: 1.5;
  }
  .glossary-read {
    border-left-color: #c4a878;
    opacity: 0.7;
  }

  /* ============================================================ */
  /* 🆕 v1.6.8 版本号常驻 + 反馈弹层                              */
  /* ============================================================ */
  .version-badge {
    position: fixed;
    bottom: 8px;
    right: 12px;
    background: rgba(60, 48, 24, 0.75);
    color: #f0d8a0;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    cursor: pointer;
    z-index: 30;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border: 1px solid rgba(196, 168, 120, 0.4);
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
    transition: all 0.2s;
  }
  .version-badge:hover {
    background: rgba(60, 48, 24, 0.92);
    border-color: #c4a878;
    transform: translateY(-1px);
  }
  .version-badge .version-text {
    font-weight: bold;
    letter-spacing: 0.3px;
  }
  .version-badge .version-hint {
    opacity: 0.7;
    font-size: 10px;
  }

  /* 反馈弹层（独立于 recap/glossary，因为样式特殊） */
  .feedback-form {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .feedback-categories {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  @media (max-width: 600px) {
    .feedback-categories {
      grid-template-columns: 1fr;
    }
  }
  .feedback-cat-btn {
    background: rgba(196, 168, 120, 0.15);
    color: #5a3e1f;
    border: 1px solid #8b6f47;
    border-radius: 4px;
    padding: 10px;
    font-family: inherit;
    font-size: 13px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
  }
  .feedback-cat-btn:hover {
    background: rgba(196, 168, 120, 0.3);
  }
  .feedback-cat-btn.selected {
    background: #8b6f47;
    color: #f5f0e1;
    border-color: #5a3e1f;
  }
  .feedback-textarea {
    min-height: 120px;
    padding: 10px;
    border: 1px solid #8b6f47;
    border-radius: 4px;
    font-family: inherit;
    font-size: 14px;
    line-height: 1.5;
    resize: vertical;
    background: #fff;
  }
  .feedback-textarea:focus {
    outline: none;
    border-color: #5a3e1f;
  }
  .feedback-context-note {
    font-size: 11px;
    color: #8b6f47;
    background: rgba(196, 168, 120, 0.1);
    padding: 8px 10px;
    border-radius: 3px;
    line-height: 1.5;
  }
  .feedback-submit-row {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }
  .feedback-submit-btn {
    background: #8b6f47;
    color: #f5f0e1;
    border: none;
    border-radius: 4px;
    padding: 10px 24px;
    font-family: inherit;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
  }
  .feedback-submit-btn:hover {
    background: #5a3e1f;
  }
  .feedback-submit-btn:disabled {
    background: #c4a878;
    cursor: not-allowed;
  }
  .feedback-success {
    color: #2d5016;
    background: rgba(108, 152, 76, 0.15);
    padding: 12px;
    border-radius: 4px;
    text-align: center;
  }
</style>
</head>
<body>
<div class="layout">
  <div class="main" id="main"></div>
  <div class="sidebar" id="sidebar"></div>
</div>

<!-- 🆕 v1.6.9 版本号常驻显示（内测标识） -->
<div id="version-badge" class="version-badge" onclick="openFeedback()">
  <span class="version-text">v1.6.9 - 内测版</span>
  <span class="version-hint">🐛 反馈</span>
</div>

<script>
let state = {
  session_id: null,
  identity: null,
  gender: null,
  era_id: "wanli1587",
};

const $main = document.getElementById("main");
const $side = document.getElementById("sidebar");

async function api(path, method = "GET", body = null) {
  const opts = { method, headers: {"Content-Type": "application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch(path, opts);
  return await resp.json();
}

let wizard = {
  step: 1,  // 1-8
  era_id: "wanli1587",
  era_data: null,
  gender: null,
  location: null,      // 盛泽镇内的具体位置
  identity_description: "",
  life_expectation: "",
  character: null,    // LLM 生成的人设
  world_dwell: null,  // LLM 生成的世界画卷
};

const STEP_TITLES = [
  "", // step 0 unused
  "1. 选择时代",        // step 1
  "2. 世界画卷",        // step 2
  "3. 选择性别",        // step 3
  "4. 选择你的位置",    // step 4 NEW
  "5. 描述你的身份",    // step 5
  "6. 描述期望生活",    // step 6
  "7. AI 生成人设",     // step 7
  "8. 确认 / 开始",     // step 8
];

// 盛泽镇内的具体位置（基于 era.json 知识条目）
const SHENGZE_LOCATIONS = [
  {
    id: "family_workshop",
    name: "自家织坊",
    icon: "🏠",
    desc: "镇中巷子里的两台织机，前面是作坊，后头是灶房。你和家人住在这里。",
    traits: "最经典的小织户起点——日常就是织布、卖丝、纳粮、应付催税的里长。",
    default: true,
  },
  {
    id: "yaxing_east",
    name: "镇东牙行",
    icon: "🏪",
    desc: "王掌柜的牙行在镇东头，你在这里做事——帮忙看丝、议价、跑腿。",
    traits: "更接近商业。容易听到行情、客商的传闻，但议价和催账是你的日常压力。",
  },
  {
    id: "market_west",
    name: "镇西市集",
    icon: "🛒",
    desc: "卖桑叶、染料、丝线的市集，茶馆也在这里。",
    traits: "市井气息最浓。各种小道消息、邻居闲聊、季节变化都在这里。",
  },
  {
    id: "sang_field",
    name: "镇外桑田",
    icon: "🌱",
    desc: "盛泽镇外几亩桑田，靠种桑养蚕为生。",
    traits: "更农耕。节奏跟着季节走，春蚕三眠、夏剪枝、冬埋根，辛苦但稳。",
  },
  {
    id: "rented_house",
    name: "租住的平房",
    icon: "🏚️",
    desc: "新近迁来盛泽镇，没有自己的作坊，租了间平房安身。",
    traits: "外来者视角。对镇上的事情不熟，没有织机，但也没有历史包袱——可以从头来。",
  },
  {
    id: "li_jia_house",
    name: "里长老宅",
    icon: "🏛️",
    desc: "里长家的偏院，你在这里帮工（或是里长的亲戚）。",
    traits: "离权力更近——知道镇上谁家纳了税、谁家出了事，但也被里长看得紧。",
  },
];

function renderStart() {
  wizard.step = 1;
  renderWizard();
}

function renderWizard() {
  $side.innerHTML = "<h2>开始游戏</h2>" +
    "<p style='color:#a08858;font-size:12px;line-height:1.7'>" +
    "本体验调用真实 Minimax LLM，每步调用约 5-15 秒。<br>" +
    "设计灵感来自《极乐迪斯科》：<br>" +
    "· 内在声音（你脑海中的声音）<br>" +
    "· 失败也是叙事<br>" +
    "· 行动点系统（耗尽才跳月）" +
    "</p>";
  $main.innerHTML = renderWizardStep(wizard.step);
  attachWizardHandlers();
}

function renderWizardStep(step) {
  let html = `<div class="start-screen">`;
  html += `<div style="color:#8b6f47;font-size:13px;margin-bottom:8px">${STEP_TITLES[step]}</div>`;
  html += `<h1 style="font-size:32px;margin-bottom:24px">历史注脚</h1>`;

  if (step === 1) {
    // Step 1: 选择时代
    html += `<div id="era-list">加载中…</div>`;
    html += `<div style="margin-top:24px"><button class="btn-secondary" onclick="renderWizardStep(0);showArchives()">继续存档</button></div>`;
  } else if (step === 2) {
    // Step 2: 世界画卷
    if (!wizard.world_dwell) {
      html += `<div id="dwell-area"><span class="loading">⏳ 正在绘制「${wizard.era_data?.name || '...'}」的世界画卷…</span></div>`;
    } else {
      html += renderWorldDwell(wizard.world_dwell);
      html += `<div style="margin-top:24px;text-align:center">
        <button class="btn-primary" onclick="wizard.step=3;renderWizard()">继续</button>
      </div>`;
    }
  } else if (step === 3) {
    // Step 3: 选择性别
    html += `
      <div class="form-group" style="max-width:400px">
        <label>你是男是女？</label>
        <div style="display:flex;gap:16px;margin-top:8px">
          <button class="btn-secondary" style="flex:1" onclick="wizard.gender='male';wizard.step=4;renderWizard()">男</button>
          <button class="btn-secondary" style="flex:1" onclick="wizard.gender='female';wizard.step=4;renderWizard()">女</button>
        </div>
      </div>`;
  } else if (step === 4) {
    // Step 4: 选择位置（盛泽镇内的具体地点）
    html += `
      <div style="max-width:600px;margin:0 auto;text-align:left">
        <div style="text-align:center;color:#5a4a30;margin-bottom:16px;line-height:1.7">
          你的故事将发生在 <strong style="color:#8b6f47">苏州府吴江县盛泽镇</strong>——
          万历年间江南最繁华的丝织市镇之一。<br>
          选一个你的「位置」，这决定你日常接触的人和事。
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px">`;
    SHENGZE_LOCATIONS.forEach(loc => {
      html += `<div class="archive-item" style="cursor:pointer" onclick='selectLocation("${loc.id}")'>
        <div class="ar-session" style="font-size:15px">${loc.icon} ${escapeHtml(loc.name)}</div>
        <div class="ar-meta" style="margin-top:4px;line-height:1.5">${escapeHtml(loc.desc)}</div>
        <div class="ar-meta" style="color:#8b6f47;margin-top:4px;font-style:italic">${escapeHtml(loc.traits)}</div>
      </div>`;
    });
    html += `</div></div>`;
  } else if (step === 5) {
    // Step 5: 描述身份
    html += `
      <div class="form-group" style="max-width:500px;margin:0 auto">
        <label>你是谁？用一两句话描述你的身份/来历</label>
        <div style="margin-top:4px;color:#8b6f47;font-size:12px">
          你的位置：<strong>${getLocationName(wizard.location)}</strong>
        </div>
        <textarea id="identity_desc" rows="3" style="width:100%;padding:8px;font-size:14px;font-family:inherit;border:1px solid #8b6f47;background:#fff;border-radius:3px;margin-top:8px"
          placeholder="例：盛泽镇的小织户 / 从福建逃难来的破产绸缎商人 / 准备科举的穷书生 / 嫁到本地的年轻媳妇"></textarea>
        <div style="margin-top:8px;color:#8b6f47;font-size:12px">可选：留空将由 AI 自由发挥</div>
      </div>
      <div style="margin-top:16px;text-align:center">
        <button class="btn-secondary" onclick="wizard.step=4;renderWizard()">← 改位置</button>
        <button class="btn-primary" onclick="wizard.identity_description=document.getElementById('identity_desc').value;wizard.step=6;renderWizard()">继续</button>
      </div>`;
  } else if (step === 6) {
    // Step 6: 期望生活
    html += `
      <div class="form-group" style="max-width:500px;margin:0 auto">
        <label>你想体验什么样的生活？</label>
        <textarea id="life_exp" rows="3" style="width:100%;padding:8px;font-size:14px;font-family:inherit;border:1px solid #8b6f47;background:#fff;border-radius:3px"
          placeholder="例：想体验小商贩的挣扎求生 / 想做点小生意改变命运 / 想安安稳稳养大孩子 / 想看看万历的繁华与崩塌"></textarea>
        <div style="margin-top:8px;color:#8b6f47;font-size:12px">可选：留空将由 AI 推测</div>
      </div>
      <div style="margin-top:16px;text-align:center">
        <button class="btn-secondary" onclick="wizard.step=5;renderWizard()">← 改身份</button>
        <button class="btn-primary" onclick="wizard.life_expectation=document.getElementById('life_exp').value;wizard.step=7;renderWizard()">继续</button>
      </div>`;
  } else if (step === 7) {
    // Step 7: AI 生成人设
    if (!wizard.character) {
      html += `<div id="char-area"><span class="loading">⏳ AI 正在根据你的描述生成专属人设…</span></div>`;
    } else {
      html += renderCharacter(wizard.character);
      html += `<div style="margin-top:24px;text-align:center">
        <button class="btn-secondary" onclick="generateCharacter()">🔄 重新生成</button>
        <button class="btn-primary" onclick="wizard.step=8;renderWizard()">确认</button>
      </div>`;
    }
  } else if (step === 8) {
    // Step 8: 确认/开始
    if (!wizard.character) {
      html += `<div class="error">请先生成人设</div>`;
    } else {
      html += renderCharacter(wizard.character);
      html += `<div style="margin-top:24px;text-align:center">
        <button class="btn-secondary" onclick="wizard.step=5;renderWizard()">← 修改身份</button>
        <button class="btn-primary" onclick="startGame()">开始游戏 →</button>
      </div>`;
    }
  }

  html += `</div>`;
  return html;
}

function renderWorldDwell(d) {
  let html = `<div style="max-width:600px;margin:0 auto;text-align:left;font-family:serif;line-height:1.9;color:#2c2416">`;
  html += `<h2 style="text-align:center;color:#8b6f47;margin-bottom:24px;letter-spacing:4px">${escapeHtml(d.title || '世界画卷')}</h2>`;
  (d.paragraphs || []).forEach(p => {
    html += `<p style="margin-bottom:12px;text-indent:2em">${escapeHtml(p)}</p>`;
  });
  if (d.key_themes && d.key_themes.length) {
    html += `<div style="margin-top:20px;padding:12px;background:rgba(139,111,71,0.1);border-radius:4px">
      <strong>时代主题：</strong>${d.key_themes.map(t => `<span class="insight-tag" style="background:#8b6f47;color:#f5f0e1;padding:2px 8px;margin:2px;border-radius:3px;display:inline-block">${escapeHtml(t)}</span>`).join('')}
    </div>`;
  }
  html += `</div>`;
  return html;
}

function renderCharacter(c) {
  let html = `<div style="max-width:600px;margin:0 auto;text-align:left;line-height:1.8">`;
  html += `<h2 style="text-align:center;color:#8b6f47">${escapeHtml(c.name || '无名氏')}</h2>`;
  if (c.hometown) html += `<div style="text-align:center;color:#5a4a30;font-size:14px">${escapeHtml(c.hometown)} · ${c.age || '?'}岁</div>`;
  if (c.background) html += `<div style="margin:16px 0;padding:12px;background:rgba(139,111,71,0.08);border-left:3px solid #8b6f47">${escapeHtml(c.background)}</div>`;
  if (c.personality) html += `<div style="margin:8px 0"><strong>性格：</strong>${escapeHtml(c.personality)}</div>`;
  if (c.tics) html += `<div style="margin:8px 0"><strong>习惯：</strong>${escapeHtml(c.tics)}</div>`;
  if (c.family) {
    html += `<div style="margin:8px 0"><strong>家庭：</strong><br>`;
    // 🆕 v1.6.5 修复：把英文 key 翻译成人话 + 数组格式化成自然语言
    const familyKeyLabels = {
      spouse: "妻子",
      husband: "丈夫",
      children: "子女",
      elderly: "老人",
      siblings: "兄弟姐妹",
      parents: "父母",
      father: "父亲",
      mother: "母亲",
    };
    for (const [k, v] of Object.entries(c.family)) {
      const label = familyKeyLabels[k] || k;
      let display;
      if (Array.isArray(v)) {
        display = v.map(item => escapeHtml(String(item))).join("、");
      } else if (typeof v === 'string') {
        display = escapeHtml(v);
      } else if (v && typeof v === 'object') {
        display = escapeHtml(JSON.stringify(v));
      } else {
        display = escapeHtml(String(v));
      }
      html += `· <span style="color:#5a4a30">${escapeHtml(label)}：</span>${display}<br>`;
    }
    html += `</div>`;
  }
  if (c.starting_situation) html += `<div style="margin:8px 0;padding:8px;background:rgba(196,168,120,0.15);border-radius:3px"><strong>开局处境：</strong>${escapeHtml(c.starting_situation)}</div>`;
  if (c.voices && c.voices.length) {
    html += `<div style="margin:16px 0"><strong>🎭 内在声音：</strong>`;
    c.voices.forEach(v => {
      html += `<div style="margin:6px 0;padding:8px;background:rgba(60,48,24,0.85);color:#f0d8a0;border-radius:3px">
        <strong>${escapeHtml(v.name || '?')}</strong> <span style="color:#a08858;font-size:11px">(${escapeHtml(v.trigger || '')})</span><br>
        <span style="font-size:13px">${escapeHtml(v.description || '')}</span><br>
        <span style="color:#c4a878;font-size:12px;font-style:italic">「${escapeHtml(v.first_words || '')}」</span>
      </div>`;
    });
    html += `</div>`;
  }
  if (c.skills && c.skills.length) {
    html += `<div style="margin:16px 0"><strong>⚔️ 初始技能：</strong>`;
    c.skills.forEach(s => {
      const stars = "★".repeat(s.level || 1) + "☆".repeat(5 - (s.level || 1));
      html += `<div style="margin:4px 0">${stars} <strong>${escapeHtml(s.name || '?')}</strong> <span style="color:#8b6f47;font-size:12px">— ${escapeHtml(s.description || '')}</span></div>`;
    });
    html += `</div>`;
  }
  if (c.opening_paragraph) {
    html += `<div style="margin:16px 0;padding:12px;background:rgba(60,48,24,0.05);border-radius:3px">
      <strong>📜 开场白：</strong><br>${escapeHtml(c.opening_paragraph)}
    </div>`;
  }
  html += `</div>`;
  return html;
}

async function attachWizardHandlers() {
  if (wizard.step === 1) {
    const data = await api("/api/eras");
    const $el = document.getElementById("era-list");
    $el.innerHTML = data.eras.map(e => `
      <div class="archive-item" onclick='selectEra("${e.id}", ${JSON.stringify(e).replace(/'/g, "&#39;")})'>
        <div class="ar-session">${escapeHtml(e.name)} <span style="color:#a08858;font-size:12px">(${escapeHtml(e.year_range)})</span></div>
        <div class="ar-meta">${escapeHtml(e.description || '')}</div>
        <div class="ar-meta">可选身份：${e.identities_count} 个</div>
      </div>
    `).join("");
  } else if (wizard.step === 2) {
    if (!wizard.world_dwell && !wizard._generating_dwell) {
      wizard._generating_dwell = true;
      const data = await api("/api/generate_world_dwell", "POST", {era_id: wizard.era_id});
      wizard._generating_dwell = false;
      if (data.error) {
        const $el = document.getElementById("dwell-area");
        if ($el) $el.innerHTML = "<div class='error'>" + data.error + "</div>";
      } else {
        wizard.world_dwell = data.world_dwell;
        // 用局部重渲染避免触发 attachWizardHandlers
        const $main = document.getElementById("main");
        $main.innerHTML = renderWizardStep(2);
      }
    }
  } else if (wizard.step === 7) {
    if (!wizard.character && !wizard._generating_character) {
      // 不 await（fire-and-forget），让 generateCharacter 自己管理渲染
      generateCharacter().catch(err => console.error("generateCharacter failed:", err));
    }
  }
}

async function selectEra(era_id, era_data) {
  wizard.era_id = era_id;
  wizard.era_data = era_data;
  wizard.world_dwell = null;
  wizard.character = null;
  wizard.step = 2;
  renderWizard();
}

function getLocationName(loc_id) {
  if (!loc_id) return "未选择";
  const loc = SHENGZE_LOCATIONS.find(l => l.id === loc_id);
  return loc ? loc.icon + " " + loc.name : loc_id;
}

function getLocationDescription(loc_id) {
  const loc = SHENGZE_LOCATIONS.find(l => l.id === loc_id);
  return loc ? loc.desc + " " + loc.traits : "";
}

async function selectLocation(loc_id) {
  wizard.location = loc_id;
  wizard.character = null;  // 改了位置就重置人设
  wizard.step = 5;
  renderWizard();
}

async function generateCharacter() {
  // 防止重入：如果已经在生成中，直接返回
  if (wizard._generating_character) return;
  wizard._generating_character = true;

  wizard.character = null;
  // 重新渲染（显示"生成中"）
  if (wizard.step === 7) {
    const $main = document.getElementById("main");
    $main.innerHTML = renderWizardStep(7);
  }

  try {
    const data = await api("/api/generate_character", "POST", {
      era_id: wizard.era_id,
      gender: wizard.gender,
      location: wizard.location,
      location_description: getLocationDescription(wizard.location),
      identity_description: wizard.identity_description,
      life_expectation: wizard.life_expectation,
    });
    if (data.error) {
      const $el = document.getElementById("char-area");
      if ($el) $el.innerHTML = "<div class='error'>" + data.error + "</div>";
    } else {
      wizard.character = data.character;
      // 重新渲染 step 7 显示结果（不重新 attach，因为 character 已设置）
      if (wizard.step === 7) {
        const $main = document.getElementById("main");
        $main.innerHTML = renderWizardStep(7);
      }
    }
  } finally {
    wizard._generating_character = false;
  }
}

// 🐛 Bug #3 修复：位置 → identity 映射
// 6 个 SHENGZE_LOCATIONS 对应 era.json 6 个 identity
const LOCATION_TO_IDENTITY = {
  "family_workshop": {"male": "weaving_male", "female": "weaving_female"},   // 自家织坊 → 织户
  "yaxing_east":     {"male": "merchant_male", "female": "merchant_female"},// 镇东牙行 → 商人
  "market_west":     {"male": "merchant_male", "female": "merchant_female"},// 镇西市集 → 商人
  "sang_field":      {"male": "weaving_male", "female": "weaving_female"},   // 镇外桑田 → 织户
  "rented_house":    {"male": "weaving_male", "female": "weaving_female"},   // 租住平房 → 织户（外来者）
  "li_jia_house":    {"male": "scholar_male", "female": "scholar_female"},   // 里长老宅 → 读书人
};

async function startGame() {
  // 🐛 Bug #3 修复：根据位置 + 性别 选择对应 identity
  let identity = "default";
  if (wizard.era_id === "wanli1587") {
    const map = LOCATION_TO_IDENTITY[wizard.location] || LOCATION_TO_IDENTITY["family_workshop"];
    identity = map[wizard.gender] || map["male"];
  }
  state.gender = wizard.gender;
  state.identity = identity;
  state.era_id = wizard.era_id;
  state.location = wizard.location;
  const data = await api("/api/start", "POST", {era_id: wizard.era_id, identity, gender: wizard.gender, character: wizard.character});
  if (data.error) {
    alert(data.error);
    return;
  }
  state.session_id = data.session_id;
  renderGame(data);
}

async function showArchives() {
  const data = await api("/api/archives?era_id=" + state.era_id);
  let html = "<div class='start-screen'><h2>存档列表</h2><div style='max-width:500px;margin:0 auto;text-align:left'>";
  if (data.archives.length === 0) {
    html += "<p style='color:#5a4a30;text-align:center'>暂无存档</p>";
  } else {
    data.archives.forEach(a => {
      html += `<div class='archive-item' onclick='loadArchive("${a.session_id}")'>
        <div class='ar-session'>${a.session_id}</div>
        <div class='ar-meta'>${a.current_date} · 第${a.current_round}回合 · 进度摘要: ${a.summary}</div>
        <div class='ar-meta'>身份: ${a.selected_identity} (${a.player_gender})</div>
      </div>`;
    });
  }
  html += "<div style='text-align:center;margin-top:24px'><button class='btn-secondary' onclick='renderStart()'>返回</button></div></div>";
  $main.innerHTML = html;
}

async function loadArchive(session_id) {
  const data = await api("/api/load", "POST", {session_id});
  if (data.error) {
    alert(data.error);
    return;
  }
  state.session_id = session_id;
  state.gender = data.player_gender;
  state.identity = data.selected_identity;
  renderGame(data);
}

// 🆕 v1.6.2 移动端适配：iOS 键盘弹出时滚动到输入区
function setupMobileKeyboardFix() {
  if (window.visualViewport) {
    const onResize = () => {
      // 当键盘弹出时，visualViewport.height < window.innerHeight
      const $inputArea = document.getElementById("input-area");
      if (!$inputArea) return;
      // 让 input-area 跟随键盘顶部位置
      const keyboardTop = window.visualViewport.height;
      const $layout = document.querySelector(".layout");
      if ($layout) {
        $layout.style.height = keyboardTop + "px";
      }
    };
    window.visualViewport.addEventListener("resize", onResize);
    window.visualViewport.addEventListener("scroll", onResize);
  }
}
setupMobileKeyboardFix();

function renderGame(data) {
  renderSidebar(data);
  $main.innerHTML = "";
  appendOpening(data);
  appendInputArea();
  // 🆕 v1.5.1 P0 Bug #2 修复：开局渲染 voice_options
  // 如果是加载存档且有 last_voice_options，复用它；否则用预定义开局选项
  if (data.last_voice_options && data.last_voice_options.length > 0) {
    appendVoiceOptions(data.last_voice_options);
  } else {
    appendOpeningVoiceOptions(data);
  }
  // 🆕 v1.6.6 侧边栏内已集成剧情回顾按钮（不再用浮动按钮）
}

async function openRecap() {
  const data = await api("/api/recap", "POST", {
    session_id: state.session_id,
    recent_count: 10,
    archive_count: 50,
  });
  if (data.error) {
    alert("回顾失败：" + data.error);
    return;
  }
  renderRecapModal(data);
}

function renderRecapModal(recap) {
  // 移除旧弹层
  const existing = document.getElementById("recap-modal");
  if (existing) existing.remove();

  const recent = recap.recent || [];
  const archive = recap.archive || [];

  const recentHtml = recent.length === 0 ? "<p class='recap-empty'>尚无最近叙事</p>" :
    recent.map(n => `<details class="recap-entry">
      <summary>第 ${n.round} 回合${n.summary ? ' · ' + escapeHtml(n.summary.slice(0, 30)) : ''}</summary>
      <div class="recap-body">${escapeHtml(n.narrative || '').replace(/\n/g, "<br>")}</div>
    </details>`).join("");

  const archiveHtml = archive.length === 0 ? "<p class='recap-empty'>尚无早期记录</p>" :
    archive.slice().reverse().map(n => `<div class="recap-archive-item">
      <span class="recap-round">第 ${n.round} 回合</span>
      <span class="recap-summary">${escapeHtml(n.summary || n.narrative_preview || '')}</span>
    </div>`).join("");

  const modal = document.createElement("div");
  modal.id = "recap-modal";
  modal.className = "recap-modal-overlay";
  modal.onclick = (e) => {
    if (e.target === modal) closeRecap();
  };
  modal.innerHTML = `
    <div class="recap-modal" onclick="event.stopPropagation()">
      <div class="recap-header">
        <h2>📖 剧情回顾</h2>
        <span class="recap-meta">第 ${recap.round_number} 回合 · ${recap.current_date} · 共 ${recap.total_narratives} 条记录</span>
        <button class="recap-close" onclick="closeRecap()">×</button>
      </div>
      <div class="recap-body-content">
        <section>
          <h3>📜 最近 ${recent.length} 回合（详细）</h3>
          ${recentHtml}
        </section>
        <section>
          <h3>📚 早期记录（${archive.length} 条摘要）</h3>
          ${archiveHtml}
        </section>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

function closeRecap() {
  const existing = document.getElementById("recap-modal");
  if (existing) existing.remove();
}

// ============================================================
// 🆕 v1.6.6 明朝名词表（侧边栏入口 + 全局 tooltip）
// ============================================================

async function openGlossary() {
  // 打开名词表弹层（默认列出全部）
  const data = await api("/api/glossary", "POST", {query: ""});
  if (data.error) {
    alert("名词表加载失败：" + data.error);
    return;
  }
  renderGlossaryModal(data);
}

function renderGlossaryModal(data) {
  const existing = document.getElementById("glossary-modal");
  if (existing) existing.remove();

  const items = (data.terms || []).map(t => `
    <div class="glossary-item" data-term="${escapeHtml(t.key)}" onclick="showTermDetail('${escapeHtml(t.key)}')">
      <span class="term-name">${escapeHtml(t.key)}</span>
      <span class="term-cat">[${escapeHtml(t.category)}]</span>
      <div class="term-def">${escapeHtml(t.definition)}</div>
    </div>
  `).join("");

  const modal = document.createElement("div");
  modal.id = "glossary-modal";
  modal.className = "recap-modal-overlay";
  modal.onclick = (e) => { if (e.target === modal) closeGlossary(); };
  modal.innerHTML = `
    <div class="recap-modal" onclick="event.stopPropagation()">
      <div class="recap-header">
        <h2>📚 明朝名词表</h2>
        <span class="recap-meta">共 ${data.total_in_dict} 个名词 · 显示 ${data.count} 个</span>
        <button class="recap-close" onclick="closeGlossary()">×</button>
      </div>
      <div class="recap-body-content">
        <input type="text" class="glossary-search" id="glossary-search-input"
          placeholder="🔍 搜索名词（如：牙行、湖丝、科举...）" oninput="filterGlossary(this.value)" />
        <div class="glossary-list" id="glossary-list">${items || '<p class="recap-empty">未找到匹配名词</p>'}</div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  // 自动 focus 搜索框
  setTimeout(() => {
    const inp = document.getElementById("glossary-search-input");
    if (inp) inp.focus();
  }, 100);
}

function closeGlossary() {
  const existing = document.getElementById("glossary-modal");
  if (existing) existing.remove();
}

// ============================================================
// 🆕 v1.6.8 玩家反馈入口（侧边栏 + 版本号点击触发）
// ============================================================
let _selectedCategory = "bug";  // 默认分类

async function openFeedback() {
  // 拉取分类列表
  const data = await api("/api/feedback_categories", "POST", {});
  if (data.error) {
    alert("反馈入口加载失败：" + data.error);
    return;
  }
  renderFeedbackModal(data.categories);
}

function renderFeedbackModal(categories) {
  const existing = document.getElementById("feedback-modal");
  if (existing) existing.remove();

  const catButtons = categories.map(c => `
    <button class="feedback-cat-btn ${c.key === _selectedCategory ? 'selected' : ''}"
            data-key="${c.key}" onclick="selectFeedbackCategory('${c.key}')">
      ${c.label}
    </button>
  `).join("");

  const selectedCat = categories.find(c => c.key === _selectedCategory);
  const placeholder = selectedCat ? selectedCat.placeholder : "描述你遇到的问题...";

  const modal = document.createElement("div");
  modal.id = "feedback-modal";
  modal.className = "recap-modal-overlay";
  modal.onclick = (e) => { if (e.target === modal) closeFeedback(); };
  modal.innerHTML = `
    <div class="recap-modal" onclick="event.stopPropagation()" style="max-width:560px">
      <div class="recap-header">
        <h2>🐛 问题反馈</h2>
        <span class="recap-meta">${categories.length} 种分类 · 自动收集上下文</span>
        <button class="recap-close" onclick="closeFeedback()">×</button>
      </div>
      <div class="recap-body-content">
        <div class="feedback-form" id="feedback-form-body">
          <label style="font-size:13px;color:#5a3e1f;font-weight:bold">问题分类：</label>
          <div class="feedback-categories">${catButtons}</div>
          <label style="font-size:13px;color:#5a3e1f;font-weight:bold">详细描述：</label>
          <textarea class="feedback-textarea" id="feedback-description"
            placeholder="${escapeHtml(placeholder)}"></textarea>
          <div class="feedback-context-note" id="feedback-context-note">
            📋 自动收集：当前回合、日期、浏览器、屏幕尺寸、最近 3 个玩家操作。<br>
            你的反馈将包含一个会话 ID（不会包含个人身份信息）。
          </div>
          <div class="feedback-submit-row">
            <button class="sidebar-action-btn" style="background:transparent;color:#5a3e1f;width:auto;display:inline-block"
              onclick="closeFeedback()">取消</button>
            <button class="feedback-submit-btn" id="feedback-submit-btn" onclick="submitFeedback()">提交反馈</button>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

function closeFeedback() {
  const existing = document.getElementById("feedback-modal");
  if (existing) existing.remove();
}

function selectFeedbackCategory(key) {
  _selectedCategory = key;
  // 更新 UI
  document.querySelectorAll(".feedback-cat-btn").forEach(btn => {
    btn.classList.toggle("selected", btn.dataset.key === key);
  });
  // 更新 placeholder（异步从服务端拉取最新 placeholder）
  api("/api/feedback_categories", "POST", {}).then(data => {
    if (data.categories) {
      const cat = data.categories.find(c => c.key === key);
      if (cat) {
        const textarea = document.getElementById("feedback-description");
        if (textarea) textarea.placeholder = cat.placeholder;
      }
    }
  });
}

async function submitFeedback() {
  const desc = document.getElementById("feedback-description").value.trim();
  if (!desc) {
    alert("请填写描述");
    return;
  }
  if (desc.length < 5) {
    alert("描述过短（至少 5 字符）");
    return;
  }

  // 收集上下文
  const context = {
    round: state.round || 0,
    date: state.current_date || "unknown",
    user_agent: navigator.userAgent,
    screen: `${window.screen.width}x${window.screen.height}`,
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    timestamp: new Date().toISOString(),
    // 玩家最近 3 个输入（从 state 读）
    recent_inputs: (state.recent_inputs || []).slice(-3),
  };

  // 禁用按钮
  const btn = document.getElementById("feedback-submit-btn");
  btn.disabled = true;
  btn.textContent = "提交中...";

  try {
    const result = await api("/api/feedback", "POST", {
      session_id: state.session_id || "",
      category: _selectedCategory,
      description: desc,
      context: context,
    });

    if (result.error) {
      alert("提交失败：" + result.error);
      btn.disabled = false;
      btn.textContent = "提交反馈";
      return;
    }

    // 成功
    const formBody = document.getElementById("feedback-form-body");
    formBody.innerHTML = `
      <div class="feedback-success">
        ✅ 反馈已收到！<br>
        <small>ID: ${result.id}</small><br>
        <small style="color:#8b6f47">开发团队会查看并处理。</small>
      </div>
      <div class="feedback-submit-row">
        <button class="feedback-submit-btn" onclick="closeFeedback()">关闭</button>
      </div>
    `;
  } catch (e) {
    alert("网络错误：" + e.message);
    btn.disabled = false;
    btn.textContent = "提交反馈";
  }
}

// 🆕 v1.6.8 页面加载时拉取版本信息更新 badge
async function loadVersionBadge() {
  try {
    const info = await api("/api/version", "POST", {});
    if (info && info.full_label) {
      const textEl = document.querySelector("#version-badge .version-text");
      if (textEl) textEl.textContent = info.full_label;
    }
  } catch (e) {
    // 静默失败，使用 HTML 模板里的默认值
  }
}
// 在页面加载完成后调用
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", loadVersionBadge);
} else {
  loadVersionBadge();
}

async function filterGlossary(query) {
  // 客户端过滤：避免每次都打 API
  const data = await api("/api/glossary", "POST", {query: query});
  const list = document.getElementById("glossary-list");
  if (!list) return;
  if (data.error || !data.terms) {
    list.innerHTML = '<p class="recap-empty">加载失败</p>';
    return;
  }
  list.innerHTML = data.terms.map(t => `
    <div class="glossary-item" data-term="${escapeHtml(t.key)}" onclick="showTermDetail('${escapeHtml(t.key)}')">
      <span class="term-name">${escapeHtml(t.key)}</span>
      <span class="term-cat">[${escapeHtml(t.category)}]</span>
      <div class="term-def">${escapeHtml(t.definition)}</div>
    </div>
  `).join("") || '<p class="recap-empty">未找到匹配名词</p>';
}

async function showTermDetail(key) {
  const data = await api("/api/glossary", "POST", {term: key});
  if (data.error) {
    alert("未找到：" + key);
    return;
  }
  // 标记已读
  if (state.session_id) {
    api("/api/mark_term_seen", "POST", {
      session_id: state.session_id,
      term: key,
    }).catch(() => {});
  }
  // 显示弹层
  showTermTooltipInline(data);
}

function showTermTooltipInline(termData) {
  const existing = document.getElementById("term-detail-modal");
  if (existing) existing.remove();

  const example = termData.example ? `<div class="term-example">例：${escapeHtml(termData.example)}</div>` : "";
  const related = (termData.related && termData.related.length)
    ? `<div class="term-related">相关：${termData.related.map(r => `<span class="term-name" style="font-size:12px">${escapeHtml(r)}</span>`).join("、")}</div>`
    : "";

  const modal = document.createElement("div");
  modal.id = "term-detail-modal";
  modal.className = "recap-modal-overlay";
  modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
  modal.innerHTML = `
    <div class="recap-modal" onclick="event.stopPropagation()" style="max-width:480px">
      <div class="recap-header">
        <h2><span class="term-name">${escapeHtml(termData.key)}</span> <span class="term-cat">[${escapeHtml(termData.category)}]</span></h2>
        <button class="recap-close" onclick="document.getElementById('term-detail-modal').remove()">×</button>
      </div>
      <div class="recap-body-content">
        <div class="term-def" style="font-size:14px;line-height:1.7;color:#2c2416">${escapeHtml(termData.definition)}</div>
        ${example}
        ${related}
        <div style="margin-top:16px;text-align:right">
          <button class="sidebar-action-btn" style="background:rgba(139,111,71,0.15);color:#5a3e1f;display:inline-block;width:auto"
            onclick="document.getElementById('term-detail-modal').remove()">知道了</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

// 给叙事中所有 .term-new 元素绑定 tooltip 事件
function attachTermTooltips() {
  document.querySelectorAll(".term-new").forEach(el => {
    if (el.dataset.tooltipBound) return;
    el.dataset.tooltipBound = "1";
    el.addEventListener("mouseenter", async (e) => {
      const term = el.dataset.term;
      if (!term) return;
      const data = await api("/api/glossary", "POST", {term: term});
      if (data.error) return;
      // 标记已读
      if (state.session_id) {
        api("/api/mark_term_seen", "POST", {
          session_id: state.session_id,
          term: term,
        }).catch(() => {});
      }
      // 显示 tooltip
      let tooltip = document.getElementById("term-tooltip");
      if (!tooltip) {
        tooltip = document.createElement("div");
        tooltip.id = "term-tooltip";
        tooltip.className = "term-tooltip";
        document.body.appendChild(tooltip);
      }
      const example = data.example ? `<div class="term-example">例：${escapeHtml(data.example)}</div>` : "";
      tooltip.innerHTML = `
        <div class="term-name">${escapeHtml(data.key)} <span class="term-cat">[${escapeHtml(data.category)}]</span></div>
        <div class="term-def">${escapeHtml(data.definition)}</div>
        ${example}
      `;
      // 定位
      const rect = el.getBoundingClientRect();
      tooltip.style.left = (rect.left + window.scrollX) + "px";
      tooltip.style.top = (rect.bottom + window.scrollY + 6) + "px";
      tooltip.style.display = "block";
    });
    el.addEventListener("mouseleave", () => {
      const tooltip = document.getElementById("term-tooltip");
      if (tooltip) tooltip.style.display = "none";
    });
  });
}

function appendOpeningVoiceOptions(data) {
  // 🐛 v1.5.1 P0 Bug #2 修复：开局的 DE 风格选项（基于开局处境）
  // 这些是"你脑海中的声音"——基于玩家人设给 2-3 个开局方向
  const cc = data.custom_character || {};
  const openingOptions = [
    {
      voice_id: "voice_observe",
      voice_name: "先看看家里情况",
      intent_text: "我先扫一眼家里有什么，银钱还剩多少，灶房是什么光景",
    },
    {
      voice_id: "voice_action",
      voice_name: "出门找活路",
      intent_text: "我去牙行问问最近有没有活计可接",
    },
    {
      voice_id: "voice_moral",
      voice_name: "先顾眼前",
      intent_text: "我想想今天的米缸还够不够，今天必须先吃饱",
    },
  ];
  appendVoiceOptions(openingOptions);
}

function appendOpening(data) {
  const nh = data.recent_narratives || [];
  nh.forEach(n => appendNarrative(n, null));
}

function appendNarrative(n, lastMeta) {
  const div = document.createElement("div");
  div.className = "narrative";
  let tag = `<div class="round-tag">第${n.round}回合 · ${n.summary || ""}</div>`;
  if (lastMeta && lastMeta.player_input) {
    tag = `<div class="player-echo">> ${escapeHtml(lastMeta.player_input)}</div>` + tag;
  }
  // 🆕 v1.5+：describe/intent_type 标签
  if (lastMeta && lastMeta.intent_type === "describe") {
    tag += `<div class="describe-tag">🪞 描述（你在补充身份/处境，不消耗行动点）</div>`;
  } else if (lastMeta && lastMeta.intent_type === "voice") {
    tag += `<div class="describe-tag">🎭 内在声音（${escapeHtml(state._selectedVoice?.voice_name || '?')}）</div>`;
  } else if (lastMeta && lastMeta.is_action === false) {
    tag += `<div class="action-tag inquire">💬 问询（不消耗行动点）</div>`;
  } else if (lastMeta && lastMeta.time_cost !== undefined) {
    const cost = lastMeta.time_cost;
    const costLabel = cost === 0 ? "瞬时" : cost === 1 ? "半日" : cost === 2 ? "一日" : cost === 3 ? "数日" : `${cost}点`;
    tag += `<div class="action-tag">⚡ 行动 · 消耗 ${cost} 点（${costLabel}）</div>`;
  }
  if (lastMeta && lastMeta.month_advanced) {
    tag = `<div class="month-marker">━━━ 行动点耗尽，进入 ${lastMeta.new_date} ━━━</div>` + tag;
  }
  // 🆕 v1.6.7 架构重构：前端不再本地清洗，统一调 /api/sanitize
  // 服务端 narrative_sanitizer.py 是单一权威（前后端共用）
  const rawNarrative = n.narrative || "";
  api("/api/sanitize", "POST", {text: rawNarrative}).then(sanitizeData => {
    const cleanedNarrative = (sanitizeData && !sanitizeData.error)
      ? sanitizeData.cleaned
      : rawNarrative;
    const narrativeText = escapeHtml(cleanedNarrative);
    div.innerHTML = tag + `<div class="narrative-body" data-round="${n.round}">${narrativeText}</div>`;
    $main.insertBefore(div, $main.lastElementChild);
    // 异步请求后端提取名词（标记未读词）
    if (state.session_id) {
      api("/api/extract_terms", "POST", {
        session_id: state.session_id,
        text: cleanedNarrative,
      }).then(data => {
        if (data.error || !data.new_terms || data.new_terms.length === 0) return;
        const $body = div.querySelector(".narrative-body");
        if ($body) {
          $body.innerHTML = data.marked_text;
          attachTermTooltips();
        }
      }).catch(() => {});
    }
  }).catch(() => {
    // 兜底：sanitize API 失败时直接显示原文
    div.innerHTML = tag + `<div class="narrative-body" data-round="${n.round}">${escapeHtml(rawNarrative)}</div>`;
    $main.insertBefore(div, $main.lastElementChild);
  });
}

function appendInputArea() {
  const div = document.createElement("div");
  div.className = "input-area";
  div.id = "input-area";
  div.innerHTML = `
    <textarea id="player_input" placeholder="或自由输入（你想做什么/想描述什么都可以）  ⏎ 直接回车提交 · Shift+Enter 换行"></textarea>
    <div class="row">
      <span class="hint">/help 查看元指令 · /state 查看状态 · /save slot1 存档</span>
      <button id="btn_submit" onclick="submitInput()">行动</button>
    </div>
    <div id="submit_msg"></div>
  `;
  $main.appendChild(div);
  document.getElementById("player_input").focus();
  // 🆕 v1.6.5 快捷键：
  // - Enter（裸键）       → 提交（移动端友好，没 Ctrl 键）
  // - Shift+Enter / Alt+Enter → 换行（多行输入）
  // - Ctrl+Enter / Cmd+Enter → 提交（兼容桌面用户习惯）
  document.getElementById("player_input").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey && !e.altKey) {
      // 裸 Enter 提交
      e.preventDefault();
      submitInput();
    } else if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      // Ctrl/Cmd+Enter 提交（兼容）
      e.preventDefault();
      submitInput();
    }
    // Shift+Enter / Alt+Enter 默认行为：插入换行
  });
}

// 🆕 v1.6.9 重置输入框 placeholder 为默认
function resetInputPlaceholder() {
  const $ta = document.getElementById("player_input");
  if ($ta) {
    $ta.placeholder = "或自由输入（你想做什么/想描述什么都可以）";
    $ta.value = "";
  }
}

function appendVoiceOptions(voiceOptions) {
  // 🆕 v1.6+ Tab 式 UX：先显示 2-4 个选项 + 「其他」按钮
  // 点「其他」后才展开自由输入框，避免玩家直接打字跳过选项
  if (!voiceOptions || voiceOptions.length === 0) return;
  const div = document.createElement("div");
  div.className = "voice-options";
  div.id = "voice-options";
  div.innerHTML = `
    <div class="voice-options-header">🎭 你脑海中的声音——选择按哪个行动</div>
    <div class="voice-options-grid">
      ${voiceOptions.map((opt, i) => `
        <button class="voice-option-btn" onclick="submitVoiceOption(${i}, ${JSON.stringify(opt).replace(/"/g, '&quot;')})">
          <span class="voice-name">${escapeHtml(opt.voice_name || '?')}</span>
          <span class="voice-intent">${escapeHtml(opt.intent_text || '?')}</span>
        </button>
      `).join("")}
      <button class="voice-option-btn other" onclick="showFreeInputTab()">
        <span class="voice-name">✍️ 其他...</span>
        <span class="voice-intent">如果都不对，自己描述要做什么</span>
      </button>
    </div>
  `;
  // 🐛 Issue #4 修复：voice_options 应该插到 input_area 之前
  const $inputArea = document.getElementById("input-area");
  if ($inputArea && $main.contains($inputArea)) {
    $main.insertBefore(div, $inputArea);
  } else {
    $main.appendChild(div);
  }
}

function showFreeInputTab() {
  // 🆕 v1.6+ Tab 式 UX：玩家点「其他」后展开自由输入框
  // 1. 隐藏选项区（避免视觉混乱）
  const $opts = document.getElementById("voice-options");
  if ($opts) $opts.style.display = "none";

  // 2. 在 input-area 上方插入一个"自由发挥"提示区
  const $inputArea = document.getElementById("input-area");
  if ($inputArea && !$main.querySelector(".free-input-banner")) {
    const banner = document.createElement("div");
    banner.className = "free-input-banner";
    banner.innerHTML = `
      <span class="free-input-banner-text">✍️ 自由发挥 — 自己描述要做什么</span>
      <button class="free-input-cancel" onclick="cancelFreeInput()">← 返回选项</button>
    `;
    $main.insertBefore(banner, $inputArea);
  }

  // 3. 聚焦输入框 + 自动滚动到底部
  const $ta = document.getElementById("player_input");
  if ($ta) {
    $ta.focus();
    $ta.placeholder = "（自由发挥）想做什么 / 想说什么？例：我要去乡试考场亲眼看看……";
  }
  $main.scrollTop = $main.scrollHeight;
}

function cancelFreeInput() {
  // 🆕 v1.6+：玩家可以「← 返回选项」回到选项区
  const $opts = document.getElementById("voice-options");
  if ($opts) $opts.style.display = "";

  const $banner = $main.querySelector(".free-input-banner");
  if ($banner) $banner.remove();

  const $ta = document.getElementById("player_input");
  if ($ta) {
    $ta.placeholder = "或自由输入（你想做什么/想描述什么都可以）";
    $ta.value = "";
  }
}

async function submitVoiceOption(index, opt) {
  // 🆕 v1.5+：玩家点击内在声音选项 → 用 intent_text 作为输入
  // 🐛 Issue #3 修复：双击防护
  if (state._submitting) return;
  const inputText = (opt.intent_text || (opt.voice_name + "的想法")).trim();
  if (!inputText) {
    console.warn("Empty intent_text in voice option", opt);
    return;
  }
  state._submitting = true;
  state._selectedVoice = opt;
  await submitInputWithText(inputText);
  state._submitting = false;
}

async function submitInputWithText(inputText) {
  const $btn = document.getElementById("btn_submit");
  if ($btn) {
    $btn.disabled = true;
    $btn.innerHTML = "<span class='loading'>⏳ DM 正在叙述...</span>";
  }
  const data = await api("/api/input", "POST", {session_id: state.session_id, input: inputText});
  if ($btn) {
    $btn.disabled = false;
    $btn.innerHTML = "行动";
  }
  if (data.error) {
    const $m = document.getElementById("submit_msg");
    if ($m) $m.innerHTML = "<div class='error'>" + data.error + "</div>";
    return;
  }
  renderSidebar(data);
  if (data.last_narrative) {
    const lastMeta = {
      player_input: inputText,
      is_action: data.last_is_action,
      time_cost: data.last_time_cost,
      intent_type: data.last_intent_type,
      month_advanced: data.last_month_advanced,
      new_date: data.last_new_date,
    };
    appendNarrative(data.last_narrative, lastMeta);
  }
  // 🆕 v1.5+：渲染新一轮的内在声音选项
  // 🐛 v1.6+ 修复：先清理旧选项区 + 旧 banner，避免重复
  const oldVoice = document.getElementById("voice-options");
  if (oldVoice) oldVoice.remove();
  const oldBanner = $main.querySelector(".free-input-banner");
  if (oldBanner) oldBanner.remove();

  if (data.last_voice_options && data.last_voice_options.length > 0) {
    appendVoiceOptions(data.last_voice_options);
  } else {
    // 🆕 v1.6.9：voice_options 为空时，async 调服务端从 narrative 提取
    // 双保险：后端 game_loop 已处理一次，这里前端再兜底一次
    if (data.last_narrative) {
      extractInlineOptionsFromText(data.last_narrative).then(opts => {
        if (opts && opts.length > 0) {
          appendVoiceOptions(opts);
          return;
        }
        // 真没找到 → 重置输入框
        resetInputPlaceholder();
      });
    } else {
      resetInputPlaceholder();
    }
  }
  $main.scrollTop = $main.scrollHeight;
}

async function submitInput() {
  // 🐛 Issue #3 修复：双击防护
  if (state._submitting) return;
  const $ta = document.getElementById("player_input");
  const input = $ta.value.trim();
  if (!input) return;
  $ta.value = "";
  state._submitting = true;
  const $btn = document.getElementById("btn_submit");
  $btn.disabled = true;
  $btn.innerHTML = "<span class='loading'>⏳ DM 正在叙述...</span>";
  const data = await api("/api/input", "POST", {session_id: state.session_id, input});
  $btn.disabled = false;
  $btn.innerHTML = "行动";
  if (data.error) {
    document.getElementById("submit_msg").innerHTML = "<div class='error'>" + data.error + "</div>";
    return;
  }
  renderSidebar(data);
  if (data.last_narrative) {
    const lastMeta = {
      player_input: input,
      is_action: data.last_is_action,
      time_cost: data.last_time_cost,
      intent_type: data.last_intent_type,
      month_advanced: data.last_month_advanced,
      new_date: data.last_new_date,
    };
    appendNarrative(data.last_narrative, lastMeta);
  }
  // 🆕 v1.5+：渲染新一轮的内在声音选项
  // 🐛 v1.6+ 修复：清理旧选项区 + banner（Tab 式 UX 一致）
  const oldVoice = document.getElementById("voice-options");
  if (oldVoice) oldVoice.remove();
  const oldBanner = $main.querySelector(".free-input-banner");
  if (oldBanner) oldBanner.remove();

  if (data.last_voice_options && data.last_voice_options.length > 0) {
    appendVoiceOptions(data.last_voice_options);
  } else {
    // 没有新选项 → 重置 placeholder
    $ta.placeholder = "或自由输入（你想做什么/想描述什么都可以）";
    $ta.value = "";
  }
  document.getElementById("submit_msg").innerHTML = "";
  $main.scrollTop = $main.scrollHeight;
  // 🐛 Issue #3 修复：解锁
  state._submitting = false;
}

function renderSidebar(data) {
  const v = data.variables || {};
  const apCur = data.action_points_current ?? 3;
  const apMax = data.action_points_max ?? 3;
  let apDots = "";
  for (let i = 0; i < apMax; i++) {
    apDots += `<div class="ap-dot${i < apCur ? " filled" : ""}"></div>`;
  }
  $side.innerHTML = `
    <h2>${data.era_name || "万历十五年"}</h2>
    <div class="stat-line"><span class="label">回合</span><span class="val">${data.round_number}</span></div>
    <div class="stat-line"><span class="label">日期</span><span class="val">${data.current_date}</span></div>
    <div class="stat-line"><span class="label">身份</span><span class="val">${data.selected_identity || "?"} (${data.player_gender || "?"})</span></div>
    <div class="stat-line"><span class="label">Session</span><span class="val" style="font-size:11px">${(data.session_id || "").slice(-8)}</span></div>

    <h3>本月行动点</h3>
    <div class="action-point-bar">${apDots}<span class="ap-label">${apCur}/${apMax}</span></div>
    <div style="color:#a08858;font-size:11px;line-height:1.5;margin-top:4px">
      ⚡ 行动点耗尽时自动跳到下月。<br>
      💬 问询/观察不消耗行动点，可继续追问。
    </div>

    <div class="sidebar-secondary"> <!-- 🆕 v1.6.2 移动端隐藏次要信息 -->
      <h3>已解锁认知 (${(data.unlocked_insights || []).length}/14)</h3>
      <div>${(data.unlocked_insights || []).map(i => `<span class="insight-tag">${i}</span>`).join("") || "<span style='color:#5a4a30;font-size:12px'>尚无</span>"}</div>

      <h3>已触发事件 (${(data.triggered_events || []).length})</h3>
      <div>${(data.triggered_events || []).map(e => `<span class="event-tag">${e}</span>`).join("") || "<span style='color:#5a4a30;font-size:12px'>尚无</span>"}</div>

      <h3>关键变量</h3>
      ${Object.entries(v).map(([k, val]) =>
        `<div class="stat-line"><span class="label">${k}</span><span class="val">${val}</span></div>`
      ).join("")}
    </div>

    <!-- 🆕 v1.6.6 侧边栏底部快捷按钮（剧情回顾 + 名词表） -->
    <div class="sidebar-actions">
      <button class="sidebar-action-btn" onclick="openRecap()" title="查看最近剧情回顾">
        📖 剧情回顾
      </button>
      <button class="sidebar-action-btn" onclick="openGlossary()" title="查看明朝名词解释">
        📚 名词表
      </button>
    </div>
  `;
}

function escapeHtml(s) {
  if (!s) return "";
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// 🆕 v1.6.7 架构重构：删除 JS 端 stripSkillMetadata（重复实现）
// 改用 /api/sanitize 端点调用服务端 narrative_sanitizer.py
// 服务端是单一权威实现，避免前后端正则漂移

// 🆕 v1.6.9 前端兜底：调用服务端 merge_voice_options（避免 JS 重复实现）
async function extractInlineOptionsFromText(text) {
  if (!text) return [];
  try {
    const data = await api("/api/merge_voice_options", "POST", {
      structured_options: [],
      narrative_text: text,
    });
    return data.options || [];
  } catch (e) {
    return [];
  }
}

renderStart();
</script>
</body>
</html>
"""

# 🆕 v1.6.2 安全：统一 logger（错误响应落日志，不返回 traceback 给前端）
logger = logging.getLogger("history_footnote.web_server")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默

    def _gzip_if_accepted(self, body: bytes) -> bytes:
        """🆕 v1.6.2 P1 A7：如果客户端支持 GZIP，返回压缩后的 body"""
        accept_encoding = self.headers.get("Accept-Encoding", "")
        if "gzip" in accept_encoding.lower() and len(body) > 1024:
            import gzip
            return gzip.compress(body, compresslevel=6)
        return body

    def _json(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        body = self._gzip_if_accepted(body)  # 🆕 v1.6.2 A7
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if body[:2] == b'\x1f\x8b':  # gzip magic
            self.send_header("Content-Encoding", "gzip")
        # 🆕 v1.6.2 A8: Cache-Control
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str):
        body = html.encode("utf-8")
        body = self._gzip_if_accepted(body)  # 🆕 v1.6.2 A7
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if body[:2] == b'\x1f\x8b':  # gzip magic
            self.send_header("Content-Encoding", "gzip")
        # 🆕 v1.6.2 A8: 静态 HTML 可以缓存
        self.send_header("Cache-Control", "public, max-age=300")  # 5 分钟
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        # 🆕 v1.6.2 P2 D6：请求限流（防 DDoS）
        import time as _time
        _t0 = _time.time()
        client_ip = self.client_address[0]
        if not GLOBAL_RATE_LIMITER.allow(client_ip):
            self._json(429, {"error": "Too Many Requests", "limit": "60 req/min"})
            return

        if path == "/" or path == "/index.html":
            self._html(INDEX_HTML)
            return
        if path == "/metrics":
            # 🆕 v1.6.2 监控面板：返回 JSON 格式的性能指标
            self._json(200, GLOBAL_METRICS.snapshot())
            return
        if path == "/health":
            # 健康检查端点
            self._json(200, {"status": "ok", "version": "1.6.2"})
            return
        if path == "/api/eras":
            # 列出所有可用时代包（含摘要）
            try:
                out = []
                for era_dir in (_ROOT / "eras").iterdir():
                    if era_dir.is_dir() and not era_dir.name.startswith(("_", ".")):
                        era_json = era_dir / "era.json"
                        if era_json.exists():
                            # 🆕 v1.6.2 P0 A1：用全局缓存替代 json.loads
                            config = load_era_config(era_dir.name)
                            timeline = config.get("world", {}).get("timeline", {})
                            out.append({
                                "id": config.get("era_id", era_dir.name),
                                "name": config.get("era_name", "未命名"),
                                "version": config.get("version", "?"),
                                "year_range": f"{timeline.get('start', {}).get('year', '?')}-{timeline.get('end', {}).get('year', '?')}",
                                "description": timeline.get("description", "")[:200],
                                "identities_count": len(config.get("world", {}).get("player_identities", {})),
                            })
                self._json(200, {"eras": out})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if path == "/api/identities":
            qs = parse_qs(urlparse(self.path).query)
            era_id = qs.get("era_id", ["wanli1587"])[0]
            try:
                config = load_era_config(era_id)  # 🆕 v1.6.2 P0 A1: 缓存版
                ids = config.get("world", {}).get("player_identities", {})
                out = [{"id": k, "label": v.get("label", k), "role": v.get("role", ""), "gender": v.get("gender")}
                       for k, v in ids.items()]
                self._json(200, {"identities": out})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return
        if path == "/api/archives":
            qs = parse_qs(urlparse(self.path).query)
            era_id = qs.get("era_id", [None])[0]
            save_manager = get_save_manager_cached()  # 🆕 v1.6.2 P0 A3: SaveManager 单例
            sessions = save_manager.list_sessions(era_id=era_id)
            out = []
            for s in sessions[:10]:
                out.append({
                    "session_id": s.session_id,
                    "era_id": s.era_id,
                    "current_round": s.current_round,
                    "current_date": s.current_date,
                    "summary": s.summary,
                    "selected_identity": s.selected_identity,
                    "player_gender": s.player_gender,
                })
            self._json(200, {"archives": out})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        # 🆕 v1.6.2 P2 D6：POST 请求限流（更严，LLM 端点特殊限流）
        import time as _time
        _t0 = _time.time()
        client_ip = self.client_address[0]
        if not GLOBAL_RATE_LIMITER.allow(client_ip):
            self._json(429, {"error": "Too Many Requests", "limit": "60 req/min"})
            return

        try:
            if path == "/api/generate_character":
                # 玩家输入自由描述 → LLM 生成完整人设
                era_id = data.get("era_id", "wanli1587")
                gender = data.get("gender", "male")
                location = data.get("location", "")
                location_desc = data.get("location_description", "")
                identity_desc = data.get("identity_description", "")
                life_exp = data.get("life_expectation", "")
                try:
                    config = load_era_config(era_id)  # 🆕 v1.6.2 P0 A1: 缓存版
                    from history_footnote.character_generator import build_character_prompt, parse_character_response
                    prompt = build_character_prompt(config, gender, identity_desc, life_exp, location=location, location_desc=location_desc)
                    llm = get_llm(provider="minimax-anthropic", era_config=config)  # 🆕 v1.6.2 P0 A2: LLM 缓存
                    from langchain_core.messages import SystemMessage, HumanMessage
                    resp = llm.invoke([
                        SystemMessage(content="你是人设生成助手。严格按 JSON 格式输出。"),
                        HumanMessage(content=prompt),
                    ])
                    parsed = parse_character_response(resp.content)
                    self._json(200, {"character": parsed, "raw": resp.content})
                except Exception as e:
                    # 🆕 v1.6.2 安全：返回通用错误 + error_id
                    error_id = str(uuid.uuid4())[:8]
                    logger.exception(f"[error_id={error_id}] generate_character failed: {e}")
                    self._json(500, {"error": "character generation failed", "error_id": error_id})
                return

            if path == "/api/generate_world_dwell":
                # 生成「世界画卷」
                era_id = data.get("era_id", "wanli1587")
                try:
                    config = load_era_config(era_id)  # 🆕 v1.6.2 P0 A1: 缓存版
                    from history_footnote.character_generator import build_world_dwell_prompt, parse_world_dwell
                    prompt = build_world_dwell_prompt(config)
                    llm = get_llm(provider="minimax-anthropic", era_config=config)  # 🆕 v1.6.2 P0 A2: LLM 缓存
                    from langchain_core.messages import SystemMessage, HumanMessage
                    resp = llm.invoke([
                        SystemMessage(content="你是世界画卷绘制师。严格按 JSON 格式输出。"),
                        HumanMessage(content=prompt),
                    ])
                    parsed = parse_world_dwell(resp.content)
                    self._json(200, {"world_dwell": parsed, "raw": resp.content})
                except Exception as e:
                    # 🆕 v1.6.2 安全：返回通用错误 + error_id
                    error_id = str(uuid.uuid4())[:8]
                    logger.exception(f"[error_id={error_id}] world_dwell failed: {e}")
                    self._json(500, {"error": "world dwell generation failed", "error_id": error_id})
                return

            if path == "/api/lore":
                # 游戏内查 lore（脱剧情）
                sid = data.get("session_id")
                topic = data.get("topic", "")
                if not sid or not topic:
                    self._json(400, {"error": "missing session_id or topic"})
                    return
                if _session_get(sid) is None:
                    game = _get_or_load_session(sid)
                    if game is None:
                        self._json(404, {"error": "session not found"})
                        return
                entry = _session_get(sid)
                game = entry[0]
                lock = entry[1]
                try:
                    from history_footnote.knowledge_base import KnowledgeBase
                    kb = game.knowledge_base
                    results = kb.search(topic, top_k=5) if hasattr(kb, "search") else []
                    self._json(200, {"topic": topic, "results": results})
                except Exception as e:
                    self._json(500, {"error": str(e)})
                return

            if path == "/api/start":
                era_id = data.get("era_id", "wanli1587")
                identity = data.get("identity", "weaving_male")
                gender = data.get("gender", "male")
                custom_character = data.get("character")  # 🐛 v1.5.1 P0 Bug #1 修复
                game = _new_session(era_id, identity, gender, custom_character=custom_character)
                # 捕获开场白到 narrative_history（用 StringIO 重定向）
                import io
                from contextlib import redirect_stdout
                buf = io.StringIO()
                with redirect_stdout(buf):
                    game._print_opening()
                opening_text = buf.getvalue().strip()
                if opening_text:
                    game.state.append_narrative(0, opening_text, "开场")
                self._json(200, {
                    "session_id": game.session.session_id,
                    **_format_state(game),
                })
                return

            if path == "/api/recap":
                # 🆕 v1.6.3 剧情回顾（增强叙事保留后可用）
                sid = data.get("session_id")
                recent_count = data.get("recent_count", 5)
                archive_count = data.get("archive_count", 30)
                if not sid:
                    self._json(400, {"error": "missing session_id"})
                    return
                entry = _session_get(sid)
                if entry is None:
                    self._json(404, {"error": "session not found or not loaded"})
                    return
                game = entry[0]
                try:
                    recap = game.state.get_recap(
                        recent_count=int(recent_count),
                        archive_count=int(archive_count),
                    )
                    self._json(200, recap)
                except Exception as e:
                    logger.exception(f"[recap] failed: {e}")
                    self._json(500, {"error": "recap failed", "error_id": str(uuid.uuid4())[:8]})
                return

            if path == "/api/glossary":
                # 🆕 v1.6.6 明朝名词字典查询
                query = data.get("query", "")
                term_key = data.get("term", "")
                try:
                    if term_key:
                        # 单个名词查询
                        from history_footnote.term_glossary import get_term, get_term_html
                        term = get_term(term_key)
                        if not term:
                            self._json(404, {"error": "term not found"})
                            return
                        self._json(200, {
                            "key": term_key,
                            "category": term["category"],
                            "definition": term["definition"],
                            "example": term.get("example", ""),
                            "related": term.get("related", []),
                            "html": get_term_html(term_key),
                        })
                    else:
                        # 搜索/列表
                        from history_footnote.term_glossary import search_terms, TERM_GLOSSARY
                        keys = search_terms(query, limit=50)
                        terms_data = []
                        for k in keys:
                            t = TERM_GLOSSARY[k]
                            terms_data.append({
                                "key": k,
                                "category": t["category"],
                                "definition": t["definition"][:80] + ("…" if len(t["definition"]) > 80 else ""),
                            })
                        self._json(200, {
                            "query": query,
                            "count": len(terms_data),
                            "terms": terms_data,
                            "total_in_dict": len(TERM_GLOSSARY),
                        })
                except Exception as e:
                    logger.exception(f"[glossary] failed: {e}")
                    self._json(500, {"error": "glossary query failed", "error_id": str(uuid.uuid4())[:8]})
                return

            if path == "/api/extract_terms":
                # 🆕 v1.6.6 从叙事文本提取名词
                text = data.get("text", "")
                if not text:
                    self._json(400, {"error": "missing text"})
                    return
                sid = data.get("session_id")
                seen = []
                if sid:
                    entry = _session_get(sid)
                    if entry:
                        seen = entry[0].state.seen_terms or []
                try:
                    from history_footnote.term_glossary import extract_terms_from_text, get_term, escape_html as term_escape
                    terms_found = extract_terms_from_text(text)
                    # 区分已读/未读
                    new_terms = [t for t in terms_found if t not in seen]
                    # 标记未读名词
                    marked = text
                    for t in terms_found:
                        if t not in seen:
                            # 新词 → 加 data-term 属性（前端加 tooltip）
                            marked = marked.replace(t, f'<span class="term-new" data-term="{term_escape(t)}">{term_escape(t)}</span>')
                    self._json(200, {
                        "found_terms": terms_found,
                        "new_terms": new_terms,
                        "seen_terms": seen,
                        "marked_text": marked,
                    })
                except Exception as e:
                    logger.exception(f"[extract_terms] failed: {e}")
                    self._json(500, {"error": "extract failed", "error_id": str(uuid.uuid4())[:8]})
                return

            if path == "/api/mark_term_seen":
                # 🆕 v1.6.6 标记名词已读
                sid = data.get("session_id")
                term = data.get("term", "")
                if not sid or not term:
                    self._json(400, {"error": "missing session_id or term"})
                    return
                entry = _session_get(sid)
                if entry is None:
                    self._json(404, {"error": "session not found"})
                    return
                game = entry[0]
                if term not in game.state.seen_terms:
                    game.state.seen_terms.append(term)
                self._json(200, {"seen_count": len(game.state.seen_terms), "marked": term})
                return

            if path == "/api/sanitize":
                # 🆕 v1.6.7 架构重构：前端通过此端点复用服务端清洗逻辑
                # 避免 JS 重复实现 10 个正则
                text = data.get("text", "")
                try:
                    from history_footnote.narrative_sanitizer import sanitize
                    cleaned = sanitize(text)
                    self._json(200, {
                        "original_length": len(text),
                        "cleaned": cleaned,
                        "cleaned_length": len(cleaned),
                    })
                except Exception as e:
                    logger.exception(f"[sanitize] failed: {e}")
                    self._json(500, {"error": "sanitize failed", "error_id": str(uuid.uuid4())[:8]})
                return

            if path == "/api/sanitize_patterns":
                # 🆕 v1.6.7 提供给前端同步使用的清洗模式（可选）
                try:
                    from history_footnote.narrative_sanitizer import patterns_as_dict
                    self._json(200, patterns_as_dict())
                except Exception as e:
                    logger.exception(f"[sanitize_patterns] failed: {e}")
                    self._json(500, {"error": "patterns fetch failed", "error_id": str(uuid.uuid4())[:8]})
                return

            if path == "/api/version":
                # 🆕 v1.6.8 版本信息端点
                try:
                    from history_footnote.issue_reporter import get_version_info
                    self._json(200, get_version_info())
                except Exception as e:
                    logger.exception(f"[version] failed: {e}")
                    self._json(500, {"error": "version fetch failed"})
                return

            if path == "/api/feedback":
                # 🆕 v1.6.8 玩家反馈端点
                try:
                    from history_footnote.issue_reporter import (
                        save_feedback, validate_feedback, ISSUE_CATEGORIES,
                    )
                    category = data.get("category", "")
                    description = data.get("description", "")
                    sid = data.get("session_id", "")
                    context = data.get("context", {})

                    # 校验
                    err = validate_feedback(category, description)
                    if err:
                        self._json(400, {"error": err})
                        return

                    result = save_feedback(sid, category, description, context)
                    logger.info(
                        f"[feedback] {result['id']} category={category} "
                        f"session={sid[:16] if sid else 'none'}"
                    )
                    self._json(200, {
                        "id": result["id"],
                        "saved_at": result["saved_at"],
                        "saved_to": result.get("saved_to", ""),
                        "save_error": result.get("save_error", ""),
                    })
                except Exception as e:
                    logger.exception(f"[feedback] failed: {e}")
                    self._json(500, {"error": "feedback submit failed", "error_id": str(uuid.uuid4())[:8]})
                return

            if path == "/api/feedback_categories":
                # 🆕 v1.6.8 反馈分类列表（前端动态渲染）
                try:
                    from history_footnote.issue_reporter import ISSUE_CATEGORIES
                    self._json(200, {"categories": ISSUE_CATEGORIES})
                except Exception as e:
                    logger.exception(f"[feedback_categories] failed: {e}")
                    self._json(500, {"error": "fetch failed"})
                return

            if path == "/api/merge_voice_options":
                # 🆕 v1.6.9 合并 voice_options（结构化优先，缺失时回填 narrative 内嵌选项）
                try:
                    from history_footnote.narrative_sanitizer import merge_voice_options
                    structured = data.get("structured_options", [])
                    narrative = data.get("narrative_text", "")
                    merged = merge_voice_options(structured, narrative)
                    self._json(200, {
                        "options": merged,
                        "source": "structured" if structured else ("inline" if merged else "none"),
                    })
                except Exception as e:
                    logger.exception(f"[merge_voice_options] failed: {e}")
                    self._json(500, {"error": "merge failed"})
                return

            if path == "/api/input":
                # 🆕 v1.6.2 P2 D6：LLM 端点更严限流（20 req/min）
                if not LLM_RATE_LIMITER.allow(client_ip):
                    self._json(429, {"error": "Too Many LLM Requests", "limit": "20 req/min"})
                    return
                sid = data.get("session_id")
                inp = data.get("input", "").strip()
                if not sid or not inp:
                    self._json(400, {"error": "missing session_id or input"})
                    return
                if _session_get(sid) is None:
                    game = _get_or_load_session(sid)
                    if game is None:
                        self._json(404, {"error": "session not found"})
                        return
                entry = _session_get(sid)
                game = entry[0]
                lock = entry[1]
                with lock:
                    if inp.startswith("/quit") or inp.startswith("/exit"):
                        # 退出
                        _session_pop(sid)
                        self._json(200, {"session_id": sid, "quit": True, **_format_state(game)})
                        return
                    if inp.startswith("/state"):
                        self._json(200, {"session_id": sid, **_format_state(game)})
                        return
                    if inp.startswith("/save"):
                        slot = inp.split()[1] if len(inp.split()) > 1 else "slot1"
                        game._handle_meta_command(inp)
                        self._json(200, {"session_id": sid, "saved_to": slot, **_format_state(game)})
                        return
                    # 普通输入：执行一回合
                    pre = game._preprocess_input(inp)
                    # 记录行动点状态变化
                    ap_before = game.state.action_points_current
                    date_before = game.state.current_date
                    # 重定向 stdout 捕获 DM 输出
                    import io
                    from contextlib import redirect_stdout
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        game._run_round(pre)
                    dm_output = buf.getvalue()
                    last = game.state.narrative_history[-1] if game.state.narrative_history else None

                    # 计算行动点消耗情况
                    ap_after = game.state.action_points_current
                    consumed = ap_before - ap_after
                    # 月是否推进：日期变了
                    month_advanced = date_before != game.state.current_date
                    new_date = game.state.current_date if month_advanced else None

                    # 从 DM 输出中提取 is_action/time_cost（通过正则）
                    import re
                    is_action = True  # 默认 true
                    time_cost = consumed if consumed > 0 else 1
                    if "[💬 问询]" in dm_output:
                        is_action = False
                        time_cost = 0
                    else:
                        m = re.search(r"本次行动消耗\s*(\d+)\s*点", dm_output)
                        if m:
                            time_cost = int(m.group(1))

                    self._json(200, {
                        "session_id": sid,
                        **_format_state(game),
                        "last_narrative": last,
                        "last_is_action": is_action,
                        "last_time_cost": time_cost,
                        # 🐛 v1.5.1 P1 Issue 6 修复：优先用规则判定的 intent_type（更可靠）
                        "last_intent_type": _detect_intent_for_response(inp, {}),  # dm_response 暂不可访问，用空 dict fallback
                        "last_voice_options": game.state.last_voice_options,  # 🆕 v1.5+
                        "last_consumed": consumed,
                        "last_month_advanced": month_advanced,
                        "last_new_date": new_date,
                        "dm_output": dm_output,
                    })
                return

            if path == "/api/load":
                sid = data.get("session_id")
                game = _get_or_load_session(sid)
                if game is None:
                    self._json(404, {"error": "session not found"})
                    return
                self._json(200, _format_state(game))
                return

            if path == "/api/input_stream":
                # 🆕 v1.6.2 P1 C2：SSE Streaming 输出
                # 🆕 v1.6.2 P2 D6：LLM 端点更严限流（20 req/min）
                if not LLM_RATE_LIMITER.allow(client_ip):
                    self._json(429, {"error": "Too Many LLM Requests", "limit": "20 req/min"})
                    return
                sid = data.get("session_id")
                inp = data.get("input", "").strip()
                if not sid or not inp:
                    self._json(400, {"error": "missing session_id or input"})
                    return
                if _session_get(sid) is None:
                    game = _get_or_load_session(sid)
                    if game is None:
                        self._json(404, {"error": "session not found"})
                        return
                entry = _session_get(sid)
                game = entry[0]
                lock = entry[1]

                # 用 StreamingEmitter 推送
                from history_footnote.streaming import StreamingEmitter, format_sse
                from history_footnote.post_validator import post_validate, generate_safe_narrative
                from history_footnote.concurrency import LLM_THROTTLE

                state_dict = {
                    "triggered_events": sorted(game.state.triggered_events),
                    "current_date": game.state.current_date,
                    "round_number": game.state.round_number,
                    "selected_identity": game.state.selected_identity,
                }
                era_config = game.era_config

                emitter = StreamingEmitter()

                def _producer():
                    try:
                        emitter.emit_thinking("DM 正在分析场景...")
                        with lock:
                            try:
                                with LLM_THROTTLE:
                                    emitter.emit_thinking("DM 正在生成叙事...")
                                    dm_response = game.dm.run(inp)
                                # 模拟 streaming：每 50 字一个 chunk
                                narrative = dm_response.get("narrative", "")
                                # 把 narrative 按字符切块（避免破坏中文）
                                import re
                                chunks = re.findall(r'.{1,40}', narrative)
                                for chunk in chunks:
                                    emitter.emit_chunk(chunk)
                                    time.sleep(0.04)
                                # 后校验
                                validation = post_validate(dm_response, state_dict, era_config, inp)
                                if not validation.valid:
                                    emitter.emit_thinking(f"后校验发现 {len(validation.errors)} 个问题")
                                # voice_options
                                final_data = {
                                    "session_id": sid,
                                    "voice_options": dm_response.get("voice_options", []),
                                    "intent_type": dm_response.get("intent_type", "action"),
                                    "validation_passed": validation.valid,
                                    "is_action": dm_response.get("is_action", True),
                                    "time_cost": dm_response.get("time_cost", 1),
                                }
                                emitter.emit_done(final_data)
                            except TimeoutError:
                                emitter.emit_error("LLM 调用超时")
                    except Exception as e:
                        import traceback
                        emitter.emit_error(f"{type(e).__name__}: {str(e)[:200]}")

                import threading as _threading
                _threading.Thread(target=_producer, daemon=True).start()

                # 发送 SSE 响应
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                try:
                    for event_type, event_data in emitter.iter_events(timeout=120.0):
                        chunk = format_sse(event_type, event_data)
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        if event_type in ("done", "error"):
                            break
                except (BrokenPipeError, ConnectionResetError):
                    # 客户端断开
                    pass
                return

            self._json(404, {"error": "unknown path"})
        except SystemExit:
            self._json(200, {"session_id": data.get("session_id"), "quit": True})
        except Exception as e:
            # 🆕 v1.6.2 安全修复：不返回 traceback 给前端（泄露文件路径）
            # 落服务端日志 + 返回错误 ID 用于排查
            error_id = str(uuid.uuid4())[:8]
            logger.exception(f"[error_id={error_id}] Unhandled exception in {self.path}: {e}")
            self._json(500, {"error": "internal server error", "error_id": error_id})


def run(host: str = "0.0.0.0", port: int = 8765):
    # 🆕 v1.6.2 P0 优化：启动时预热 era.json + LLM + SaveManager 单例
    print("[v1.6.2] 预热资源缓存...")
    warm_era_configs()
    print(f"[v1.6.2] 预热完成")

    # 🆕 v1.6.2 P2 A6：HTTP keep-alive（启用持久连接）
    setup_keepalive(Handler)
    print(f"[v1.6.2] HTTP keep-alive 已启用")

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[HF Web] 历史注脚体验入口已启动: http://localhost:{port}/")
    print(f"[HF Web] 访问 http://localhost:{port}/ 开始游戏")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[HF Web] 已停止")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    run(args.host, args.port)
