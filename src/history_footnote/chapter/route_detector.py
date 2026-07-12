"""v2.10.1 W85 涌现式章节 · RouteDetector

设计目标：
- Phase 1：纯规则版（关键词 + 价值偏移阈值）
- Phase 2：加 LLM 意图分类（识别设计者未预设的即兴路线）
- Phase 3：DM 参与判断（双判断架构）

Phase 1 判断逻辑（优先级从高到低）：
1. 历史铁轨触达 → 强制 convergence（confidence=1.0）
2. 关键词匹配 → 立即触发对应模板（confidence=0.85）
3. 价值偏移 > 阈值 → 触发 rising_conflict（confidence=0.7）
4. 都未触发 → route_change=False（保持当前路线）

Phase 2 升级（仅在 Phase 1 未触发时调）：
- LLM 意图分类：识别设计者未预设的即兴路线（"投奔海瑞"）
- 调用条件：llm_callable 不为 None 且前面未触发
- 输出：JSON 5 字段（core_intent / changed_conflict / suggested_template / confidence / reason）
- 异常 fallback：changed_conflict=False（不触发）

返回值 dict 给 coordinator，由 coordinator.apply_route_change 写入 state。
本模块不改 state，纯函数易测试。

依据 spec：docs/design/v2.10.1-W85-涌现式章节设计.md §2.2 + §3.1
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from history_footnote.chapter.types import ChapterBlueprint

_LOG = logging.getLogger("history_footnote.chapter.route_detector")


# 关键词路由表（可被 era_config 覆盖）
DEFAULT_ROUTE_KEYWORDS: dict[str, list[str]] = {
    "rising_conflict": [
        # 中文关键词
        "抗税", "不交", "逃税", "投奔", "逃跑", "告官", "反抗",
        "海瑞", "衙门", "闹事", "罢工", "起义",
        # 英文（如适用）
        "rebel", "flee", "protest",
    ],
    "crisis": [
        "倭寇", "灾难", "火灾", "洪水", "地震", "海瑞去世",
        "银税", "抄家", "破产", "死亡",
        "disaster", "death",
    ],
    "convergence": [
        "万历", "皇帝", "朝廷", "诏书", "圣旨",
    ],
}

# 价值偏移阈值（绝对值超过即触发）
VALUE_SHIFT_THRESHOLD = 0.7

# 触发历史铁轨的关键词（决定强制 convergence）
HISTORICAL_ANCHOR_KEYWORDS = [
    "倭寇来袭", "万历驾崩", "海瑞去世", "银税改革", "一条鞭法",
]

# 5 类模板 → DM 创作指令的映射
DM_INSTRUCTION_BASE: dict[str, str] = {
    "opening": "铺陈日常，暗示即将到来的变故",
    "rising_conflict": "冲突升级，逼迫玩家表态",
    "crisis": "不可逆事件发生，玩家被迫重新定位",
    "convergence": "历史铁轨事件落地，根据玩家路线调整叙事入口",
    "resolution": "收束所有线索，对照开头的日常",
}


class RouteDetector:
    """v2.10.1 W85 路线检测器（Phase 1 纯规则版 + Phase 2 LLM 意图）

    用法（Phase 1）：
        detector = RouteDetector()
        result = detector.detect(...)

    用法（Phase 2）：
        detector = RouteDetector(llm_callable=my_llm_fn)
        # Phase 1 未触发时,会自动调 my_llm_fn 分类玩家意图

    llm_callable 形态：
    - callable 函数: detector.llm(prompt: str, max_tokens: int) -> str (JSON 字符串)
    - callable 函数: detector.llm(prompt: str) -> dict (直接返回 dict)
    - None: Phase 2 跳过（仅 Phase 1 关键词 + 价值偏移）
    """

    def __init__(
        self,
        route_keywords: Optional[dict[str, list[str]]] = None,
        llm_callable: Optional[callable] = None,
    ):
        self.route_keywords = route_keywords or DEFAULT_ROUTE_KEYWORDS
        # 🆕 v2.10.1 W85 Phase 2: LLM 意图分类
        self.llm = llm_callable

    def detect(
        self,
        player_input: str,
        value_shifts: dict[str, float],
        current_chapter: ChapterBlueprint,
        historical_anchors_triggered: list[str] | None = None,
    ) -> dict:
        """检测玩家行为是否构成新路线

        Args:
            player_input: 玩家本回合输入原文
            value_shifts: 当前 value_shifts dict（如 {"trust": -0.8, ...}）
            current_chapter: 当前章节蓝图（ChapterBlueprint 或 dict）
            historical_anchors_triggered: 本回合触发的历史铁轨列表
                Phase 1 默认 None（保留接口给 Phase 2）

        Returns:
            {
                "route_change": bool,
                "suggested_template": str,
                "trigger": str | None,
                "confidence": float,
                "dm_instruction": str,
            }
        """
        # 兼容 current_chapter 既可以是 dataclass 也可以是 dict
        if isinstance(current_chapter, dict):
            current_position = current_chapter.get("narrative_position", "opening")
            current_title = current_chapter.get("chapter_title", "")
        else:
            current_position = getattr(current_chapter, "narrative_position", "opening")
            current_title = getattr(current_chapter, "chapter_title", "")

        # 1. 优先级最高：历史铁轨触达 → 强制 convergence
        if historical_anchors_triggered:
            anchor = historical_anchors_triggered[0]
            return {
                "route_change": True,
                "suggested_template": "convergence",
                "trigger": f"historical_anchor:{anchor}",
                "confidence": 1.0,
                "dm_instruction": self._build_dm_instruction(
                    "convergence",
                    current_position,
                    current_title,
                    f"历史铁轨事件「{anchor}」已触发。"
                    f"无论玩家之前做了什么路线，都必须在此刻汇合。"
                    f"根据玩家之前的选择（可参考 value_state），调整叙事入口。",
                ),
            }

        # 2. 关键词匹配
        keyword_match = self._match_keywords(player_input or "")
        if keyword_match:
            template, kw = keyword_match
            return {
                "route_change": True,
                "suggested_template": template,
                "trigger": f"keyword:{kw}",
                "confidence": 0.85,
                "dm_instruction": self._build_dm_instruction(
                    template,
                    current_position,
                    current_title,
                    f"玩家行为触发关键词「{kw}」",
                ),
            }

        # 3. 价值偏移检测
        for dim, val in (value_shifts or {}).items():
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            if abs(v) >= VALUE_SHIFT_THRESHOLD:
                return {
                    "route_change": True,
                    "suggested_template": "rising_conflict",
                    "trigger": f"value_shift:{dim}={v:+.2f}",
                    "confidence": 0.7,
                    "dm_instruction": self._build_dm_instruction(
                        "rising_conflict",
                        current_position,
                        current_title,
                        f"玩家在「{dim}」维度上发生剧烈偏移（{v:+.2f}）",
                    ),
                }

        # 4. 🆕 v2.10.1 W85 Phase 2: LLM 意图分类（仅在前面 3 级都未触发时）
        if self.llm is not None and player_input:
            intent = self._classify_intent_with_llm(player_input, current_chapter)
            if intent.get("changed_conflict"):
                template = intent.get("suggested_template", "rising_conflict")
                # 安全检查：必须为 5 类之一,否则忽略
                if template in DM_INSTRUCTION_BASE:
                    return {
                        "route_change": True,
                        "suggested_template": template,
                        "trigger": f"llm_intent:{intent.get('core_intent', 'unknown')}",
                        "confidence": float(intent.get("confidence", 0.5)),
                        "dm_instruction": self._build_dm_instruction(
                            template,
                            current_position,
                            current_title,
                            f"LLM 意图分类: {intent.get('reason', '')}",
                        ),
                    }
                _LOG.warning(
                    "[W85-Phase 2] LLM 返回非法 template: %s, 忽略",
                    template,
                )

        # 5. 未触发
        return {
            "route_change": False,
            "suggested_template": current_position,
            "trigger": None,
            "confidence": 0.0,
            "dm_instruction": "",
        }

    def _match_keywords(self, text: str) -> Optional[tuple[str, str]]:
        """返回 (template, keyword) 或 None"""
        if not text:
            return None
        for template, keywords in self.route_keywords.items():
            for kw in keywords:
                if kw in text:
                    return (template, kw)
        return None

    def _build_dm_instruction(
        self, template: str, current_position: str, current_title: str, reason: str
    ) -> str:
        """根据模板生成 DM 创作指令"""
        base = DM_INSTRUCTION_BASE.get(template, "")
        title_part = f"\n当前章节：{current_title or '未命名'}。"
        position_part = f"\n当前 narrative_position：{current_position} → {template}。"
        return f"[{template}] {base}。\n触发原因：{reason}。{title_part}{position_part}"

    # ============= 🆕 v2.10.1 W85 Phase 2: LLM 意图分类 =============

    def _classify_intent_with_llm(self, player_input: str, current: ChapterBlueprint | dict) -> dict:
        """调 LLM 分类玩家意图

        spec §3.1: prompt 必须简短（< 500 tokens）,仅传必要字段
        仅传 3 个字段：
        1. 当前章节标题
        2. 当前 must_resolve 冲突
        3. 玩家本回合输入

        Returns:
            dict: 5 字段（core_intent / changed_conflict / suggested_template / confidence / reason）
                  异常时返回 {"changed_conflict": False}（不触发路线变更）
        """
        # 取章节标题和 must_resolve
        if isinstance(current, dict):
            chapter_title = current.get("chapter_title", "")
            must_resolve = current.get("must_resolve", [])
        else:
            chapter_title = getattr(current, "chapter_title", "")
            must_resolve = getattr(current, "must_resolve", [])

        must_resolve_str = ", ".join(must_resolve) if must_resolve else "(无显式冲突)"

        prompt = (
            "你是历史注脚的章节导演。分析玩家行为是否改变了当前章节的核心冲突。\n\n"
            f"当前章节：{chapter_title or '未命名'}\n"
            f"当前冲突：{must_resolve_str}\n\n"
            f"玩家行为：「{player_input}」\n\n"
            "回答 JSON（必须含以下 5 个字段）：\n"
            "{\n"
            '  "core_intent": "玩家核心意图（10 字内）",\n'
            '  "changed_conflict": true/false,\n'
            '  "suggested_template": "opening/rising_conflict/crisis/convergence/resolution",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "reason": "理由（30 字内）"\n'
            "}"
        )

        try:
            # 兼容 3 种 LLM 返回形态：
            # 1) 返回字符串(JSON)
            # 2) 返回 dict(已解析)
            # 3) 异常
            response = self.llm(prompt, max_tokens=200)
            if isinstance(response, str):
                # 尝试从可能的 markdown 代码块中提取 JSON
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    response = json_match.group(0)
                return json.loads(response)
            elif isinstance(response, dict):
                return response
            else:
                _LOG.warning("[W85-Phase 2] LLM 返回非 str/dict: %s", type(response))
                return {"changed_conflict": False}
        except json.JSONDecodeError as e:
            _LOG.warning("[W85-Phase 2] LLM 返回 JSON 解析失败: %s", e)
            return {"changed_conflict": False}
        except Exception as e:
            _LOG.warning("[W85-Phase 2] LLM 调用失败: %s", e)
            return {"changed_conflict": False}