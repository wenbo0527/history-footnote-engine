"""🆕 v1.7.30 dm_agent/mock_helpers.py

DMAgent 的 Mock 模式辅助 Mixin：
- _make_view_state_dict（私有 view 序列化，9 字段）
- _get_forced_events_for_mock / _pacing / _triggers / _insights_for_mock
  （mock 数据源，调 RuleEngine.get_* 直接拿数据）

历史背景：原本 inline 在 agent.py 1370-1434 行（4 个函数 + 1 个 view 序列化）

为什么拆出：
- mixin 让 DMAgent 类瘦身（25 个方法中 5 个下沉到独立文件）
- 测试可独立验证这 5 个 mock 助手的输出（已通过 test_dm_agent_golden）
"""
from __future__ import annotations


class MockHelpersMixin:
    """DM Agent 的 Mock 工具集（依赖 self.state / self.rule_engine）"""

    def _make_view_state_dict(self) -> dict:
        return {
            "round_number": self.state.round_number,
            "current_date": self.state.current_date,
            "variables": dict(self.state.variables),
            "triggered_events": list(self.state.triggered_events),
            "unlocked_insights": list(self.state.unlocked_insights),
            "npc_levels": dict(self.state.npc_levels),
            "value_shifts": dict(self.state.value_shifts),
            "player_idle_rounds": self.state.player_idle_rounds,
            "selected_identity": self.state.selected_identity,
            "player_gender": self.state.player_gender,
        }

    def _get_forced_events_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        forced = self.rule_engine.check_forced_events(view)
        return [
            {
                "event_id": fe.event_id,
                "event_name": fe.event_name,
                "description": fe.description,
                "narrative_mandatory": fe.narrative_mandatory,
            }
            for fe in forced
        ]

    def _get_pacing_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        pacing = self.rule_engine.check_pacing(view)
        return [
            {
                "id": pd.id,
                "direction": pd.direction,
                "hint": pd.hint,
            }
            for pd in pacing
        ]

    def _get_triggers_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        triggers = self.rule_engine.check_triggers(view)
        return [
            {
                "id": tr.id,
                "narrative_hint": tr.narrative_hint,
                "effect": tr.effect,
            }
            for tr in triggers
        ]

    def _get_insights_for_mock(self) -> list[dict]:
        view = self.rule_engine.make_view(self.state)
        insights = self.rule_engine.check_insights(view, player_input=self.state._last_player_input or "")
        return [
            {
                "id": ic.id,
                "topic": ic.topic,
                "confirm_needed": ic.confirm_needed,
                "narrative_hint": ic.narrative_hint,
            }
            for ic in insights
        ]
