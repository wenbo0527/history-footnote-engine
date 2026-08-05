"""🆕 v2.10.24 Phase 12 — ScriptedStoryEngine 故事模式引擎 (重构版)

零 LLM 调用:
- 玩家输入 → 匹配当前 node 的 voice_options
- D&D 风格: flag 组合 + 触发条件 + effects
- 输出: narrative + voice_options + 状态变化

API 跟现有 /api/input 完全兼容 (前端零改动):
- 接收: {session_id, input}
- 返回: {narrative, voice_options, scripted_node_id, ...}

🆕 v2.10.24 重构:
- 拆分常量 → constants.py
- 拆分检定逻辑 → check_service.py
- 拆分效果应用 → effects.py
- 拆分跨章回响 → chapter_echo.py
- 拆分章节加载 → chapter_loader.py
- engine.py 瘦身: 520 行 → ~280 行
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

from history_footnote.story_mode.check_service import CheckService
from history_footnote.story_mode.chapter_echo import ChapterEchoService
from history_footnote.story_mode.chapter_loader import get_chapter
from history_footnote.story_mode.constants import (
    CHECK_RESULT_FAIL,
    CHECK_RESULT_SUCCESS,
    DEFAULT_CITY,
    SCRIPTED_STATE_KEYS,
)
from history_footnote.story_mode.effects import EffectsService
from history_footnote.story_mode.narrative_renderer import NarrativeRenderer
from history_footnote.story_mode.node_filter import NodeFilter
from history_footnote.story_mode.rich import (
    EnvironmentContext,
    maybe_trigger_encounter,
    perform_check,
    random_env_phrase,
)
from history_footnote.story_mode.types import (
    ScriptedChapter,
    ScriptedNode,
    ScriptedVoiceOption,
)

_LOG = logging.getLogger("history_footnote.story_mode.engine")


# 🆕 v2.10.32: 中文关键词提取 (用于自然语言输入 → voice_option 匹配)
_STOPWORDS = set("我你他她它吗呢啊吧了着的也是就不很都和与及或")


def _extract_keywords(text: str) -> list[str]:
    """从中文文本提取关键词

    简单实现: 按字符切分 (去除停用词), 也保留常见 2 字词组
    """
    keywords = []
    # 1. 单字关键词 (去除停用词)
    for ch in text:
        if '\u4e00' <= ch <= '\u9fff' and ch not in _STOPWORDS:
            keywords.append(ch)
    # 2. 2 字词组
    for i in range(len(text) - 1):
        if '\u4e00' <= text[i] <= '\u9fff' and '\u4e00' <= text[i + 1] <= '\u9fff':
            word = text[i:i + 2]
            if not any(c in _STOPWORDS for c in word):
                keywords.append(word)
    # 3. 3 字词组 (如 "借银子", "卖织机")
    for i in range(len(text) - 2):
        if all('\u4e00' <= text[i + j] <= '\u9fff' for j in range(3)):
            word = text[i:i + 3]
            if not any(c in _STOPWORDS for c in word):
                keywords.append(word)
    return keywords


class ScriptedStoryEngine:
    """故事模式引擎 (0 LLM)"""

    def __init__(
        self,
        chapter: Optional[ScriptedChapter] = None,
        check_service: Optional[CheckService] = None,
        effects_service: Optional[EffectsService] = None,
        echo_service: Optional[ChapterEchoService] = None,
        narrative_renderer: Optional[NarrativeRenderer] = None,
        rng: Optional[random.Random] = None,
    ):
        self.chapter = chapter or get_chapter(1)
        self._chapter_id = self.chapter.chapter_id if self.chapter else 1
        # 🆕 v2.10.24: 注入 services (依赖反转)
        self._checks = check_service or CheckService(rng=rng)
        self._effects = effects_service or EffectsService()
        self._echo = echo_service or ChapterEchoService()
        # 🆕 v2.10.25: 多声部叙事渲染
        self._renderer = narrative_renderer or NarrativeRenderer()

    def set_chapter_by_id(self, chapter_id: int) -> None:
        """🆕 v2.10.18: 切换章节"""
        self.chapter = get_chapter(chapter_id)
        self._chapter_id = self.chapter.chapter_id

    # ============================================================
    # 状态操作（直接读写 game state dict）
    # ============================================================

    @staticmethod
    def ensure_state(game_state: dict) -> dict:
        """确保 game_state 有故事模式字段 (只补缺失的 key, 不覆盖已有值)"""
        for key, default in SCRIPTED_STATE_KEYS.items():
            if key not in game_state:
                game_state[key] = default
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
        - no_match: bool (🆕 v2.10.33: 自由输入模糊匹配失败的标记)
        - suggested_options: list[dict] (🆕 v2.10.33: 建议玩家重选)
        - match_attempted: str (🆕 v2.10.33: 玩家原始输入, 便于前端 toast)
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
                # 🆕 v2.10.33 P0-1: 模糊匹配失败不再静默 — 返回当前节点 + no_match 信号
                return self._no_match_response(game_state, voice_id, node)

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
            # 🆕 v2.10.33 P0-1: 成功路径也明确 no_match=False（前端无需另判）
            "no_match": False,
            "match_attempted": voice_id,
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
        - 🆕 v2.10.30: NodeFilter 检查 required_city / required_flags / forbidden_flags
        - 🆕 v2.10.31: AutoNextNode — 无选项时自动跳到 auto_next_node_id
        """
        node_id = game_state.get("scripted_node_id") or self.chapter.start_node_id
        node = self.chapter.nodes.get(node_id)
        if node is None:
            return "【剧本损坏：找不到节点】", []

        # 🆕 v2.10.31: AutoNextNode — 空 voice_options + auto_next_node_id 自动跳转
        # 防循环: 最多跳跃 50 次
        visited_chain: list[str] = []
        while (
            not node.voice_options
            and node.auto_next_node_id
            and len(visited_chain) < 50
        ):
            next_id = node.auto_next_node_id
            if next_id in visited_chain:
                _LOG.warning(f"AutoNextNode cycle detected: {' → '.join(visited_chain)} → {next_id}")
                break
            visited_chain.append(node_id)
            node_id = next_id
            node = self.chapter.nodes.get(node_id)
            if node is None:
                return "【剧本损坏：auto_next 目标节点不存在】", []
            game_state["scripted_node_id"] = node_id

        # 🆕 v2.10.30: 检查节点可见性 (required_city / required_flags / forbidden_flags)
        if not NodeFilter.is_accessible(node, game_state):
            reasons = NodeFilter.get_unmet_requirements(node, game_state)
            warning = f"【节点 {node_id} 暂不可访问】\n原因: {', '.join(reasons)}\n请先满足前置条件。"
            _LOG.warning(f"node {node_id} inaccessible: {reasons}")
            # 返回警告 narrative + 空 options
            return warning, []

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

        # 🆕 v2.10.25: 委托给 NarrativeRenderer (优先 narrative_sections, 兜底 narrative)
        narrative = self._renderer.render(
            node,
            game_state,
            env_label=env_label,
            env_phrase=env_phrase,
        )

        # 🆕 v2.10.24: 委托给 ChapterEchoService
        narrative = self._echo.apply(
            narrative,
            game_state,
            self._chapter_id,
            node_id,
        )

        # 🆕 随机事件触发 (D&D 检定)
        round_num = game_state.get("round_number", 1)
        encounters = getattr(self.chapter, "random_encounters", []) or []
        triggered = maybe_trigger_encounter(encounters, game_state, round_num)
        if triggered:
            encounter_text, encounter_effects = self._resolve_encounter(triggered, game_state)
            narrative += f"\n\n🔀 【随机事件：{triggered.name}】\n{encounter_text}"

        return narrative, node.voice_options

    def _apply_chapter_echo(self, narrative: str, game_state: dict, node_id: str) -> str:
        """🆕 v2.10.24: 已委托给 ChapterEchoService, 保留方法名兼容旧调用"""
        return self._echo.apply(narrative, game_state, self._chapter_id, node_id)

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
        """🆕 v2.10.24: 委托给 CheckService"""
        return self._checks.do_check(check_expr, game_state)

    def _resolve_attr(self, attr: str, game_state: dict) -> int:
        """🆕 v2.10.24: 委托给 CheckService"""
        return self._checks.resolve_attr(attr, game_state)

    def _apply_effects(self, game_state: dict, effects: dict[str, Any]) -> None:
        """🆕 v2.10.24: 委托给 EffectsService, 但保留 father_health_delta 特殊逻辑"""
        # 抽出特殊效应
        special = {}
        if "father_health_delta" in effects:
            special["father_health_delta"] = effects.pop("father_health_delta")

        # 标准效应
        self._effects.apply(game_state, effects)

        # father_health 特殊处理 (clamp 0-100)
        if "father_health_delta" in special:
            v = special["father_health_delta"]
            if "father_health" not in game_state:
                game_state["father_health"] = 50
            game_state["father_health"] = max(0, min(100, game_state["father_health"] + v))

    def _fuzzy_match(self, voice_id: str, options: list[ScriptedVoiceOption]) -> Optional[ScriptedVoiceOption]:
        """模糊匹配（兼容前端输入差异 + 🆕 v2.10.32 中文关键词匹配）

        匹配策略 (按优先级):
        1. voice_id 精确匹配 (含大小写不敏感)
        2. voice_id 子串匹配 (e.g. "borrow_money" 包含 "borrow")
        3. 🆕 中文关键词匹配 — 玩家自由输入 → 匹配 voice_name / inner_voice / description / emotion
           例: 输入"借钱" → 匹配 voice_name="💰 向牙行借银子"
        4. 全失败 → 返回 None
        """
        vid = voice_id.lower().strip()

        # 1. 精确匹配
        for o in options:
            if o.voice_id.lower() == vid or voice_id == o.voice_id:
                return o

        # 2. 子串匹配
        for o in options:
            if vid in o.voice_id.lower() or o.voice_id.lower() in vid:
                return o

        # 3. 🆕 中文关键词匹配 (玩家输入自然语言)
        #    提取玩家输入中的关键词, 与 voice_name / inner_voice / description / emotion 比较
        if any('\u4e00' <= ch <= '\u9fff' for ch in vid):
            # 是中文输入, 才做关键词匹配
            keywords = set(_extract_keywords(vid))
            best_match: Optional[ScriptedVoiceOption] = None
            best_score = 0
            for o in options:
                text_blob = ' '.join(filter(None, [
                    o.voice_name or '',
                    o.inner_voice or '',
                    getattr(o, 'description', '') or '',
                    getattr(o, 'emotion', '') or '',
                ]))
                opt_keywords = set(_extract_keywords(text_blob))
                # 计算交集
                common = keywords & opt_keywords
                # 相似度: 交集 / min(玩家输入关键词数, 选项关键词数)
                #   - 短输入"借" vs 长选项: min(2, 30) = 2 → 1/2 = 0.5 ✓
                #   - 长输入"借钱买米" vs 选项: min(7, 5) = 5 → 1/5 = 0.2 ✓
                #   - 任意交集 (至少 1) 即视为匹配
                denom = max(min(len(keywords), len(opt_keywords)), 1)
                score = len(common) / denom
                if score > best_score and score >= 0.2 and len(common) >= 1:
                    best_score = score
                    best_match = o
            if best_match:
                _LOG.info(f"keyword match: '{voice_id}' → '{best_match.voice_id}' (score={best_score:.2f})")
                return best_match

        return None

    def _error(self, game_state: dict, msg: str) -> tuple[str, list[ScriptedVoiceOption], dict]:
        _LOG.warning(msg)
        return f"【剧本错误：{msg}】", [], {"error": msg}

    def _no_match_response(
        self,
        game_state: dict,
        voice_id: str,
        node: "ScriptedNode",
    ) -> tuple[str, list[ScriptedVoiceOption], dict]:
        """🆕 v2.10.33 P0-1: 玩家自由输入未匹配到任何 voice_option

        旧行为: 返回空 options + 不报错, 玩家看到"按了没反应"。
        新行为:
        1. 不改 state（节点不变, 玩家不前进）
        2. 返回原节点的 narrative（玩家看到上下文不丢失）
        3. 返回原节点的 voice_options（让玩家可以重选）
        4. info.no_match = True + match_attempted + suggestions
        """
        _LOG.info(
            f"[v2.10.33 no_match] voice_id='{voice_id}' not matched in node '{node.node_id}' "
            f"({len(node.voice_options)} options available)"
        )
        # 重新渲染当前节点（不动 state）
        narr, options = self._get_current_view(game_state)

        # 在 narrative 顶部插入"未识别"提示
        hint = (
            f"【未识别】DM 没有听懂「{voice_id[:30]}」——"
            f"请从下方选项中选择，或用更简单的词重述。"
        )
        narr = hint + "\n\n" + narr

        info = {
            "no_match": True,
            "match_attempted": voice_id,
            "chapter_complete": False,
            "new_node_id": node.node_id,
            "effects_applied": {},
            "flag_added": [],
            "suggested_options": [
                {
                    "voice_id": o.voice_id,
                    "voice_name": o.voice_name,
                    "intent_text": o.intent_text or o.description or o.voice_name,
                }
                for o in options
            ],
        }
        return narr, options, info

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