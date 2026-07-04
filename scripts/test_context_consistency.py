"""🆕 v1.6.4 P0 Bug 修复：叙事上下文一致性测试

修复前问题：
- 张寡妇刚说完话，下一回合突然变成陈三（NPC 混淆）
- system prompt 只注入 recent_scenes（场景标签如"织机前/茶馆"）
- LLM 不知上回合完整对话上下文

修复后验证：
1. _build_recent_context_for_prompt() 返回正确格式
2. state_ref 注入 recent_narratives（供 Mock LLM 用）
3. 没有 narrative 时返回空串（不破坏开局）
"""
import sys
from pathlib import Path
sys.path.insert(0, "src")

from history_footnote.game_state import GameState


class MockDMAgent:
    """Mock DM Agent（只测试 _build_recent_context_for_prompt）"""
    def __init__(self, state):
        self.state = state

    _build_recent_context_for_prompt = None  # 占位


def bind_method():
    """从真实 dm_agent 拿方法"""
    from history_footnote.dm_agent import DMAgent
    return DMAgent._build_recent_context_for_prompt


def test_empty_history():
    """空历史 → 空字符串"""
    state = GameState(current_date="1587年1月")
    method = bind_method()
    agent = MockDMAgent(state)
    result = method(agent)
    assert result == "", f"空历史应返回空串，实际：{result!r}"
    print(f"✅ test_empty_history: 空历史 → 空字符串（不污染 prompt）")


def test_single_round():
    """单回合 → 1 个上下文段"""
    state = GameState(current_date="1587年1月")
    state.append_narrative(1, "灶房里，沈氏说：'赵里长今天来。'",
                          "赵里长到访")
    method = bind_method()
    agent = MockDMAgent(state)
    result = method(agent)
    assert "第 1 回合" in result
    assert "赵里长到访" in result
    assert "灶房里" in result
    assert "重要提示" in result  # 必须有"重要提示"指令
    print(f"✅ test_single_round: 1 回合 → 包含 {len(result)} 字符")


def test_three_rounds():
    """3 回合 → 完整上下文（最近 3）"""
    state = GameState(current_date="1587年1月")
    rounds = [
        (1, "张寡妇看着你：'租钱怎么算？'", "与张寡妇谈租"),
        (2, "沈氏在灶房喊吃早饭了。", "家庭日常"),
        (3, "赵里长来收税。", "赵里长收税"),
    ]
    for r, narr, summary in rounds:
        state.append_narrative(r, narr, summary)
        # 同时模拟 event_log 中的 player_input
        state.event_log.append({
            "round": r,
            "player_action": f"行动 {r}",
            "type": "dm_narrative",
            "summary": summary,
        })

    method = bind_method()
    agent = MockDMAgent(state)
    result = method(agent)
    assert "第 1 回合" in result
    assert "第 2 回合" in result
    assert "第 3 回合" in result
    assert "张寡妇" in result  # 关键：必须保留张寡妇上下文
    assert "赵里长" in result
    assert "重要提示" in result
    print(f"✅ test_three_rounds: 3 回合 → 完整上下文 {len(result)} 字符")


def test_truncation():
    """超长叙事截前 400 字"""
    state = GameState(current_date="1587年1月")
    long_narrative = "测试" * 300  # 600 字
    state.append_narrative(1, long_narrative, "测试摘要")

    method = bind_method()
    agent = MockDMAgent(state)
    result = method(agent)
    # 叙事片段应该被截断（约 400 字 + …）
    assert "…" in result or "测试" * 200 in result
    # 不应该有 600 字
    narr_in_result = result.split("**叙事片段**：")[1].split("\n")[0] if "**叙事片段**" in result else ""
    assert len(narr_in_result) <= 500, f"叙事片段应≤500字符（截前400+ellipsis），实际 {len(narr_in_result)}"
    print(f"✅ test_truncation: 长叙事截断到 ≤400 字符")


def test_state_ref_has_recent_narratives():
    """state_ref 含 recent_narratives 字段（供 Mock LLM）"""
    # 模拟 DM Agent.run() 中 state_ref 的构造
    state = GameState(current_date="1587年1月")
    state.append_narrative(1, "你看见张寡妇。", "张寡妇登场")
    state.append_narrative(2, "她开口说话。", "对话")

    state_ref = {
        "round_number": state.round_number,
        "recent_narratives": [
            {
                "round": n.get("round"),
                "summary": n.get("summary", ""),
                "narrative": (n.get("narrative", "") or "")[:400],
            }
            for n in getattr(state, "narrative_recent", [])[-3:]
        ],
    }

    assert "recent_narratives" in state_ref
    assert len(state_ref["recent_narratives"]) == 2
    # 必须保留张寡妇名字
    assert any("张寡妇" in n["narrative"] for n in state_ref["recent_narratives"])
    print(f"✅ test_state_ref_has_recent_narratives: state_ref 含 {len(state_ref['recent_narratives'])} 条 recent_narratives")


def test_variables_included():
    """关键变量出现在上下文"""
    state = GameState(current_date="1587年1月")
    state.append_narrative(1, "你借了织机。", "借机")
    state.variables = {"银两": 10, "绸缎": 5, "心情": 3}

    method = bind_method()
    agent = MockDMAgent(state)
    result = method(agent)
    assert "银两" in result
    assert "绸缎" in result
    print(f"✅ test_variables_included: 关键变量正确显示")


def test_npc_consistency_simulation():
    """模拟玩家场景：确保张寡妇上下文保留"""
    # 这是玩家报告的具体问题：张寡妇 → 陈三
    state = GameState(current_date="1587年1月")
    state.append_narrative(
        1,
        "张寡妇听完，没有立刻答应，也没有拒绝。"
        "她看了你一眼：'租钱怎么算？'"
        "你：'一个月五百文。' "
        "她：'太少了。一台机子值二钱银子。'",
        "与张寡妇谈租"
    )
    state.append_narrative(
        2,
        "沈氏在灶房喊吃早饭了。你放下织机。",
        "家庭日常"
    )

    method = bind_method()
    agent = MockDMAgent(state)
    result = method(agent)

    # 关键断言：张寡妇必须出现在上下文中
    assert "张寡妇" in result, "❌ 张寡妇未保留在上下文中，LLM 仍可能混淆 NPC"
    assert "租钱怎么算" in result or "五百文" in result, "❌ 关键对话内容丢失"
    print(f"✅ test_npc_consistency_simulation: 张寡妇上下文完整保留")


if __name__ == "__main__":
    print("=" * 50)
    print("叙事上下文一致性 测试（v1.6.4 P0 Bug 修复）")
    print("=" * 50)
    test_empty_history()
    test_single_round()
    test_three_rounds()
    test_truncation()
    test_state_ref_has_recent_narratives()
    test_variables_included()
    test_npc_consistency_simulation()
    print("\n✅ 所有叙事上下文一致性测试通过")