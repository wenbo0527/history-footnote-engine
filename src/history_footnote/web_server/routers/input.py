"""游戏输入相关路由：

POST /api/input                — 玩家输入一行动（标准 JSON 响应）
POST /api/input_stream         — 玩家输入（SSE 流式输出）
POST /api/dilemma              — 从 narrative 提取困境引导
POST /api/render_narrative     — 渲染 narrative
POST /api/merge_voice_options  — 合并结构化与内嵌选项
"""
from __future__ import annotations

import io
import json
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

    # 🆕 v1.7.28：输入验证（非游戏内容检测）
    from history_footnote.input_validator import validate_input, is_low_quality_input
    if is_low_quality_input(inp):
        result = validate_input(inp, knowledge_matched=0, knowledge_matched_required=0)
        handler._json(400, {
            "error": result.reason,
            "message": result.message,
            "suggestion": result.suggestion,
            "retryable": True,
        })
        return True

    result = validate_input(inp, knowledge_matched=0, knowledge_matched_required=0)
    if not result.is_valid:
        handler._json(400, {
            "error": result.reason,
            "message": result.message,
            "suggestion": result.suggestion,
            "retryable": True,
        })
        return True

    # 🆕 软提示（low_relevance）→ 不阻断，只在响应里加 warning
    soft_warning = None
    if result.reason == "low_relevance":
        soft_warning = {
            "type": "low_relevance",
            "message": result.message,
            "suggestion": result.suggestion,
        }
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
                    # 🆕 v2.3: 传 game 给 LLM 驱动（不再用关键词匹配）
                    game.state.last_voice_options = _context_aware_voices(last.get("narrative", ""), game=game)
                    logger.info(f"[input] 注入 {len(game.state.last_voice_options)} voice_options (context-aware)")
            except Exception as e:
                logger.exception(f"[input] voice_options 注入失败: {e}")
                game.state.last_voice_options = _context_aware_voices(last.get("narrative", ""), game=game)
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
            "soft_warning": soft_warning,    # 🆕 v1.7.28
        })
    return True


def _context_aware_voices(narr_text: str, game=None) -> list:
    """🆕 v2.3 升级：LLM 驱动的 context-aware voice_options

    历史问题：v1.7.22 关键词匹配兜底（"算盘声/本分/手艺人的骄傲"）反复出现，
    与玩家实际面对的具体问题脱节。

    v2.3 策略：
      1. **优先 LLM**：复用 voice_suggest 的 prompt 和逻辑，基于 narrative 末段生成
         真正"可执行的动作"（如"向王牙人借三两/月息一分/押房契"）
      2. **降级关键词**：LLM 调用失败/超时时退回 v1.7.22 静态映射
      3. **完全无声时**：3 个硬编码应急（"先观察一阵/找邻居问问/想清楚再做"）

    Args:
        narr_text: 最近的叙事（≤ 600 字）
        game: 可选，Game 实例。如果提供则 LLM 生成更精准（带身份/回合/状态）

    Returns:
        list[dict]: 2-5 个 voice_options
    """
    if not narr_text or len(narr_text.strip()) < 10:
        # 叙事太短，直接给通用兜底（不浪费 LLM token）
        return _fallback_keyword_voices(narr_text or "")

    # 尝试 LLM 生成（仅在有 game 实例时，避免 /api/dilemma 等无 session 场景）
    if game is not None:
        try:
            llm_voices = _llm_generate_voices(narr_text, game)
            if llm_voices and len(llm_voices) >= 2:
                return llm_voices
        except Exception as e:
            logger.warning(f"[v2.3] LLM voice gen 失败，降级关键词: {e}")

    # 降级：关键词匹配
    return _fallback_keyword_voices(narr_text)


def _llm_generate_voices(narr_text: str, game) -> list:
    """内部：直接调 LLM 生成 context-aware voice_options

    复用 voice_suggest._SUGGEST_PROMPT 的核心思路
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from history_footnote.narrative_sanitizer import extract_json_from_text
    from history_footnote.resource_cache import load_era_config
    from history_footnote.llm_wrapper import get_wrapped_llm

    last_narr = (game.state.narrative_history or [])[-1] if game.state.narrative_history else None
    narrative_text = (last_narr or {}).get("narrative", "")[:600] or narr_text[:600]
    round_number = game.state.round_number or 0
    identity = game.state.selected_identity or "未选身份"

    config = load_era_config(game.era_id)
    llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)

    prompt = f"""你是 DM 引导者。玩家是 {identity}，当前第 {round_number} 回合。

玩家面对的局面（最近叙事末尾）：
\"\"\"
{narrative_text}
\"\"\"

**请基于玩家此刻面对的具体问题，给出 3~4 个**可执行**的应对方案。**

每条一行 JSON：
{{
  "voice_id": "<id>",
  "voice_name": "<3~10 字短句，是玩家可执行的动作>",
  "intent_text": "<一句话解释为何这样做>"
}}

要求：
- voice_name 是**玩家会做的事**（如"向王牙人借三两/先赊账度日/卖布应急"），
  **不是**情绪名（不要"算盘声/本分/手艺人的骄傲"这种）
- 覆盖：应急方案（今天能做的）+ 治本方案（1~3 回合）+ 迂回方案（避开硬碰）
- 贴合万历十五年社会现实（钱/粮/差役/人情/官府/邻里/家族）
- 严格 JSON 数组输出，不要其他文字"""

    resp = llm.invoke([
        SystemMessage(content="你是明朝万历年间的游戏引导者，严格输出 JSON 数组。"),
        HumanMessage(content=prompt),
    ])

    raw = (resp.content or "").strip()
    parsed = None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            parsed = data
        elif isinstance(data, dict):
            parsed = data.get("options") or data.get("voice_options") or [data]
    except json.JSONDecodeError:
        try:
            extracted = extract_json_from_text(raw)
            if isinstance(extracted, list):
                parsed = extracted
            elif isinstance(extracted, dict):
                parsed = [extracted]
        except Exception:
            parsed = None

    validated = []
    if isinstance(parsed, list):
        for o in parsed[:4]:
            if not isinstance(o, dict):
                continue
            vname = (o.get("voice_name") or "").strip()
            if not vname:
                continue
            validated.append({
                "voice_id": o.get("voice_id") or f"ctx_{len(validated)}",
                "voice_name": vname[:20],
                "intent_text": (o.get("intent_text") or "").strip()[:80],
                "is_freetext": False,
                "_is_context": True,  # 标记，区别于 DM 原生 voice_options
            })
    return validated


def _fallback_keyword_voices(narr_text: str) -> list:
    """v1.7.22 原版关键词匹配兜底（v2.3 仅在 LLM 失败时使用）"""
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

    # 🆕 v1.7.28：输入验证（非游戏内容检测）
    from history_footnote.input_validator import validate_input, is_low_quality_input
    if is_low_quality_input(inp):
        result = validate_input(inp, knowledge_matched=0, knowledge_matched_required=0)
        handler._json(400, {
            "error": result.reason,
            "message": result.message,
            "suggestion": result.suggestion,
            "retryable": True,
        })
        return True
    result = validate_input(inp, knowledge_matched=0, knowledge_matched_required=0)
    if not result.is_valid:
        handler._json(400, {
            "error": result.reason,
            "message": result.message,
            "suggestion": result.suggestion,
            "retryable": True,
        })
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


# ============================================================
# /api/location/* — v2.4 文字地图系统
# ============================================================

def _get_location_service_for_session(sid: str):
    """从 session 中获取 location_service 实例"""
    from history_footnote.location_service import build_location_service
    entry = session_get(sid)
    if not entry:
        return None, None, None
    game = entry[0]
    era_config = getattr(game, "era_config", None)
    if not era_config:
        return None, None, None
    return build_location_service(era_config), game, entry[1]


def handle_POST_location_move(handler, body) -> bool:
    """POST /api/location/move — 移动到目标地点（消耗 AP）

    Request:
        {
            "session_id": "...",
            "target": "tooth_market"  // 目标 location id
        }

    Response:
        {
            "success": true,
            "from_location": "home",
            "to_location": "tooth_market",
            "ap_cost": 1.0,
            "time_mode": "now_time",
            "new_ap": 2.0,
            "new_voice_options": [...],  // 新地点的选项（包含移动）
            "narrative": "你沿着青石板路往西走..."  // 简短移动叙事
        }
    """
    sid = body.get("session_id")
    target = body.get("target", "").strip()
    if not sid or not target:
        handler._json(400, {"error": "missing session_id or target"})
        return True

    svc, game, lock = _get_location_service_for_session(sid)
    if not svc or not game:
        handler._json(404, {"error": "session not found"})
        return True

    with lock:
        from_id = game.state.current_location or svc.get_default()
        visited = list(game.state.visited_locations or [])
        heard = list(game.state.heard_locations or [])
        ap = float(getattr(game.state, "action_points_current", 3) or 3)

        result = svc.can_move(from_id, target, visited, heard, ap)
        if not result.success:
            handler._json(400, {
                "error": "cannot_move",
                "reason": result.reason,
                "from_location": from_id,
                "to_location": target,
            })
            return True

        # 移动成功：更新 state
        game.state.current_location = target
        if target not in visited:
            visited.append(target)
            game.state.visited_locations = visited
        game.state.action_points_current = max(0, ap - result.ap_cost)

        # 触发 heard 解锁检查
        newly_heard = svc.check_unlock_hooks(game.state)
        if newly_heard:
            cur_heard = list(game.state.heard_locations or [])
            for h in newly_heard:
                if h not in cur_heard:
                    cur_heard.append(h)
            game.state.heard_locations = cur_heard

        # 生成"新地点"选项（含移动选项）
        new_voices = svc.get_move_options(
            target, visited, list(game.state.heard_locations or []),
            game.state.action_points_current,
        )

        # 简单移动叙事（不调 LLM，节省 token）
        to_loc = svc.get(target)
        narrative = f"你到了{to_loc.name}。{to_loc.description}"

        # 🆕 v2.4.1 路遇事件（30% 概率触发，v2.5 起支持 seed 重放）
        encounter = None
        try:
            encounter = svc.roll_encounter(from_id, target, session_id=sid)
            if encounter:
                encounter_text = svc.build_encounter_narrative(encounter)
                narrative = encounter_text + " " + narrative
                logger.info(f"[v2.5] 路遇触发: {encounter.get('npc')} ({from_id}→{target})")
        except Exception as e:
            logger.warning(f"[v2.5] roll_encounter 失败: {e}")

        # 🆕 v2.4.1 该地 NPC
        npcs_at_dest = svc.get_npcs_at(target)

        logger.info(
            f"[v2.4 location] sid={sid[:8]} {from_id}→{target} AP={result.ap_cost} "
            f"new_heard={[svc.get_name(h) for h in newly_heard]}"
        )

        handler._json(200, {
            "success": True,
            "from_location": from_id,
            "to_location": target,
            "to_location_name": to_loc.name,
            "ap_cost": result.ap_cost,
            "time_mode": result.time_mode,
            "new_ap": game.state.action_points_current,
            "new_voice_options": new_voices,
            "narrative": narrative,
            "newly_heard": [svc.get_name(h) for h in newly_heard],
            "encounter": encounter,  # 🆕 v2.4.1 路遇事件（None 或 {npc, event}）
            "npcs_at": npcs_at_dest,  # 🆕 v2.4.1 该地所有 NPC
            "location": {
                "id": to_loc.id,
                "name": to_loc.name,
                "tier": to_loc.tier,
                "description": to_loc.description,
                "atmosphere_sound": to_loc.atmosphere_sound,
                "npcs_default": to_loc.npcs_default,
                "neighbors": [svc.get_name(n) for n in to_loc.neighbors],
            },
            **format_state(game),
        })
    return True


def handle_GET_location_list(handler, body) -> bool:
    """GET /api/location/list — 获取地图信息（已访问 + 听过 + 当前）

    Request:
        {"session_id": "..."}

    Response:
        {
            "current_location": {...},
            "visited": [{...}],
            "heard": [...],  // 听过没去过（标 ❓）
            "unseen": [...]   // 存在但玩家不知道
        }
    """
    sid = body.get("session_id")
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True

    svc, game, lock = _get_location_service_for_session(sid)
    if not svc or not game:
        handler._json(404, {"error": "session not found"})
        return True

    with lock:
        current = game.state.current_location or svc.get_default()
        visited = set(game.state.visited_locations or [])
        heard = set(game.state.heard_locations or [])

        def fmt(loc_id: str) -> dict:
            loc = svc.get(loc_id)
            if not loc:
                return {"id": loc_id, "name": loc_id, "unknown": True}
            return {
                "id": loc.id,
                "name": loc.name,
                "tier": loc.tier,
                "type": loc.type,
                "description": loc.description,
            }

        # 触发 heard 解锁检查（玩家可能满足新条件）
        newly_heard = svc.check_unlock_hooks(game.state)
        if newly_heard:
            cur_heard = list(game.state.heard_locations or [])
            for h in newly_heard:
                if h not in cur_heard:
                    cur_heard.append(h)
            game.state.heard_locations = cur_heard
            heard.update(newly_heard)

        all_locs = svc.all_l1_l2()
        visited_l = [fmt(l.id) for l in all_locs if l.id in visited]
        heard_l = [fmt(l.id) for l in all_locs if l.id in heard and l.id not in visited]
        unseen_l = [fmt(l.id) for l in all_locs if l.id not in visited and l.id not in heard]

        handler._json(200, {
            "city_name": svc.city_name,
            "city_intro": svc.city_intro,
            "current_location": fmt(current),
            "visited": visited_l,
            "heard": heard_l,
            "unseen": unseen_l,
            "newly_heard": [svc.get_name(h) for h in newly_heard],
        })
    return True


def handle_GET_location_detail(handler, body) -> bool:
    """GET /api/location/detail — 获取某个地点的详情 + 可去选项

    Request:
        {"session_id": "...", "location_id": "tooth_market"}
    """
    sid = body.get("session_id")
    loc_id = body.get("location_id", "").strip()
    if not sid or not loc_id:
        handler._json(400, {"error": "missing session_id or location_id"})
        return True

    svc, game, lock = _get_location_service_for_session(sid)
    if not svc or not game:
        handler._json(404, {"error": "session not found"})
        return True

    with lock:
        loc = svc.get(loc_id)
        if not loc:
            handler._json(404, {"error": "location not found"})
            return True

        visited = list(game.state.visited_locations or [])
        heard = list(game.state.heard_locations or [])
        ap = float(getattr(game.state, "action_points_current", 3) or 3)

        # 从此地点出发的"可去"选项
        move_opts = svc.get_move_options(loc_id, visited, heard, ap)

        handler._json(200, {
            "id": loc.id,
            "name": loc.name,
            "tier": loc.tier,
            "type": loc.type,
            "tone": loc.tone,
            "description": loc.description,
            "atmosphere_sound": loc.atmosphere_sound,
            "npcs_default": loc.npcs_default,
            "neighbors": [svc.get_name(n) for n in loc.neighbors],
            "events": loc.events,
            "move_options": move_opts,
        })
    return True


# ============================================================
# /api/fate/* — v2.5 命运卡系统
# ============================================================

def handle_GET_fate_hand(handler, body) -> bool:
    """GET /api/fate/hand — 获取当前手牌（命运卡）

    Returns:
        {
            "hand": [{"id": "windfall", "name": "天降横财", "icon": "💰", "color": "...", "description": "...", "used": false}, ...],
            "used": ["..."]
        }
    """
    sid = body.get("session_id")
    if not sid:
        handler._json(400, {"error": "missing session_id"})
        return True

    _, game, _ = _get_location_service_for_session(sid)
    if not game:
        handler._json(404, {"error": "session not found"})
        return True

    handler._json(200, {
        "hand": list(getattr(game.state, "fate_hand", []) or []),
        "used": list(getattr(game.state, "fate_used", []) or []),
    })
    return True


def handle_POST_fate_use(handler, body) -> bool:
    """POST /api/fate/use — 触发一张命运卡

    Request:
        {
            "session_id": "...",
            "card_id": "windfall"
        }

    Returns:
        {
            "success": true,
            "card": {...},
            "messages": ["银两 +3.00（现 8.50）"],
            "state": {...}
        }
    """
    sid = body.get("session_id")
    card_id = body.get("card_id", "").strip()
    if not sid or not card_id:
        handler._json(400, {"error": "missing session_id or card_id"})
        return True

    _, game, _ = _get_location_service_for_session(sid)
    if not game:
        handler._json(404, {"error": "session not found"})
        return True

    hand = list(getattr(game.state, "fate_hand", []) or [])
    card = next((c for c in hand if c.get("id") == card_id and not c.get("used")), None)
    if not card:
        handler._json(400, {"error": "card not found or already used"})
        return True

    # 应用效果
    from history_footnote.fate_cards import FateCard, apply_fate_card
    fc = FateCard(
        id=card["id"], name=card["name"], icon=card["icon"], color=card["color"],
        description=card["description"], effect_type=card["effect_type"],
        effect_params=card["effect_params"],
    )
    messages = apply_fate_card(fc, game.state)

    # 标记已用
    for c in hand:
        if c.get("id") == card_id:
            c["used"] = True
    game.state.fate_hand = hand
    used = list(getattr(game.state, "fate_used", []) or [])
    if card_id not in used:
        used.append(card_id)
    game.state.fate_used = used

    handler._json(200, {
        "success": True,
        "card": card,
        "messages": messages,
        "state": {k: getattr(game.state, k, None) for k in [
            "cash", "debt", "rice", "action_points_current",
            "reputation", "fate_hand", "fate_used", "heard_locations"
        ]},
    })
    return True


