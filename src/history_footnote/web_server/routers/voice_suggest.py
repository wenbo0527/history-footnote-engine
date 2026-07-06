"""🆕 v1.7.30 玩家主动求建议：/api/voice_options/suggest

设计：
- 玩家点"✨ 帮我一下"时调这个端点
- 后端 LLM 基于（最近 narrative + state + 时代包）生成 3~5 个
  玩家**可执行的方案**（不是情绪名）
- 触发条件：当前 voiceOptions 数量 < 2（前端控制）
- 数据契约：复用 voice_options schema（voice_id/voice_name/intent_text）
- 建议选项**不写回** state.last_voice_options（避免污染 DM 下次输入）
- 限流：全局 60/min + session 30/min

🆕 v1.7.30 prompt 思路：基于玩家面对的**具体问题**给可执行方案，不是情绪名

设计动机（用户反馈）：
- 之前给"算盘声/本分/手艺人的骄傲"是情绪名 → 不解决问题
- 现在给"向赵里长求减免/先赊账度日/卖布应急"是动作 → 解决具体问题
"""
from __future__ import annotations

import json
from langchain_core.messages import HumanMessage, SystemMessage

from history_footnote.narrative_sanitizer import extract_json_from_text
from history_footnote.resource_cache import load_era_config
from history_footnote.web_enhancements import (
    LLM_RATE_LIMITER,
    SESSION_LLM_RATE_LIMITER,
)
from history_footnote.web_server.handler_base import logger, safe_error_id
from history_footnote.web_server.views.session import _get_or_load_session


# 🆕 v1.7.30 修正后的 prompt：基于具体问题给可执行方案
_SUGGEST_PROMPT = """你是 DM 引导者。玩家是 {identity}，当前第 {round_number} 回合。

玩家面对的局面（最近叙事）：
\"\"\"
{narrative}
\"\"\"

**请基于玩家面对的具体问题，给出 3~5 个可行的应对方案。**

每条一行 JSON：
{{
  "voice_id": "<id>",
  "voice_name": "<3~8 字短句，是玩家可执行的动作>",
  "intent_text": "<一句话解释为何这样做>"
}}

要求：
- voice_name 是**玩家会做的事**（如"向赵里长求减免"/"先赊账度日"/"卖布应急"），
  **不是**情绪名（如"算盘声"/"本分"）
- 覆盖：应急方案（今天能做的）+ 治本方案（1~3 回合才能办成）+ 迂回方案（避开硬碰）
- 贴合万历十五年社会现实（钱/粮/差役/人情/官府/邻里/家族）
- 如果玩家面临的问题不明确，voice_name 可用"先观察一阵/等消息/问个明白"
- 严格 JSON 数组输出，不要其他文字
"""


def handle_POST_voice_options_suggest(handler, body) -> bool:
    """POST /api/voice_options/suggest — 玩家主动求 LLM 补充选项

    触发条件（前端控制）：当前 voiceOptions 数量 < 2
    输入：{ "session_id": "..." }
    输出：{ "voice_options": [...], "from_suggestion": true, "round_number": N }
    """
    # 双层限流：全局 + session
    client_ip = handler.client_address[0]
    if not LLM_RATE_LIMITER.allow(client_ip):
        handler._json(429, {"error": "Too Many LLM Requests", "scope": "global"})
        return True

    sid = body.get("session_id", "").strip()
    if not sid:
        handler._json(400, {"error": "session_id required"})
        return True

    if not SESSION_LLM_RATE_LIMITER.allow(f"sid:{sid}"):
        handler._json(429, {
            "error": "Too Many Suggestions",
            "scope": "session",
            "message": "DM 累了，请直接输入或稍后再试",
        })
        return True

    game = _get_or_load_session(sid)
    if not game:
        handler._json(404, {"error": "session not found"})
        return True

    try:
        # 1. 收集上下文
        last_narr = (game.state.narrative_history or [])[-1] if game.state.narrative_history else None
        narrative_text = (last_narr or {}).get("narrative", "")[:600] or "（无最近叙事）"
        round_number = game.state.round_number or 0
        identity = game.state.selected_identity or "未选身份"

        # 2. 调 LLM
        config = load_era_config(game.era_id)
        from history_footnote.llm_wrapper import get_wrapped_llm
        llm = get_wrapped_llm(primary_provider="minimax-anthropic", era_config=config)
        prompt = _SUGGEST_PROMPT.format(
            identity=identity,
            round_number=round_number,
            narrative=narrative_text,
        )
        try:
            resp = llm.invoke([
                SystemMessage(content="你是明朝万历年间的游戏引导者，严格输出 JSON 数组。"),
                HumanMessage(content=prompt),
            ])
        except Exception as e:
            error_id = safe_error_id()
            logger.exception(f"[voice_options_suggest] {error_id} LLM 失败: {e}")
            handler._json(502, {
                "error": "DM 在忙，请稍后重试或直接输入",
                "error_id": error_id,
            })
            return True

        # 3. 解析 + 兜底（LLM 偶返回脏 JSON / 单 dict 而非数组）
        raw = (resp.content or "").strip()
        parsed = None
        try:
            # 先尝试直接 JSON
            data = json.loads(raw)
            if isinstance(data, list):
                parsed = data
            elif isinstance(data, dict):
                # 可能包了 options 字段
                parsed = data.get("options") or data.get("voice_options") or [data]
        except json.JSONDecodeError:
            # 退到 extract_json_from_text
            try:
                extracted = extract_json_from_text(raw)
                if isinstance(extracted, list):
                    parsed = extracted
                elif isinstance(extracted, dict):
                    parsed = [extracted]
            except Exception as e:
                logger.exception(f"[voice_options_suggest] JSON 解析失败: {e}")
                parsed = None

        # 4. 验证：voice_name 必填
        validated = []
        if isinstance(parsed, list):
            for o in parsed[:5]:
                if not isinstance(o, dict):
                    continue
                vname = (o.get("voice_name") or "").strip()
                if not vname:
                    continue
                validated.append({
                    "voice_id": o.get("voice_id") or f"suggest_{len(validated)}",
                    "voice_name": vname[:20],  # 防超长
                    "intent_text": (o.get("intent_text") or "").strip()[:80],
                    "is_freetext": False,
                    "_is_suggestion": True,  # 标记，前端可区分
                })

        # 5. 完全没拿到时兜底（不返回 500，给几个硬编码应急选项）
        if not validated:
            logger.warning(f"[voice_options_suggest] LLM 返回空选项，sid={sid[:16]}")
            validated = [
                {"voice_id": "sug_fallback_1", "voice_name": "先观察一阵",
                 "intent_text": "等事态明朗再动", "is_freetext": False, "_is_suggestion": True},
                {"voice_id": "sug_fallback_2", "voice_name": "找邻居问问",
                 "intent_text": "问问人看有没有主意", "is_freetext": False, "_is_suggestion": True},
                {"voice_id": "sug_fallback_3", "voice_name": "想清楚再做",
                 "intent_text": "不急，先把思路理清", "is_freetext": False, "_is_suggestion": True},
            ]

        handler._json(200, {
            "voice_options": validated,
            "from_suggestion": True,
            "round_number": round_number,
            "fallback_used": len(validated) == 3 and validated[0].get("voice_id", "").startswith("sug_fallback"),
        })
    except Exception as e:
        error_id = safe_error_id()
        logger.exception(f"[voice_options_suggest] {error_id} failed: {e}")
        handler._json(500, {"error": "suggest failed", "error_id": error_id})
    return True
