"""🆕 v2.10.25 — NarrativeRenderer (多声部叙事渲染)

负责把 ScriptedNode.narrative_sections 渲染成 narrative 字符串

格式约定:
- 旁白 (narrator == "旁白"): 直接文本
- 内心独白 (italic=True): 「...」 + 斜体前缀
- NPC 对话 (其他 narrator): 【NPC名】 + 文本
- Emotion: 表情 (e.g. "叹息" "微笑")
- Sound: 拟声 (e.g. "咚" "咳嗽")
- Action: 动作 (e.g. "攥紧借据")

输出示例:
    旁白: 你站在门前。
    【张氏】（忧）: 「相公...」
    张氏（攥紧借据）: 「债主明天就来。」
    内心独白: 「我该怎么办？」
    💢 咚 — 敲门声

支持模板变量 {var} (通过 TemplateEngine)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from history_footnote.story_mode.rich import (
    NarrativeSection,
    TemplateEngine,
)

if TYPE_CHECKING:
    from history_footnote.story_mode.types import ScriptedNode

logger = logging.getLogger(__name__)


class NarrativeRenderer:
    """渲染 ScriptedNode.narrative_sections → narrative 字符串"""

    def __init__(self, template_engine: TemplateEngine | None = None):
        self._tpl = template_engine or TemplateEngine()

    def render(
        self,
        node: "ScriptedNode",
        game_state: dict,
        env_label: str = "",
        env_phrase: str = "",
    ) -> str:
        """渲染一个节点为完整 narrative 字符串

        Args:
            node: ScriptedNode
            game_state: 当前游戏状态 (用于 TemplateEngine 变量)
            env_label: 环境标签 (e.g. "【春季·晴·盛泽镇·辰时】")
            env_phrase: 环境描写短语

        Returns:
            完整 narrative (含环境 + 多声部)
        """
        self._tpl.state = game_state

        # 1. 优先用 narrative_sections (多声部)
        if node.narrative_sections:
            body = self._render_sections(node.narrative_sections)
        elif node.narrative:
            body = self._tpl.render(node.narrative)
        else:
            body = ""

        # 2. 拼接环境 + on_enter_text + body
        parts = []
        if env_label:
            parts.append(env_label)
        if env_phrase:
            parts.append(env_phrase)
        if node.on_enter_text:
            parts.append(self._tpl.render(node.on_enter_text))
        if body:
            parts.append(body)

        return "\n\n".join(p for p in parts if p)

    def _render_sections(self, sections: list[NarrativeSection]) -> str:
        """渲染多声部段落列表

        规则:
        - 旁白: 直接输出
        - 其他 narrator: 【NPC】前缀
        - italic: 「...」
        - emotion: (emotion) 后缀
        - sound: 单独一行 💢 音效
        - action: (action) 前缀
        """
        lines = []
        for s in sections:
            # 跳过空文本
            if not s.text and not s.sound and not s.action:
                continue

            # 音效单独一行
            if s.sound:
                lines.append(f"💢 {s.sound}")

            # 动作单独一行
            if s.action:
                lines.append(f"*{s.action}*")

            # 主文本
            if s.text:
                text = self._tpl.render(s.text)
                if s.italic or s.narrator in ("内心", "内心独白", "inner_voice"):
                    # 内心独白: 「...」
                    lines.append(f"「{text}」")
                elif s.narrator in ("旁白", "narrator", ""):
                    lines.append(text)
                else:
                    # NPC 对话
                    suffix = f"（{s.emotion}）" if s.emotion else ""
                    lines.append(f"【{s.narrator}】{suffix}：{text}")

        # 清理过多空行
        result = "\n".join(lines)
        return result.strip()


def render_simple(
    sections: list[NarrativeSection],
    game_state: dict | None = None,
) -> str:
    """便捷函数: 不创建 engine 实例, 快速渲染"""
    return NarrativeRenderer()._render_sections(sections)