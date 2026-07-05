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


def _render_wiki_summary_safe(wiki) -> str:
    """🆕 v1.7.1 安全地渲染 wiki summary（用于 HTTP API）"""
    try:
        from history_footnote.character_wiki import render_wiki_summary
        return render_wiki_summary(wiki)
    except Exception:
        logger.exception("[v1.7.2] wiki summary 渲染失败")
        return ""
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
        logger.exception("[v1.7.2] intent 类型检测失败")
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
    # 🆕 v1.7.16: 改用 LLMWrapper（支持超时 + fallback + token 日志）
    from history_footnote.llm_wrapper import get_wrapped_llm
    llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
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
    # 🆕 v1.7.16: 改用 LLMWrapper
    from history_footnote.llm_wrapper import get_wrapped_llm
    llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
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


# 🆕 v1.7.3 HTML/CSS/JS 拆分到独立文件
# - HTML 框架在 web/templates/index.html
# - CSS 在 web/static/css/main.css
# - JS 在 web/static/js/main.js
# 这里只 load 文件内容（启动时缓存）
from history_footnote.web import TEMPLATES_DIR as _TPL_DIR, STATIC_DIR as _STATIC_DIR
_INDEX_HTML_PATH = _TPL_DIR / "index.html"
_INDEX_HTML = _INDEX_HTML_PATH.read_text(encoding="utf-8") if _INDEX_HTML_PATH.exists() else "<!-- template missing -->"
# 兼容老名字（其他代码可能引用 INDEX_HTML）
INDEX_HTML = _INDEX_HTML

# 🆕 v1.6.2 安全：统一 logger（错误响应落日志，不返回 traceback 给前端）
logger = logging.getLogger("history_footnote.web_server")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
# 🆕 v1.7.17 修复：禁用 propagate（防止与 root logger 重复输出）
# 背景：__init__.py 配置 root logger + handlers，web_server logger 通过 propagate 也会输出
# 现象：每条 log 出现 2 次（root + web_server 自身）
logger.propagate = False


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

    # 🆕 v1.7.3 静态资源（CSS/JS）服务
    MIME_TYPES = {
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
    }

    def _serve_static(self, path: str):
        """服务 /static/ 下的静态资源（防止路径穿越攻击）"""
        from history_footnote.web import STATIC_DIR
        # 去掉 /static/ 前缀
        rel = path[len("/static/"):]
        # 安全：禁止 .. 路径穿越
        if ".." in rel or rel.startswith("/"):
            self._json(400, {"error": "invalid path"})
            return
        file_path = STATIC_DIR / rel
        if not file_path.exists() or not file_path.is_file():
            self._json(404, {"error": "not found", "path": rel})
            return
        # MIME type
        ext = file_path.suffix
        mime = self.MIME_TYPES.get(ext, "application/octet-stream")
        # 读 + gzip
        try:
            body = file_path.read_bytes()
        except OSError as e:
            logger.exception("[v1.7.3] 读静态文件失败: %s", file_path)
            self._json(500, {"error": "read failed"})
            return
        body = self._gzip_if_accepted(body)
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        if body[:2] == b'\x1f\x8b':
            self.send_header("Content-Encoding", "gzip")
        # 静态资源可以长期缓存
        self.send_header("Cache-Control", "public, max-age=3600")  # 1 小时
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
        # 🆕 v1.7.3 静态资源服务（CSS/JS 拆分到独立文件）
        if path.startswith("/static/"):
            self._serve_static(path)
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
        if path == "/api/state":
            # 🆕 v1.7.15: 获取当前 session 完整 state（流式调用后取最终态）
            qs = parse_qs(urlparse(self.path).query)
            sid = qs.get("session_id", [None])[0]
            if not sid:
                self._json(400, {"error": "missing session_id"})
                return
            try:
                game = _get_or_load_session(sid)
                if game is None:
                    self._json(404, {"error": "session not found"})
                    return
                # _format_state 已包含所有字段（current_date, round, action_points, variables, last_narrative 等）
                self._json(200, _format_state(game))
            except Exception as e:
                logger.exception(f"[/api/state] 失败: {e}")
                self._json(500, {"error": str(e)})
            return
        if path == "/api/llm/stats":
            # 🆕 v1.7.16: LLM 调用的 token 统计 + fallback 历史
            try:
                from history_footnote.llm_wrapper import get_usage_logger
                logger_instance = get_usage_logger()
                qs = parse_qs(urlparse(self.path).query)
                recent_limit = int(qs.get("recent_limit", ["20"])[0])
                stats = logger_instance.get_stats()
                stats["recent"] = logger_instance.get_recent(limit=recent_limit)
                self._json(200, stats)
            except Exception as e:
                logger.exception(f"[/api/llm/stats] 失败: {e}")
                self._json(500, {"error": str(e)})
            return
        if path == "/api/llm/reset_stats":
            # 🆕 v1.7.16: 重置统计（开发/调试用）
            from history_footnote.llm_wrapper import get_usage_logger
            get_usage_logger().reset()
            self._json(200, {"ok": True, "message": "stats reset"})
            return
        if path == "/api/archives":
            qs = parse_qs(urlparse(self.path).query)
            era_id = qs.get("era_id", [None])[0]
            try:
                save_manager = get_save_manager_cached()  # 🆕 v1.6.2 P0 A3: SaveManager 单例
                sessions = save_manager.list_sessions(era_id=era_id)
                out = []
                for s in sessions[:10]:
                    # 🆕 v1.7.13: SaveSession 没有 selected_identity/player_gender 字段
                    # 用 getattr 兜底（防止 AttributeError → ERR_EMPTY_RESPONSE）
                    out.append({
                        "session_id": s.session_id,
                        "era_id": s.era_id,
                        "current_round": getattr(s, "current_round", 0),
                        "current_date": getattr(s, "current_date", ""),
                        "summary": getattr(s, "summary", ""),
                        "created_at": getattr(s, "created_at", ""),
                        "last_saved_at": getattr(s, "last_saved_at", ""),
                        "selected_identity": getattr(s, "selected_identity", ""),
                        "player_gender": getattr(s, "player_gender", ""),
                    })
                self._json(200, {"archives": out})
            except Exception as e:
                # 🆕 v1.7.13 修复：捕获异常并返回 500（不再让请求挂死）
                logger.exception("[/api/archives] 失败: %s", e)
                self._json(500, {"error": f"列出存档失败: {e}", "archives": []})
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
                    # 🆕 v1.7.16: 改用 LLMWrapper（超时 + fallback + token 日志）
                    from history_footnote.llm_wrapper import get_wrapped_llm
                    llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
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
                    # 🆕 v1.7.16: 改用 LLMWrapper
                    from history_footnote.llm_wrapper import get_wrapped_llm
                    llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
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

            if path == "/api/render_narrative":
                # 🆕 v1.7.0 结构化叙事渲染（前端 async 用）
                try:
                    from history_footnote.narrative_renderer import (
                        ensure_blocks, render_blocks_to_html,
                    )
                    structured = data.get("structured_blocks", [])
                    narrative = data.get("narrative_text", "")
                    blocks = ensure_blocks(structured, narrative)
                    html = render_blocks_to_html(blocks)
                    self._json(200, {
                        "blocks": blocks,
                        "html": html,
                        "block_count": len(blocks),
                        "block_types": list(set(b.get("type", "scene") for b in blocks)),
                    })
                except Exception as e:
                    logger.exception(f"[render_narrative] failed: {e}")
                    self._json(500, {"error": "render failed"})
                return

            if path == "/api/character_wiki":
                # 🆕 v1.7.1 Per-Save Character Wiki 查询
                sid = data.get("session_id")
                if not sid:
                    self._json(400, {"error": "missing session_id"})
                    return
                entry = _session_get(sid)
                if entry is None:
                    self._json(404, {"error": "session not found"})
                    return
                game = entry[0]
                try:
                    from history_footnote.character_wiki import CharacterWiki
                    wiki = CharacterWiki.from_dict(game.state.character_wiki or {})
                    self._json(200, {
                        "wiki": wiki.to_dict(),
                        "summary": _render_wiki_summary_safe(wiki),
                    })
                except Exception as e:
                    logger.exception(f"[character_wiki] failed: {e}")
                    self._json(500, {"error": "wiki query failed"})
                return

            if path == "/api/character_wiki_update":
                # 🆕 v1.7.1 玩家/LLM 主动更新 wiki（如发现错误）
                sid = data.get("session_id")
                char_data = data.get("character", {})
                if not sid:
                    self._json(400, {"error": "missing session_id"})
                    return
                entry = _session_get(sid)
                if entry is None:
                    self._json(404, {"error": "session not found"})
                    return
                game = entry[0]
                try:
                    from history_footnote.character_wiki import CharacterWiki
                    wiki = CharacterWiki.from_dict(game.state.character_wiki or {})
                    name = char_data.get("id", "")
                    if not name:
                        self._json(400, {"error": "missing character id"})
                        return
                    char = wiki.add_or_update_character(
                        name=name,
                        round=char_data.get("round", game.state.round_number),
                        summary=char_data.get("summary", ""),
                        relationship=char_data.get("relationship"),
                        traits=char_data.get("traits"),
                        description=char_data.get("description"),
                    )
                    game.state.character_wiki = wiki.to_dict()
                    self._json(200, {"updated": char.to_dict()})
                except Exception as e:
                    logger.exception(f"[character_wiki_update] failed: {e}")
                    self._json(500, {"error": "update failed"})
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
                    # 🆕 v1.7.9 fix: last_narrative 是 dict（保持向后兼容）
                    #   - 前端 appendNarrative(n) 期望 n.round / n.summary / n.narrative

                    # 🆕 v1.7.9 测试用：mock LLM 不返回 voice_options，注入默认
                    if not game.state.last_voice_options and last:
                        # 从 narrative 提取"一、二、三"格式的内嵌选项
                        from history_footnote.narrative_sanitizer import merge_voice_options
                        extracted = merge_voice_options(None, last.get("narrative", ""))
                        if extracted:
                            game.state.last_voice_options = extracted
                            logger.info(f"[v1.7.9] 注入 {len(extracted)} voice_options from narrative")
                        else:
                            # 🆕 v1.7.9 改进：基于 context 注入**独特**的 3 个内在声音
                            # 根据 narrative 提取关键词，匹配不同的"内在声音"
                            narr_text = last.get("narrative", "")
                            # 默认 3 个 + 1 个兜底（让玩家总可继续）
                            base_voices = [
                                {"voice_id": "voice_default_1", "voice_name": "谨慎行事", "intent_text": "先观察，再决定"},
                                {"voice_id": "voice_default_2", "voice_name": "按本心", "intent_text": "照自己想做的去做"},
                                {"voice_id": "voice_default_3", "voice_name": "问问旁人", "intent_text": "找个信得过的人商量"},
                            ]
                            # 根据 narrative 关键词，添加额外的"时代个性"选项
                            extra = []
                            if "银" in narr_text or "钱" in narr_text or "税" in narr_text:
                                extra.append({"voice_id": "voice_accountant", "voice_name": "算盘声", "intent_text": "再盘算盘算，看有没有别的进项"})
                            if "官" in narr_text or "里长" in narr_text or "朝廷" in narr_text:
                                extra.append({"voice_id": "voice_compliance", "voice_name": "本分", "intent_text": "照官府说的办，别惹麻烦"})
                            if "织" in narr_text or "布" in narr_text or "丝" in narr_text:
                                extra.append({"voice_id": "voice_craft", "voice_name": "手艺人的骄傲", "intent_text": "把活儿做好，名声自然有"})
                            if "王" in narr_text or "张" in narr_text or "李" in narr_text:
                                extra.append({"voice_id": "voice_social", "voice_name": "邻里情分", "intent_text": "人情世故，也得顾着"})
                            # 截取前 3 个（保证 UI 紧凑）
                            voices = base_voices + extra
                            game.state.last_voice_options = voices[:3] if len(voices) >= 3 else voices + base_voices[:3-len(voices)]
                            logger.info(f"[v1.7.9] 注入 {len(game.state.last_voice_options)} voice_options (mock fallback with context)")

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
                        "last_narrative": last,  # 🆕 v1.7.9: dict with round/summary/narrative
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

            if path == "/api/archive/delete":
                # 🆕 v1.7.14：删除单个存档
                sid = data.get("session_id", "").strip()
                if not sid:
                    self._json(400, {"error": "missing session_id"})
                    return
                try:
                    save_manager = get_save_manager_cached()
                    # 安全检查：session_id 不能包含路径分隔符
                    if "/" in sid or "\\" in sid or ".." in sid:
                        self._json(400, {"error": "invalid session_id"})
                        return
                    if not save_manager.find_session(sid):
                        self._json(404, {"error": "session not found", "session_id": sid})
                        return
                    ok = save_manager.delete_session(sid)
                    if ok:
                        # 同时清理 _session_get 缓存（如果加载过）
                        _session_pop(sid)
                        logger.info(f"[v1.7.14] Deleted archive: {sid}")
                        self._json(200, {"ok": True, "session_id": sid, "deleted": True})
                    else:
                        self._json(500, {"error": "delete failed", "session_id": sid})
                except Exception as e:
                    logger.exception(f"[/api/archive/delete] 失败: {e}")
                    self._json(500, {"error": f"delete failed: {e}"})
                return

            if path == "/api/archives/clear":
                # 🆕 v1.7.14：清空某 era 的所有存档
                era_id = data.get("era_id", "").strip()
                confirm = data.get("confirm", False)  # 二次确认
                if not era_id:
                    self._json(400, {"error": "missing era_id"})
                    return
                if not confirm:
                    self._json(400, {"error": "需要 confirm=true 二次确认"})
                    return
                try:
                    save_manager = get_save_manager_cached()
                    sessions = save_manager.list_sessions(era_id=era_id)
                    if not sessions:
                        self._json(200, {"ok": True, "deleted_count": 0, "deleted_ids": []})
                        return
                    deleted_ids = []
                    failed = []
                    for s in sessions:
                        # 安全检查
                        sid = s.session_id
                        if "/" in sid or "\\" in sid or ".." in sid:
                            failed.append(sid)
                            continue
                        if save_manager.delete_session(sid):
                            deleted_ids.append(sid)
                            _session_pop(sid)
                        else:
                            failed.append(sid)
                    logger.info(f"[v1.7.14] Cleared {len(deleted_ids)} archives for era {era_id}")
                    self._json(200, {
                        "ok": True,
                        "deleted_count": len(deleted_ids),
                        "deleted_ids": deleted_ids,
                        "failed": failed,
                    })
                except Exception as e:
                    logger.exception(f"[/api/archives/clear] 失败: {e}")
                    self._json(500, {"error": f"clear failed: {e}"})
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
                        # 🆕 v1.7.15 阶段化进度事件（前端弹窗用）
                        emitter.emit_phase("analyzing", "DM 正在分析场景...", 10)
                        emitter.emit_thinking("DM 正在分析场景...")
                        with lock:
                            try:
                                # 🆕 v1.7.15 阶段 1: 等待 LLM 队列
                                emitter.emit_phase("queue", "等待 LLM 队列...", 20)
                                with LLM_THROTTLE:
                                    # 🆕 v1.7.15 阶段 2: LLM 正在生成
                                    emitter.emit_phase("generating", "DM 正在生成叙事...", 30)
                                    dm_response = game.dm.run(inp)
                                # 🆕 v1.7.15 阶段 3: 模拟 streaming（按字块输出）
                                emitter.emit_phase("streaming", "正在渲染叙事...", 60)
                                narrative = dm_response.get("narrative", "")
                                # 把 narrative 按字符切块（避免破坏中文）
                                import re
                                chunks = re.findall(r'.{1,40}', narrative)
                                for chunk in chunks:
                                    emitter.emit_chunk(chunk)
                                    time.sleep(0.04)
                                # 🆕 v1.7.15 阶段 4: 后校验
                                emitter.emit_phase("validating", "校验叙事质量...", 85)
                                validation = post_validate(dm_response, state_dict, era_config, inp)
                                if not validation.valid:
                                    emitter.emit_thinking(f"后校验发现 {len(validation.errors)} 个问题")
                                # 🆕 v1.7.15 阶段 5: 整理
                                emitter.emit_phase("finalizing", "整理行动选项...", 95)
                                # 🆕 v1.7.18: done 事件包含全量数据
                                # 背景：前端不再发 /api/state（减少并发 fetch）
                                # 全量数据来自 _format_state
                                _full_state = _format_state(game)
                                # _format_state 没有 last_narrative 字段，但有 recent_narratives[]
                                _recent_narrs = _full_state.get("recent_narratives", [])
                                _last_narrative_obj = _recent_narrs[-1] if _recent_narrs else {
                                    "round": _full_state.get("round_number", 0),
                                    "summary": "",
                                    "narrative": "",
                                }
                                final_data = {
                                    "session_id": sid,
                                    "voice_options": dm_response.get("voice_options", []),
                                    "intent_type": dm_response.get("intent_type", "action"),
                                    "validation_passed": validation.valid,
                                    "is_action": dm_response.get("is_action", True),
                                    "time_cost": dm_response.get("time_cost", 1),
                                    # 🆕 v1.7.18 全量数据
                                    "last_narrative": _last_narrative_obj,
                                    "last_is_action": dm_response.get("is_action", True),
                                    "last_time_cost": dm_response.get("time_cost", 1),
                                    "last_intent_type": dm_response.get("intent_type", "action"),
                                    "last_month_advanced": _full_state.get("last_month_advanced", False),
                                    "last_new_date": _full_state.get("last_new_date"),
                                    "current_date": _full_state.get("current_date", ""),
                                    "round_number": _full_state.get("round_number", 0),
                                    "action_points_current": _full_state.get("action_points_current", 0),
                                    "action_points_max": _full_state.get("action_points_max", 3),
                                    "variables": _full_state.get("variables", {}),
                                }
                                logger.info(f"emit_done for sid={sid}, voice_count={len(final_data['voice_options'])}, narr_len={len(_last_narrative_obj.get('narrative', ''))}")
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
                # 🆕 v1.7.18: SSE 必须 close，不能 keep-alive
                # 原因：keep-alive 让客户端 fetch 一直等 EOF，触发 ERR_ABORTED
                # SSE 协议设计：服务端完成所有事件后直接 close TCP
                self.send_header("Connection", "close")
                self.send_header("X-Accel-Buffering", "no")  # 禁用 nginx 缓冲
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
