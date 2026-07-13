"""🆕 v2.10.3 SKILL-3 线索投放（原 dm_skills.py 第 523-588 行）

在恰当时机释放信息：push / guide / reveal / pressure 4 种类型。
"""
from __future__ import annotations

from history_footnote.dm_skills.types import LeadPlan, PacingDecision, SceneAssessment


LEAD_TYPES = {
    "push": "推动型：玩家无所事事时",
    "guide": "引导型：玩家跑偏时",
    "reveal": "揭示型：玩家主动探索时",
    "pressure": "压力型：需制造紧迫感时",
}


def skill_3_plan_lead(
    assessment: SceneAssessment,
    pacing: PacingDecision,
    era_config: dict,
    state: dict,
    player_input: str,
) -> LeadPlan | None:
    """SKILL-3 线索投放：在恰当时机释放信息

    4 种线索类型：
    - push（推动型）：玩家无所事事 → NPC闲话/环境变化
    - guide（引导型）：玩家跑偏 → NPC主动提及/巧合
    - reveal（揭示型）：玩家主动探索 → 搜索发现/NPC深谈
    - pressure（压力型）：需制造紧迫感 → 传闻/倒计时
    """
    # 玩家停滞 → 推动型
    if pacing.correction_type == "new_event" or assessment.deviation == "stuck":
        return LeadPlan(
            lead_type="push",
            lead_content="镇上出了件大事 / 邻居来说消息",
            delivery_method="npc_chat",
            target_route="",
        )

    # 玩家跑偏/困惑 → 引导型
    if assessment.deviation == "serious" or assessment.emotion == "confused":
        return LeadPlan(
            lead_type="guide",
            lead_content="王婶说某件事 / 偶遇某人",
            delivery_method="npc_chat",
            target_route="",
        )

    # 锐切/重大抉择 → 压力型
    if pacing.time_mode == "sharp_cut":
        return LeadPlan(
            lead_type="pressure",
            lead_content="税吏三日后到镇 / 矿监来了",
            delivery_method="gossip",
            target_route="",
        )

    # 玩家主动探索 → 揭示型
    if pacing.time_mode == "slow_time" and assessment.engagement == "high":
        return LeadPlan(
            lead_type="reveal",
            lead_content="你发现/听到的细节",
            delivery_method="environment",
            target_route=assessment.route_tendency,
        )

    return None