"""🆕 v1.7.42 State Ref Helpers（架构拆分）

v1.7.41 抽了 set_state_ref_slot 通用方法。
本 commit 进一步抽到独立模块 + 完整化 set_action_context_for_dm。

设计：
- DMStateRefHelpers 类：所有 set_*_hint 方法统一管理
- game_loop.py 删 5 个 set_*_hint 方法
- 引入 from history_footnote.state_ref_helpers import DMStateRefHelpers
"""
from __future__ import annotations

import json
from typing import Any, Optional


class DMStateRefHelpers:
    """DM LLM state_ref 注入 helpers

    LLM 通过 _state_ref_slot_ref[0] 读取 state_ref 字典。
    所有 hint 注入都通过这里。

    5 个 hint：
    - calendar_events（历法大事件）
    - wiki_hint（Wiki 检索片段）
    - drama_hint（DramaManager 干预）
    - action_context（PlayerAction + ActionResult）
    - random_events（随机事件）
    """

    def __init__(self, dm_llm):
        self.dm_llm = dm_llm

    def _get_state_ref(self) -> Optional[dict]:
        if not hasattr(self.dm_llm, "_state_ref_slot_ref"):
            return None
        return self.dm_llm._state_ref_slot_ref[0]

    def set_slot(self, key: str, value: Any) -> None:
        """通用 slot 注入"""
        if not value:
            return
        state_ref = self._get_state_ref()
        if state_ref is not None:
            state_ref[key] = value

    def set_calendar_events(self, calendar_text: str) -> None:
        """历法大事件"""
        self.set_slot("calendar_events", calendar_text)

    def set_wiki_hint(self, fragments: list) -> None:
        """Wiki 检索片段（最多 3 段，截断 800 字）"""
        if not fragments:
            return
        content_blocks = []
        for f in fragments[:3]:
            c = f.get("content", "")
            if len(c) > 800:
                c = c[:800] + "..."
            content_blocks.append(f"【{f.get('title', '')}】\n{c}")
        self.set_slot("wiki_hint", "\n\n".join(content_blocks))

    def set_drama_hint(self, hint: str) -> None:
        """DramaManager 干预 hint"""
        self.set_slot("drama_hint", hint)

    def set_action_context(self, player_action, action_result,
                           failed: bool = False) -> None:
        """PlayerAction + ActionResult 注入

        LLM 用这些 context 生成 narrative（不再需要输出 events 块）
        """
        state_ref = self._get_state_ref()
        if state_ref is None:
            return
        state_ref["action_context"] = {
            "raw_text": player_action.raw_text,
            "verb": player_action.verb,
            "object": player_action.object,
            "amount": player_action.amount,
            "target": player_action.target,
            "location": player_action.location,
            "hint": player_action.hint,
            "state_changes": action_result.state_changes if action_result else {},
            "events_triggered": [e.get("id", "") for e in (action_result.events if action_result else [])],
            "narrative_hints": action_result.narrative_hints if action_result else [],
            "failed": failed,
            "error_msg": action_result.error_msg if action_result else "",
            "instruction": (
                "游戏引擎已处理以下结构化数据。你只需要把以下状态变化包装成 narrative："
                + "\n".join([f"  - {e.get('id', '')}: {e.get('note', '')}" for e in (action_result.events if action_result else [])])
                + "\n不需要输出 <events> 块。"
            ),
        }

    def set_random_events(self, triggered: list) -> None:
        """随机事件结果"""
        if not triggered:
            return
        # 序列化为可读文本
        text = "\n".join([
            f"- {ev.get('outcome', {}).get('description', '')}" for ev in triggered
        ])
        self.set_slot("random_events", text)

    def get_all_slots(self) -> dict:
        """获取当前所有 slot（用于调试）"""
        state_ref = self._get_state_ref()
        if state_ref is None:
            return {}
        return dict(state_ref)

    def build_unified_context(self) -> str:
        """🆕 v1.7.43 合并所有 hint 为 1 个 unified context

        替代 4 个独立 hint 字段（calendar_events / wiki_hint / drama_hint / action_context）。
        LLM 一次看到所有 context，无需分别处理。

        Returns:
            unified context 字符串
        """
        state_ref = self._get_state_ref() or {}
        parts = []
        # 1. 玩家动作 context（最重要）
        action_ctx = state_ref.get("action_context")
        if action_ctx:
            parts.append(f"【玩家动作】\n{action_ctx.get('instruction', '')}")
        # 2. Wiki 检索片段
        wiki = state_ref.get("wiki_hint")
        if wiki:
            parts.append(f"【历史参考】\n{wiki}")
        # 3. 戏剧干预
        drama = state_ref.get("drama_hint")
        if drama:
            parts.append(f"【节奏干预】\n{drama}")
        # 4. 历法大事件
        cal = state_ref.get("calendar_events")
        if cal:
            parts.append(f"【时代背景】\n{cal}")
        return "\n\n".join(parts)

    def clear_all_slots(self) -> None:
        """清空所有 slot（测试用）"""
        state_ref = self._get_state_ref()
        if state_ref is not None:
            state_ref.clear()


# ============= 烟雾测试 =============

if __name__ == "__main__":
    # 模拟 LLM
    class MockLLM:
        def __init__(self):
            self._state_ref_slot_ref = [{}]  # 必须 list 包 dict（DM Agent 内部用 list）

    llm = MockLLM()
    helpers = DMStateRefHelpers(llm)

    print("=== State Ref Helpers 烟雾测试 ===\n")
    # 1. set_slot
    helpers.set_slot("test_key", "test_value")
    print(f"  set_slot('test_key') → state_ref: {helpers.get_all_slots()}")
    assert helpers.get_all_slots().get("test_key") == "test_value"

    # 2. set_calendar_events
    helpers.set_calendar_events("- evt.guoben_dispute\n- evt.little_ice_age")
    print(f"  set_calendar_events: {len(helpers.get_all_slots().get('calendar_events', ''))} 字符")

    # 3. set_wiki_hint
    helpers.set_wiki_hint([
        {"title": "苏州", "content": "阊门码头..."},
        {"title": "船", "content": "船上时光..."},
    ])
    print(f"  set_wiki_hint: {len(helpers.get_all_slots().get('wiki_hint', ''))} 字符")

    # 4. set_drama_hint
    helpers.set_drama_hint("玩家太紧张，给安静时光")
    print(f"  set_drama_hint: '{helpers.get_all_slots().get('drama_hint', '')[:20]}...'")

    # 5. set_action_context
    from history_footnote.action_resolver import PlayerAction, ActionResult
    pa = PlayerAction(raw_text="我去苏州", verb="TRAVEL", target="suzhou", location="shengze",
                      hint="（动作：前往某地或回家，目标：suzhou，地点：shengze）")
    ar = ActionResult(state_changes={"current_city": "suzhou"},
                       events=[{"id": "city.arrive.suzhou", "note": "到达 suzhou"}],
                       success=True)
    helpers.set_action_context(pa, ar)
    ac = helpers.get_all_slots().get("action_context", {})
    print(f"  set_action_context: verb={ac.get('verb')}, events={ac.get('events_triggered')}")

    # 6. set_random_events
    helpers.set_random_events([
        {"outcome": {"description": "你在镇上看到有织工聚众议论加税"}},
        {"outcome": {"description": "邻居张婶告诉你最近风声紧"}},
    ])
    print(f"  set_random_events: '{helpers.get_all_slots().get('random_events', '')[:30]}...'")

    # 7. 全部 slots
    print(f"\n所有 slot:")
    for k, v in helpers.get_all_slots().items():
        v_preview = str(v)[:40]
        print(f"  {k}: {v_preview}{'...' if len(str(v)) > 40 else ''}")

    # 8. clear
    helpers.clear_all_slots()
    print(f"\n清空后: {helpers.get_all_slots()}")
    assert helpers.get_all_slots() == {}
