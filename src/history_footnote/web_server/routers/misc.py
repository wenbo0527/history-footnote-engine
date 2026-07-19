"""杂项路由（多领域路由，未单独立项）：

POST /api/lore                  — 游戏内查 lore
POST /api/generate_character    — LLM 生成人设
POST /api/generate_world_dwell  — LLM 生成世界画卷
POST /api/version               — 版本信息
POST /api/feedback              — 反馈提交
POST /api/feedback_categories   — 反馈分类
"""
from __future__ import annotations

from history_footnote.web_server.handler_base import logger, safe_error_id
from history_footnote.web_server.views.session import session_get, _get_or_load_session


def handle_POST_lore(handler, body) -> bool:
    sid = body.get("session_id")
    topic = body.get("topic", "")
    if not sid or not topic:
        handler._json(400, {"error": "missing session_id or topic"})
        return True
    if session_get(sid) is None:
        game = _get_or_load_session(sid)
        if game is None:
            handler._json(404, {"error": "session not found"})
            return True
    entry = session_get(sid)
    game = entry[0]
    try:
        from history_footnote.knowledge_base import KnowledgeBase
        kb = game.knowledge_base
        results = kb.search(topic, top_k=5) if hasattr(kb, "search") else []
        handler._json(200, {"topic": topic, "results": results})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[lore] {error_id} failed: {e}")
        handler._json(500, {"error": "lore query failed", "error_id": error_id})
    return True


def handle_POST_generate_character(handler, body) -> bool:
    era_id = body.get("era_id", "wanli1587")
    gender = body.get("gender", "male")
    location = body.get("location", "")
    location_desc = body.get("location_description", "")
    identity_desc = body.get("identity_description", "")
    life_exp = body.get("life_expectation", "")
    # 🆕 v1.9.4 玩家隔离（account_id 从 query 或 body 取）
    account_id = ""
    try:
        from urllib.parse import parse_qs
        qs = parse_qs(handler.path.split("?", 1)[1]) if "?" in handler.path else {}
        account_id = qs.get("account_id", [None])[0] or body.get("account_id", "") or ""
    except Exception:
        account_id = body.get("account_id", "") or ""
    # 🆕 v1.9.2 缓存查询（精确 → 模糊 → 兜底）
    try:
        from history_footnote.llm_cache import get as cache_get, put as cache_put
        cached = cache_get(era_id, gender, location, identity_desc, life_exp, account_id=account_id)
        if cached:
            hit = cached.get("cache_hit", "exact")
            logger.info(f"[generate_character] 缓存命中 ({hit}): {cached.get('character', {}).get('name', '?')}")
            handler._json(200, {
                "character": cached["character"],
                "raw": cached.get("raw", ""),
                "cache_hit": hit,
            })
            return True
    except Exception as e:
        logger.warning(f"[generate_character] 缓存读失败：{e}")
    try:
        from history_footnote.resource_cache import load_era_config
        config = load_era_config(era_id)
        from history_footnote.character_generator import build_character_prompt, parse_character_response
        prompt = build_character_prompt(config, gender, identity_desc, life_exp, location=location, location_desc=location_desc)
        from history_footnote.llm_wrapper import get_wrapped_llm
        llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
        from langchain_core.messages import SystemMessage, HumanMessage
        # 🆕 v1.9.3 Prompt Caching：使用固定的 system prompt 前缀
        # （所有调用都用同一字符串 → Anthropic/Claude/OpenAI 字节级 KV cache 命中）
        STATIC_SYSTEM_PROMPT = "你是「历史注脚体验引擎」的人设生成助手。严格按 JSON 格式输出，包含 name/age/family/background/occupation/location 字段。文字生动，时代感强（明万历年间）。"
        resp = llm.invoke([
            SystemMessage(content=STATIC_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])
        parsed = parse_character_response(resp.content)
        # 🆕 v1.9.2 写缓存（v1.9.4 双层）
        try:
            from history_footnote.llm_cache import put as cache_put
            cache_put(era_id, gender, location, identity_desc, life_exp, parsed, resp.content, account_id=account_id)
        except Exception as e:
            logger.warning(f"[generate_character] 缓存写失败：{e}")
        handler._json(200, {"character": parsed, "raw": resp.content, "cache_hit": "miss"})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[generate_character] {error_id} failed: {e}")
        # 🆕 v1.9.2 降级：模糊匹配 → 兜底（最新）
        try:
            from history_footnote.llm_cache import find_similar, find_latest
            fallback = find_similar(era_id, gender, location, identity_desc, life_exp, account_id=account_id) or find_latest(era_id, account_id=account_id)
            if fallback:
                hit = fallback.get("cache_hit", "fallback")
                logger.info(f"[generate_character] LLM 失败，降级用缓存 {hit}: {fallback.get('character', {}).get('name', '?')}")
                handler._json(200, {
                    "character": fallback["character"],
                    "raw": fallback.get("raw", ""),
                    "cache_hit": hit,
                    "degraded": True,
                    "warning": f"LLM 失败，已用缓存 ({hit})",
                })
                return True
        except Exception as e2:
            logger.warning(f"[generate_character] 降级失败：{e2}")
        handler._json(500, {"error": "character generation failed", "error_id": error_id})
    return True


def handle_POST_generate_world_dwell(handler, body) -> bool:
    era_id = body.get("era_id", "wanli1587")
    try:
        from history_footnote.resource_cache import load_era_config
        config = load_era_config(era_id)
        from history_footnote.character_generator import build_world_dwell_prompt, parse_world_dwell
        prompt = build_world_dwell_prompt(config)
        from history_footnote.llm_wrapper import get_wrapped_llm
        llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
        from langchain_core.messages import SystemMessage, HumanMessage
        resp = llm.invoke([
            SystemMessage(content="你是世界画卷绘制师。严格按 JSON 格式输出。"),
            HumanMessage(content=prompt),
        ])
        parsed = parse_world_dwell(resp.content)
        handler._json(200, {"world_dwell": parsed, "raw": resp.content})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[generate_world_dwell] {error_id} failed: {e}")
        handler._json(500, {"error": "world dwell generation failed", "error_id": error_id})
    return True


def handle_GET_version(handler) -> bool:
    try:
        from history_footnote.issue_reporter import get_version_info
        info = get_version_info()
        # 🆕 v2.10.10：附上前端路径诊断（部署排错用）
        try:
            from history_footnote.web_server.static_assets import frontend_paths_info
            info["frontend"] = frontend_paths_info()
        except Exception as e:
            info["frontend_error"] = str(e)
        handler._json(200, info)
    except Exception as e:
        handler._json(500, {"error": "version fetch failed", "detail": str(e)})
    return True


def handle_POST_version(handler, body) -> bool:
    """🆕 v1.8.0 POST /api/version（与 GET 同效）
    main.js loadVersionBadge 用 POST { } 调用
    """
    return handle_GET_version(handler)


def handle_POST_feedback(handler, body) -> bool:
    try:
        from history_footnote.issue_reporter import (
            save_feedback, validate_feedback, ISSUE_CATEGORIES,
        )
        category = body.get("category", "")
        description = body.get("description", "")
        sid = body.get("session_id", "")
        context = body.get("context", {})
        err = validate_feedback(category, description)
        if err:
            handler._json(400, {"error": err})
            return True
        result = save_feedback(sid, category, description, context)
        logger.info(
            f"[feedback] {result['id']} category={category} "
            f"session={sid[:16] if sid else 'none'}"
        )
        handler._json(200, {
            "id": result["id"],
            "saved_at": result["saved_at"],
            "saved_to": result.get("saved_to", ""),
            "save_error": result.get("save_error", ""),
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[feedback] {error_id} failed: {e}")
        handler._json(500, {"error": "feedback submit failed", "error_id": error_id})
    return True


def handle_GET_feedback_categories(handler) -> bool:
    try:
        from history_footnote.issue_reporter import ISSUE_CATEGORIES
        handler._json(200, {"categories": ISSUE_CATEGORIES})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[feedback_categories] {error_id} failed: {e}")
        handler._json(500, {"error": "categories fetch failed", "error_id": error_id})
    return True
