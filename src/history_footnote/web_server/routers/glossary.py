"""名词字典 + 文本清洗路由：

POST /api/glossary             — 查询名词
POST /api/extract_terms        — 从文本提取名词
POST /api/mark_term_seen       — 标记名词已读
POST /api/sanitize             — 清洗 narrative
GET  /api/sanitize_patterns    — 取 sanitizer 正则模式
"""
from __future__ import annotations

from history_footnote.web_server.handler_base import logger, safe_error_id


def handle_POST_glossary(handler, body) -> bool:
    query = body.get("query", "")
    term_key = body.get("term", "")
    try:
        if term_key:
            from history_footnote.term_glossary import get_term, get_term_html
            term = get_term(term_key)
            if not term:
                handler._json(404, {"error": "term not found"})
                return True
            handler._json(200, {
                "key": term_key,
                "category": term["category"],
                "definition": term["definition"],
                "example": term.get("example", ""),
                "related": term.get("related", []),
                "html": get_term_html(term_key),
            })
        else:
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
            handler._json(200, {
                "query": query,
                "count": len(terms_data),
                "terms": terms_data,
                "total_in_dict": len(TERM_GLOSSARY),
            })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[glossary] {error_id} failed: {e}")
        handler._json(500, {"error": "glossary query failed", "error_id": error_id})
    return True


def handle_POST_extract_terms(handler, body) -> bool:
    text = body.get("text", "")
    if not text:
        handler._json(400, {"error": "missing text"})
        return True
    sid = body.get("session_id")
    seen = []
    if sid:
        from history_footnote.web_server.views.session import session_get
        entry = session_get(sid)
        if entry:
            seen = entry[0].state.seen_terms or []
    try:
        from history_footnote.term_glossary import (
            extract_terms_from_text,
            escape_html as term_escape,
        )
        terms_found = extract_terms_from_text(text)
        new_terms = [t for t in terms_found if t not in seen]
        marked = text
        for t in terms_found:
            if t not in seen:
                marked = marked.replace(t, f'<span class="term-new" data-term="{term_escape(t)}">{term_escape(t)}</span>')
        handler._json(200, {
            "found_terms": terms_found,
            "new_terms": new_terms,
            "seen_terms": seen,
            "marked_text": marked,
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[extract_terms] {error_id} failed: {e}")
        handler._json(500, {"error": "extract failed", "error_id": error_id})
    return True


def handle_POST_mark_term_seen(handler, body) -> bool:
    sid = body.get("session_id")
    term = body.get("term", "")
    if not sid or not term:
        handler._json(400, {"error": "missing session_id or term"})
        return True
    from history_footnote.web_server.views.session import session_get, _get_or_load_session
    entry = session_get(sid)
    if entry is None:
        game = _get_or_load_session(sid)
        if game is None:
            handler._json(404, {"error": "session not found"})
            return True
        entry = session_get(sid)
    game = entry[0]
    if term not in game.state.seen_terms:
        game.state.seen_terms.append(term)
    handler._json(200, {"seen_count": len(game.state.seen_terms), "marked": term})
    return True


def handle_POST_sanitize(handler, body) -> bool:
    text = body.get("text", "")
    try:
        from history_footnote.narrative_sanitizer import sanitize
        cleaned = sanitize(text)
        handler._json(200, {
            "original_length": len(text),
            "cleaned": cleaned,
            "cleaned_length": len(cleaned),
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[sanitize] {error_id} failed: {e}")
        handler._json(500, {"error": "sanitize failed", "error_id": error_id})
    return True


def handle_GET_sanitize_patterns(handler) -> bool:
    try:
        from history_footnote.narrative_sanitizer import patterns_as_dict
        handler._json(200, patterns_as_dict())
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[sanitize_patterns] {error_id} failed: {e}")
        handler._json(500, {"error": "patterns fetch failed", "error_id": error_id})
    return True
