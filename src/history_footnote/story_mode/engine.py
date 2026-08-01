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
        from history_footnote.story_mode.chapter_03 import get_chapter_03
        if chapter_id == 1:
            self.chapter = get_chapter_01()
        elif chapter_id == 2:
            self.chapter = get_chapter_02()
        elif chapter_id == 3:
            self.chapter = get_chapter_03()
        else:
            self.chapter = get_chapter_01()
        self._chapter_id = self.chapter.chapter_id

    # ============================================================
    # 状态操作（直接读写 game state dict）
    # ============================================================

    @staticmethod
    def ensure_state(game_state: dict) -> dict:
        """确保 game_state 有故事模式字段 (只补缺失的 key, 不覆盖已有值)"""
        if "scripted_mode" not in game_state:
            game_state["scripted_mode"] = False
        if "scripted_chapter_id" not in game_state:
            game_state["scripted_chapter_id"] = 0
        if "scripted_node_id" not in game_state:
            game_state["scripted_node_id"] = ""
        if "scripted_flags" not in game_state:
            game_state["scripted_flags"] = []
        if "scripted_visits" not in game_state:
            game_state["scripted_visits"] = []
        if "scripted_chapter_complete" not in game_state:
            game_state["scripted_chapter_complete"] = False
        return game_state

    def start_chapter(self, game_state: dict, chapter_id: int = 1) -> tuple[str, list[ScriptedVoiceOption]]:
        """开始一章剧本（重置 node + flags，不重置主游戏 cash/debt）

        🆕 v2.10.22: 改造为不重置主游戏状态 (cash/debt/rice/looms 保留)
        """
        self.ensure_state(game_state)
        # 切换章节
        if chapter_id != self.chapter.chapter_id:
            self.set_chapter_by_id(chapter_id)

        game_state["scripted_mode"] = True
        game_state["scripted_chapter_id"] = chapter_id
        game_state["scripted_node_id"] = self.chapter.start_node_id
        # 重置脚本状态 (但保留 cash/debt/rice/looms 等主游戏状态)
        game_state["scripted_flags"] = []
        game_state["scripted_visits"] = []
        game_state["scripted_chapter_complete"] = False

        return self._get_current_view(game_state)

    def exit_scripted_mode(self, game_state: dict) -> dict:
        """🆕 v2.10.22: 退出剧本模式

        保留 scripted_flags 作为 LLM 提示
        """
        self.ensure_state(game_state)
        game_state["scripted_mode"] = False
        # 保留 scripted_flags (作为 LLM context)
        # 清空 active state
        game_state["scripted_chapter_complete"] = False
        return game_state

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

        # 🆕 v2.10.22: D&D 检定 — 在跳转之前决定目标节点
        check_result = None
        check_d20 = None
        if opt.check:
            check_result, check_d20 = self._do_check(opt.check, game_state)

        # 1. 应用 effects
        effects_applied = dict(opt.effects)
        self._apply_effects(game_state, effects_applied)

        # 2. 设置 flag
        flag_added = []
        # 检定结果作为 flag
        if opt.check:
            flag_added.append(f"check:{check_result}:{opt.check}")
        for flag in effects_applied.pop("flag_set", []):
            if flag not in game_state["scripted_flags"]:
                game_state["scripted_flags"].append(flag)
                flag_added.append(flag)

        # 3. city_move 效果
        city_move = effects_applied.pop("city_move", None)
        if city_move:
            game_state["city"] = city_move

        # 4. 跳转节点 (检定影响)
        if opt.check:
            # success 或 great_success 都用 check_success_node
            # fail 用 check_fail_node
            # 没有对应节点时 fallback 到 next_node_id
            if check_result in ("great_success", "success") and opt.check_success_node:
                next_node_id = opt.check_success_node
            elif check_result == "fail" and opt.check_fail_node:
                next_node_id = opt.check_fail_node
            else:
                next_node_id = opt.next_node_id
        else:
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
        - 🆕 v2.10.19: 跨章回响 — 根据第一章 flag 动态调整 narrative
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

        # 🆕 v2.10.19: 跨章回响 — 第二章开局根据第一章 flag 动态调整
        narrative = self._apply_chapter_echo(narrative, game_state, node_id)

        # 🆕 随机事件触发 (D&D 检定)
        round_num = game_state.get("round_number", 1)
        encounters = getattr(self.chapter, "random_encounters", []) or []
        triggered = maybe_trigger_encounter(encounters, game_state, round_num)
        if triggered:
            encounter_text, encounter_effects = self._resolve_encounter(triggered, game_state)
            narrative += f"\n\n🔀 【随机事件：{triggered.name}】\n{encounter_text}"

        return narrative, node.voice_options

    def _apply_chapter_echo(self, narrative: str, game_state: dict, node_id: str) -> str:
        """🆕 v2.10.19: 跨章回响 — 第一章 flag 动态影响第二章 narrative"""
        chapter_id = self.chapter.chapter_id if self.chapter else 1
        flags = set(game_state.get("scripted_flags") or [])
        cash = game_state.get("cash") or 0
        debt = game_state.get("debt") or 0
        rice = game_state.get("rice") or 0
        looms = game_state.get("looms") or 0

        # 第二章专属回响
        if chapter_id == 2 and node_id == "ch2_intro_normal":
            echoes = []
            # 第一章 prosperity → 开局描述
            if "prosperous" in flags or cash >= 5:
                echoes.append("\n\n🆕 第一章回响：你攒下了些银钱，家境尚可。")
            elif debt > 0:
                echoes.append(f"\n\n🆕 第一章回响：你仍欠着 {debt} 两银子，月息压得你喘不过气。")
            if "has_debt" in flags:
                echoes.append("\n🆕 牙行钱老板的儿子钱少见你，目光闪烁。")
            if "zhou_favor" in flags:
                echoes.append("\n🆕 周大娘托人捎来口信：'沈老弟，有空来坐坐。'")
            if "met_big_merchant" in flags:
                echoes.append("\n🆕 苏州大绸商仍记得你，名帖还在案头。")
            if "sold_loom" in flags:
                echoes.append(f"\n🆕 你只剩 {looms} 架织机，产能捉襟见肘。")
            if "learned_qixia" in flags:
                echoes.append("\n🆕 你掌握了'绮霞罗'织法，这是盛泽镇不传之秘。")
            if "met_zhang" in flags or "zhang_helped" in flags:
                echoes.append("\n🆕 张叔对你仍有信任，是你的靠山。")
            if echoes:
                narrative += "\n".join(echoes)

        # 第三章专属回响 (承接 ch1 + ch2)
        if chapter_id == 3 and node_id == "ch3_intro_normal":
            ch3_echoes = []
            if "ch2_prosperous" in flags or cash >= 10:
                ch3_echoes.append("\n\n🆕 第二章回响：你家境小康，三架织机仍转。")
            if "merchant_disgraced" in flags:
                ch3_echoes.append("\n🆕 第二章回响：你在苏州商誉受损，订单减少。")
            if "master_dyer" in flags or "knew_color_master" in flags:
                ch3_echoes.append("\n🆕 第二章回响：你织染技艺了得，可号召同行抗税。")
            if "father_will" in flags or "father_secret" in flags:
                ch3_echoes.append("\n\n🆕 父亲遗愿：万历九年的丝绢案冤情，你手中尚有文书证据。")
            if "zhang_helped" in flags:
                ch3_echoes.append("\n🆕 第二章回响：张叔仍可信赖，可联合抗税。")
            if "child_born" in flags:
                ch3_echoes.append("\n🆕 第二章回响：你有了孩子，家庭羁绊更深。")
            if "wife_dead" in flags:
                ch3_echoes.append("\n🆕 第二章回响：妻子已逝，你孤身一人，抗税决心更坚。")
            if ch3_echoes:
                narrative += "\n".join(ch3_echoes)

        return narrative

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

    def _do_check(self, check_expr: str, game_state: dict) -> tuple[str, int]:
        """🆕 v2.10.22: 执行 D&D 检定

        check_expr 格式:
        - "charisma >= 2" → 属性检定 (d20+charisma vs DC)
        - "cash >= 3" → 资源硬性检查 (>= 即过, 否则 fail)
        - "luck >= 4" → 随机检定
        - "flag.has_debt" → flag 存在检查

        返回 (结果档位, d20 值)
        结果档位: "great_success" / "success" / "fail"
        """
        try:
            # 解析 "<attr> <op> <value>"
            parts = check_expr.split()
            if len(parts) != 3:
                # 特殊: "flag.<name>" 没有 op/value, 默认 >= 1
                if parts and parts[0].startswith("flag."):
                    attr = parts[0]
                    op = ">="
                    value = 1
                else:
                    return ("fail", 0)
            else:
                attr, op, value_str = parts
                value = int(value_str)

            # 获取属性值
            actual = self._resolve_attr(attr, game_state)

            # 硬性检查
            passed = False
            if op == ">=":
                passed = actual >= value
            elif op == ">":
                passed = actual > value
            elif op == "<=":
                passed = actual <= value
            elif op == "<":
                passed = actual < value
            elif op == "==":
                passed = actual == value

            # 资源类属性 (cash/rice/...) 是硬性检查, 无 d20
            if attr in ("cash", "rice", "debt", "looms", "stamina"):
                return ("success" if passed else "fail", 0)

            # flag 类也是硬性检查
            if attr.startswith("flag."):
                return ("success" if passed else "fail", 0)

            if not passed:
                return ("fail", 0)

            # D&D 检定: d20 + 属性 vs DC=10+value*2
            # - value=2 (e.g. charisma >= 2): DC=14, 难
            # - value=3: DC=16, 较难
            # - value=4: DC=18, 很难
            d20 = roll_d20()
            total = d20 + actual
            dc = 10 + value * 2  # DC = 14 for value=2

            if total >= dc + 8:
                return ("great_success", d20)
            elif total >= dc:
                return ("success", d20)
            else:
                return ("fail", d20)
        except Exception as e:
            logger.warning(f"check failed: {e}")
            return ("fail", 0)

    def _resolve_attr(self, attr: str, game_state: dict) -> int:
        """解析属性值

        支持:
        - charisma / skill / luck / courage: 默认 2 (可被 flag 调整)
        - cash / rice / debt / looms / stamina: 从 game_state 取
        - flag.<name>: 1 if flag exists else 0
        """
        if attr.startswith("flag."):
            flag_name = attr[5:]
            flags = game_state.get("scripted_flags") or []
            return 1 if flag_name in flags else 0

        if attr in ("cash", "rice", "debt", "looms", "stamina"):
            return game_state.get(attr, 0) or 0

        # 抽象属性 (charisma / skill / luck / courage): 默认 2
        # 可被 specific flag 调整
        attr_mod_flags = {
            "charisma": ["zhou_favor", "met_big_merchant", "knew_color_master"],
            "skill": ["master_dyer", "learned_qixia", "knew_scale_trick"],
            "luck": ["has_debt", "sold_loom", "lone_warrior"],
            "courage": ["joined_resistance", "led_resistance", "lone_warrior"],
        }
        base = 2
        flags = game_state.get("scripted_flags") or []
        for f in attr_mod_flags.get(attr, []):
            if f in flags:
                base += 1
        return base

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
        """导出为前端格式（兼容现有 VoiceOption）

        🆕 v2.10.22: 加 intent_text / value_dimension, 跟主游戏对齐
        """
        return [
            {
                "voice_id": o.voice_id,
                "voice_name": o.voice_name,
                "intent_text": o.intent_text or o.description or o.voice_name,
                "description": o.description,
                "inner_voice": o.inner_voice,
                "value_dimension": o.value_dimension,
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