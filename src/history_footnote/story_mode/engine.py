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
import random
from typing import Any, Optional

from history_footnote.story_mode.chapter_01 import get_chapter_01
from history_footnote.story_mode.rich import (
    EnvironmentContext,
    NarrativeSection,
    maybe_trigger_encounter,
    perform_check,
    random_env_phrase,
    roll_d20,
)
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
        self._chapter_id = self.chapter.chapter_id if self.chapter else 1

    def set_chapter_by_id(self, chapter_id: int) -> None:
        """🆕 v2.10.18: 切换章节"""
        from history_footnote.story_mode.chapter_02 import get_chapter_02
        if chapter_id == 1:
            self.chapter = get_chapter_01()
        elif chapter_id == 2:
            self.chapter = get_chapter_02()
        else:
            self.chapter = get_chapter_01()
        self._chapter_id = self.chapter.chapter_id

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
        # 切换章节
        if chapter_id != self.chapter.chapter_id:
            self.set_chapter_by_id(chapter_id)

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
        """获取当前节点的 (narrative, voice_options)

        🆕 v2.10.17 增强:
        - 自动注入环境描写
        - 触发随机事件 (D&D 检定)
        """
        node_id = game_state.get("scripted_node_id") or self.chapter.start_node_id
        node = self.chapter.nodes.get(node_id)
        if node is None:
            return "【剧本损坏：找不到节点】", []

        # 应用 on_enter 效果 (一次性)
        if node.on_enter_effects or node.on_enter_text:
            self._apply_effects(game_state, node.on_enter_effects)

        # 🆕 注入环境描写
        env = EnvironmentContext(
            city=game_state.get("city", "shengze"),
            city_chinese="盛泽镇" if game_state.get("city", "shengze") == "shengze" else "苏州府",
        )
        env_label = env.env_label()
        env_phrase = random_env_phrase(env)

        # 组装 narrative (环境 + 节点 + 进入文本)
        narrative = f"{env_label}\n{env_phrase}\n\n{node.narrative}"
        if node.on_enter_text:
            narrative = f"{env_label}\n{env_phrase}\n\n{node.on_enter_text}\n\n" + node.narrative

        # 🆕 随机事件触发 (D&D 检定)
        round_num = game_state.get("round_number", 1)
        encounters = getattr(self.chapter, "random_encounters", []) or []
        triggered = maybe_trigger_encounter(encounters, game_state, round_num)
        if triggered:
            encounter_text, encounter_effects = self._resolve_encounter(triggered, game_state)
            narrative += f"\n\n🔀 【随机事件：{triggered.name}】\n{encounter_text}"

        return narrative, node.voice_options

    def _resolve_encounter(
        self,
        encounter,
        game_state: dict,
    ) -> tuple[str, dict]:
        """解析随机事件，根据 d20 检定返回 narrative + effects"""
        # 取角色属性 (简化: 用 cash 或 city 推断)
        attr_value = 2
        # 高 cash = 富裕 = 高 charisma
        if (game_state.get("cash") or 0) >= 5:
            attr_value = 4
        # 有 met_merchant flag = 高 luck
        if "met_big_merchant" in (game_state.get("scripted_flags") or []):
            attr_value = 5

        result, d20_value = perform_check(attr_value, encounter.check_difficulty)

        if result == "great_success":
            sections = encounter.great_success_sections
            effects = dict(encounter.great_success_effects)
        elif result == "success":
            sections = encounter.success_sections
            effects = dict(encounter.success_effects)
        else:
            sections = encounter.fail_sections
            effects = dict(encounter.fail_effects)

        # 渲染 sections
        text_lines = []
        for s in sections:
            prefix = ""
            if s.narrator == "内心":
                prefix = "💭 "
            elif s.narrator == "旁白":
                prefix = ""
            else:
                prefix = f"【{s.narrator}】"
            text_lines.append(f"{prefix}{s.text}")

        text = "\n".join(text_lines)
        text += f"\n\n🎲 d20={d20_value} + attr={attr_value} ≥ 难度{encounter.check_difficulty} → {result}"

        # 应用 effects (会写到 state)
        if effects:
            self._apply_effects(game_state, effects)
            for flag in effects.get("flag_set", []):
                if flag not in game_state.get("scripted_flags", []):
                    game_state.setdefault("scripted_flags", []).append(flag)

        return text, effects

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