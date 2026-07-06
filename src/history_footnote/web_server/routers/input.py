"""游戏输入相关路由：

POST /api/input                — 玩家输入一行动（标准 JSON 响应）
POST /api/input_stream         — 玩家输入（SSE 流式输出）
POST /api/dilemma              — 从 narrative 提取困境引导
POST /api/render_narrative     — 渲染 narrative
POST /api/merge_voice_options  — 合并结构化与内嵌选项
"""
from __future__ import annotations

import io
from contextlib import redirect_stdout

from history_footnote.web_enhancements import LLM_RATE_LIMITER
from history_footnote.web_server.handler_base import (
    extract_last_consumed,
    logger,
    safe_error_id,
)
from history_footnote.web_server.views.format_state import detect_intent, format_state
from history_footnote.web_server.views.session import _get_or_load_session, session_get, session_pop


# ============================================================
# /api/dilemma — 从 narrative 提取困境（不依赖 session）
# ============================================================

def handle_POST_dilemma(handler, body) -> bool:
    text = body.get("text", "")
    try:
        import re
        dilemma_match = re.search(r"【当前困境】\s*(.+?)(?=【|$)", text, re.DOTALL)
        dilemma = dilemma_match.group(1).strip() if dilemma_match else ""
        question_match = re.search(r"([^。！？\n]*[？\?])", text)
        question = question_match.group(1).strip() if question_match else ""
        context = text.strip()[-80:] if text else ""
        if dilemma and question:
            placeholder = f"【当前困境】\n{dilemma[:200]}\n\n{question}"
        elif question:
            placeholder = question
        elif dilemma:
            placeholder = f"【当前困境】\n{dilemma[:200]}\n\n你想做什么？"
        else:
            placeholder = f"……{context}\n\n你想做什么？"
        handler._json(200, {
            "placeholder": placeholder[:300],
            "dilemma": dilemma[:200],
            "question": question,
            "has_dilemma": bool(dilemma),
            "has_question": bool(question),
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[dilemma] {error_id} failed: {e}")
        handler._json(500, {"error": "dilemma extraction failed", "error_id": error_id})
    return True


# ============================================================
# /api/merge_voice_options — 合并结构化与内嵌选项
# ============================================================

def handle_POST_merge_voice_options(handler, body) -> bool:
    try:
        from history_footnote.narrative_sanitizer import merge_voice_options
        options = merge_voice_options(
            body.get("structured_options"),
            body.get("narrative_text", ""),
        )
        handler._json(200, {"options": options})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[merge_voice_options] {error_id} failed: {e}")
        handler._json(500, {"error": "merge failed", "error_id": error_id})
    return True


# ============================================================
# /api/render_narrative — 渲染 narrative
# ============================================================

def handle_POST_render_narrative(handler, body) -> bool:
    try:
        from history_footnote.narrative_renderer import render_narrative
        text = body.get("text", "")
        rendered = render_narrative(text)
        handler._json(200, {"rendered": rendered})
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[render_narrative] {error_id} failed: {e}")
        handler._json(500, {"error": "render failed", "error_id": error_id})
    return True


# ============================================================
# /api/input — 标准 JSON 响应
# ============================================================

def handle_POST_input(handler, body) -> bool:
    # LLM 端点专用限流
    if handler._rate_limit_or_429(LLM_RATE_LIMITER, "Too Many LLM Requests"):
        return True
    sid = body.get("session_id")
    inp = body.get("input", "").strip()
    if not sid or not inp:
        handler._json(400, {"error": "missing session_id or input"})
        return True
    if session_get(sid) is None:
        game = _get_or_load_session(sid)
        if game is None:
            handler._json(404, {"error": "session not found"})
            return True
    entry = session_get(sid)
    game = entry[0]
    lock = entry[1]
    with lock:
        # 退出元指令
        if inp.startswith("/quit") or inp.startswith("/exit"):
            session_pop(sid)
            handler._json(200, {"session_id": sid, "quit": True, **format_state(game)})
            return True
        # /state 元指令
        if inp.startswith("/state"):
            handler._json(200, {"session_id": sid, **format_state(game)})
            return True
        # /save 元指令
        if inp.startswith("/save"):
            slot = inp.split()[1] if len(inp.split()) > 1 else "slot1"
            game._handle_meta_command(inp)
            handler._json(200, {"session_id": sid, "saved_to": slot, **format_state(game)})
            return True
        # 普通输入：执行一回合
        pre = game._preprocess_input(inp)
        ap_before = game.state.action_points_current
        date_before = game.state.current_date
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                game._run_round(pre)
        except Exception as e:
            error_id = safe_error_id()
            logger.exception(f"[input] {error_id} failed during _run_round: {e}")
            handler._json(500, {"error": "game error", "error_id": error_id})
            return True
        dm_output = buf.getvalue()
        last = game.state.narrative_history[-1] if game.state.narrative_history else None
        # 补 voice_options（context-aware 兜底，复用 inline 提取）
        if not game.state.last_voice_options and last:
            try:
                from history_footnote.narrative_sanitizer import merge_voice_options
                extracted = merge_voice_options(None, last.get("narrative", ""))
                if extracted:
                    game.state.last_voice_options = extracted
                    logger.info(f"[input] 注入 {len(extracted)} voice_options from narrative")
                else:
                    game.state.last_voice_options = _context_aware_voices(last.get("narrative", ""))
                    logger.info(f"[input] 注入 {len(game.state.last_voice_options)} voice_options (context-aware)")
            except Exception as e:
                logger.exception(f"[input] voice_options 注入失败: {e}")
                game.state.last_voice_options = _context_aware_voices(last.get("narrative", ""))
        ap_after = game.state.action_points_current
        consumed = ap_before - ap_after
        month_advanced = date_before != game.state.current_date
        is_action, time_cost = extract_last_consumed(dm_output, fallback=(1 if consumed > 0 else 0))
        handler._json(200, {
            "session_id": sid,
            **format_state(game),
            "last_narrative": last,
            "last_is_action": is_action,
            "last_time_cost": time_cost,
            "last_intent_type": detect_intent(inp, {}),
            "last_voice_options": game.state.last_voice_options,
            "last_consumed": consumed,
            "last_month_advanced": month_advanced,
            "last_new_date": game.state.current_date if month_advanced else None,
            "dm_output": dm_output,
        })
    return True


def _context_aware_voices(narr_text: str) -> list:
    """🆕 v1.7.22 context-aware voice_options 兜底（独立函数，原 web_server.py 内嵌）"""
    context_voices = []
    if "银" in narr_text or "钱" in narr_text or "税" in narr_text or "束脩" in narr_text:
        context_voices.append({"voice_id": "voice_accountant", "voice_name": "算盘声", "intent_text": "再盘算盘算，看能不能借到银子或换条活路"})
    if "官" in narr_text or "里长" in narr_text or "朝廷" in narr_text or "赵里长" in narr_text:
        context_voices.append({"voice_id": "voice_compliance", "voice_name": "本分", "intent_text": "照官府说的办，别给家里招祸"})
    if "织" in narr_text or "布" in narr_text or "丝" in narr_text or "织机" in narr_text:
        context_voices.append({"voice_id": "voice_craft", "voice_name": "手艺人的骄傲", "intent_text": "把活儿做好，名声立住了自然有客来"})
    if "牙行" in narr_text or "王掌柜" in narr_text or "客商" in narr_text:
        context_voices.append({"voice_id": "voice_market", "voice_name": "生意经", "intent_text": "问问价、比比货，总不吃亏"})
    if "王癞子" in narr_text or "赵里长" in narr_text or "李秀才" in narr_text or "沈氏" in narr_text:
        context_voices.append({"voice_id": "voice_social", "voice_name": "邻里情分", "intent_text": "人情世故，也得顾着"})
    base_voices = [
        {"voice_id": "voice_observed", "voice_name": "先看再看", "intent_text": "不急，先把眼前事理清楚"},
        {"voice_id": "voice_action", "voice_name": "动手试", "intent_text": "先动起来，做了再说"},
        {"voice_id": "voice_ask", "voice_name": "问问人", "intent_text": "这事得问个懂行的人"},
    ]
    seen = set()
    merged = []
    for v in context_voices + base_voices:
        key = v["voice_id"]
        if key in seen:
            continue
        seen.add(key)
        merged.append(v)
        if len(merged) >= 3:
            break
    return merged


# ============================================================
# /api/input_stream — SSE 流式
# ============================================================

def handle_POST_input_stream(handler, body) -> bool:
    if handler._rate_limit_or_429(LLM_RATE_LIMITER, "Too Many LLM Requests"):
        return True
    sid = body.get("session_id")
    inp = body.get("input", "").strip()
    if not sid or not inp:
        handler._json(400, {"error": "missing session_id or input"})
        return True
    if session_get(sid) is None:
        game = _get_or_load_session(sid)
        if game is None:
            handler._json(404, {"error": "session not found"})
            return True
    entry = session_get(sid)
    game = entry[0]
    lock = entry[1]
    from history_footnote.streaming import StreamingEmitter, format_sse
    from history_footnote.post_validator import post_validate, generate_safe_narrative

    emitter = StreamingEmitter()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()

    def push(event: str, data):
        try:
            handler.wfile.write(format_sse(event, data))
            handler.wfile.flush()
        except Exception:
            pass

    push("thinking", {"message": "DM 思考中..."})
    with lock:
        pre = game._preprocess_input(inp)
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                game._run_round(pre)
        except Exception as e:
            push("error", {"message": str(e), "error_id": safe_error_id()})
            return True
        dm_output = buf.getvalue()
        last = game.state.narrative_history[-1] if game.state.narrative_history else None
        last_narr = (last.get("narrative", "") if last else "")
        # 推送 chunk（按句切分）
        import re as _re
        sentences = _re.split(r"(?<=[。！？\?\!])", last_narr)
        for s in sentences:
            s = s.strip()
            if s:
                push("chunk", {"text": s})
        push("done", {
            "session_id": sid,
            "last_narrative": last,
            "voice_options": game.state.last_voice_options,
            "dm_output": dm_output,
            **format_state(game),
        })
    return True
