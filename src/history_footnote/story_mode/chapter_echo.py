"""🆕 v2.10.24 — 跨章回响服务

负责根据 chapter_id + flags 注入 narrative 动态内容
"""
from __future__ import annotations

import logging
from typing import Set

from history_footnote.story_mode.constants import CHAPTER_INFO

logger = logging.getLogger(__name__)


class ChapterEchoService:
    """跨章回响服务 - 根据前章 flag 注入 narrative 动态内容"""

    def apply(
        self,
        narrative: str,
        game_state: dict,
        chapter_id: int,
        node_id: str,
    ) -> str:
        """注入跨章回响

        Args:
            narrative: 原 narrative
            game_state: 当前游戏状态
            chapter_id: 当前章节 (1/2/3)
            node_id: 当前节点 ID (只在 intro 节点生效)

        Returns:
            注入回响后的 narrative
        """
        flags = set(game_state.get("scripted_flags") or [])
        cash = game_state.get("cash") or 0
        debt = game_state.get("debt") or 0
        looms = game_state.get("looms") or 0

        if chapter_id == 2 and node_id == "ch2_intro_normal":
            echoes = self._ch2_intro_echoes(flags, cash, debt, looms)
        elif chapter_id == 3 and node_id == "ch3_intro_normal":
            echoes = self._ch3_intro_echoes(flags, cash, debt, looms)
        else:
            echoes = []

        if echoes:
            return narrative + "\n".join(echoes)
        return narrative

    def _ch2_intro_echoes(
        self, flags: Set[str], cash: int, debt: int, looms: int
    ) -> list[str]:
        """第二章开局回响 (基于第一章 flag)"""
        echoes = []
        if "prosperous" in flags or cash >= 5:
            echoes.append("\n\n🆕 第一章回响：你攒下了些银钱，家境尚可。")
        elif debt > 0:
            echoes.append(
                f"\n\n🆕 第一章回响：你仍欠着 {debt} 两银子，月息压得你喘不过气。"
            )
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
        return echoes

    def _ch3_intro_echoes(
        self, flags: Set[str], cash: int, debt: int, looms: int
    ) -> list[str]:
        """第三章开局回响 (基于第一章+第二章 flag)"""
        echoes = []
        if "ch2_prosperous" in flags or cash >= 10:
            echoes.append("\n\n🆕 第二章回响：你家境小康，三架织机仍转。")
        if "merchant_disgraced" in flags:
            echoes.append("\n🆕 第二章回响：你在苏州商誉受损，订单减少。")
        if "master_dyer" in flags or "knew_color_master" in flags:
            echoes.append("\n🆕 第二章回响：你织染技艺了得，可号召同行抗税。")
        if "father_will" in flags or "father_secret" in flags:
            echoes.append(
                "\n\n🆕 父亲遗愿：万历九年的丝绢案冤情，你手中尚有文书证据。"
            )
        if "zhang_helped" in flags:
            echoes.append("\n🆕 第二章回响：张叔仍可信赖，可联合抗税。")
        if "child_born" in flags:
            echoes.append("\n🆕 第二章回响：你有了孩子，家庭羁绊更深。")
        if "wife_dead" in flags:
            echoes.append("\n🆕 第二章回响：妻子已逝，你孤身一人，抗税决心更坚。")
        return echoes