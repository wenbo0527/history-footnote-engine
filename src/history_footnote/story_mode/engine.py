"""🆕 v2.10.16 Phase 10 — ScriptedStoryEngine 故事模式引擎

零 LLM 调用:
- 玩家输入 → 匹配当前 node 的 voice_options
- D&D 风格: flag 组合 + 触发条件 + effects
- 输出: narrative + voice_options + 状态变化

API 跟现有 /api/input 完全兼容 (前端零改动):
- 接收: {session_id, input}
- 返回: {narrative, voice_options, scripted_node_id, ...}
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from history_footnote.story_mode.chapter_01 import get_chapter_01
from history_footnote.story_mode.types import (
    ScriptedChapter,
    ScriptedNode,
    ScriptedVoiceOption,
)

_LOG = logging.getLogger("history_footnote.story_mode.engine")


class ScriptedStoryEngine:
    """故事模式引擎 (0 LLM)"""

    def __init__(self, chapter: Optional[ScriptedChapter] = None):
        self.chapter = chapter or get_chapter_01()

    # ============================================================
    # 状态操作（直接读写 game state dict）
    # ============================================================

    @staticmethod
    def ensure_state(game_state: dict) -> dict:
        """确保 game_state 有故事模式字段"""
        if not game_state.get("scripted_mode"):
            game_state["scripted_mode"] = False
            game_state["scripted_chapter_id"] = 0
            game_state["scripted_node_id"] = ""
            game_state["scripted_flags"] = []
            game_state["scripted_visits"] = []
            game_state["scripted_chapter_complete"] = False
        return game_state

    def start_chapter(self, game_state: dict, chapter_id: int = 1) -> tuple[str, list[ScriptedVoiceOption]]:
        """开始一章剧本（重置 node + flags）"""
        self.ensure_state(game_state)
        game_state["scripted_mode"] = True
        game_state["scripted_chapter_id"] = chapter_id
        game_state["scripted_node_id"] = self.chapter.start_node_id
        game_state["scripted_flags"] = []
        game_state["scripted_visits"] = []
        game_state["scripted_chapter_complete"] = False

        return self._get_current_view(game_state)

    def get_current(self, game_state: dict) -> tuple[str, list[ScriptedVoiceOption]]:
        """获取当前节点视图（不动状态）"""
        self.ensure_state(game_state)
        return self._get_current_view(game_state)

    def handle_input(self, game_state: dict, voice_id: str) -> tuple[str, list[ScriptedVoiceOption], dict]:
        """处理玩家选择，返回 (narrative, options, info)

        info 包含:
        - chapter_complete: bool
        - new_node_id: str
        - effects_applied: dict
        - flag_added: list
        """
        self.ensure_state(game_state)
        node_id = game_state.get("scripted_node_id") or self.chapter.start_node_id
        node = self.chapter.nodes.get(node_id)
        if node is None:
            return self._error(game_state, f"node not found: {node_id}")

        # 找匹配的 voice_option
        opt = next((o for o in node.voice_options if o.voice_id == voice_id), None)
        if opt is None:
            # 模糊匹配（兼容前端 typo）
            opt = self._fuzzy_match(voice_id, node.voice_options)
            if opt is None:
                return self._error(game_state, f"voice_id not found: {voice_id}")

        # 1. 应用 effects
        effects_applied = dict(opt.effects)
        self._apply_effects(game_state, effects_applied)

        # 2. 设置 flag
        flag_added = []
        for flag in effects_applied.pop("flag_set", []):
            if flag not in game_state["scripted_flags"]:
                game_state["scripted_flags"].append(flag)
                flag_added.append(flag)

        # 3. city_move 效果
        city_move = effects_applied.pop("city_move", None)
        if city_move:
            game_state["city"] = city_move

        # 4. 跳转节点
        next_node_id = opt.next_node_id
        if not next_node_id:
            return self._error(game_state, "voice_option has no next_node_id")

        # 5. 章节完成判断
        chapter_complete = next_node_id in self.chapter.end_node_ids
        if chapter_complete:
            game_state["scripted_chapter_complete"] = True

        game_state["scripted_node_id"] = next_node_id
        if next_node_id not in game_state["scripted_visits"]:
            game_state["scripted_visits"].append(next_node_id)

        # 6. 返回新视图
        narr, options = self._get_current_view(game_state)

        info = {
            "chapter_complete": chapter_complete,
            "new_node_id": next_node_id,
            "effects_applied": effects_applied,
            "flag_added": flag_added,
        }
        return narr, options, info

    # ============================================================
    # 内部方法
    # ============================================================

    def _get_current_view(self, game_state: dict) -> tuple[str, list[ScriptedVoiceOption]]:
        """获取当前节点的 (narrative, voice_options)"""
        node_id = game_state.get("scripted_node_id") or self.chapter.start_node_id
        node = self.chapter.nodes.get(node_id)
        if node is None:
            return "【剧本损坏：找不到节点】", []

        # 应用 on_enter 效果 (一次性)
        if node.on_enter_effects or node.on_enter_text:
            self._apply_effects(game_state, node.on_enter_effects)

        narrative = node.narrative
        if node.on_enter_text:
            narrative = node.on_enter_text + "\n\n" + narrative

        return narrative, node.voice_options

    def _apply_effects(self, game_state: dict, effects: dict[str, Any]) -> None:
        """应用 effects 到 game_state"""
        for k, v in effects.items():
            if k == "cash_delta":
                game_state["cash"] = (game_state.get("cash") or 0) + v
            elif k == "debt_delta":
                game_state["debt"] = (game_state.get("debt") or 0) + v
            elif k == "rice_delta":
                game_state["rice"] = (game_state.get("rice") or 0) + v
            elif k == "looms_delta":
                game_state["looms"] = (game_state.get("looms") or 0) + v
            elif k == "stamina_delta":
                # 模拟 health/stamina 字段
                if "stamina" in game_state:
                    game_state["stamina"] = (game_state.get("stamina") or 0) + v
            elif k == "father_health_delta":
                # 简化：写到 character 字段（如果存在）
                if "father_health" not in game_state:
                    game_state["father_health"] = 50
                game_state["father_health"] = max(0, min(100, game_state["father_health"] + v))
            elif k == "flag_set":
                pass  # 已在 handle_input 中处理
            elif k == "city_move":
                pass  # 已在 handle_input 中处理
            else:
                _LOG.warning(f"unknown effect key: {k}")

    def _fuzzy_match(self, voice_id: str, options: list[ScriptedVoiceOption]) -> Optional[ScriptedVoiceOption]:
        """模糊匹配（兼容前端输入差异）"""
        vid = voice_id.lower().strip()
        for o in options:
            if o.voice_id.lower() == vid:
                return o
            if voice_id == o.voice_id or vid == o.voice_id:
                return o
        return None

    def _error(self, game_state: dict, msg: str) -> tuple[str, list[ScriptedVoiceOption], dict]:
        _LOG.warning(msg)
        return f"【剧本错误：{msg}】", [], {"error": msg}

    # ============================================================
    # 导出给前端（兼容现有 VoiceOption 格式）
    # ============================================================

    def export_voice_options(self, options: list[ScriptedVoiceOption]) -> list[dict]:
        """导出为前端格式（兼容现有 VoiceOption）"""
        return [
            {
                "voice_id": o.voice_id,
                "voice_name": o.voice_name,
                "description": o.description,
                "inner_voice": o.inner_voice,
            }
            for o in options
        ]


# 单例
_engine = None


def get_engine() -> ScriptedStoryEngine:
    """获取故事引擎单例"""
    global _engine
    if _engine is None:
        _engine = ScriptedStoryEngine()
    return _engine