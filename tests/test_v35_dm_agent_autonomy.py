"""🆕 v2.9.x W35: dm_agent LangGraph Tool 自主决策验证（最终版）

W35 关键发现：DMAgent.tools 实际有 12 个（不是 10/11）。
decision_tools 6 个含 fill_chapter_blueprint + fill_chapter_summary，
**已 bind 给 LLM**（v2.7+ Wiki Agent 拆分后 LLM 自主决策章节生成）。

测试：
1. make_tools 返 12 个 Tool（含 fill_chapter_*）
2. DMAgent.tools = 12
3. DMAgent.decision_tools = 6（bind LLM，含 fill_chapter_*）
4. DMAgent.query_tools = 6（不 bind LLM）
5. fill_chapter Tool 实际可调
6. 拆分规则正确
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W35_001_make_tools_returns_12():
    """make_tools 返 12 个 Tool"""
    from history_footnote.dm_agent.tools import make_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    tools = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
    assert len(tools) == 12, f"期望 12 个 Tool，实际 {len(tools)}"
    names = [t.name for t in tools]
    assert "fill_chapter_blueprint" in names
    assert "fill_chapter_summary" in names
    return True


def test_W35_002_dma_tools_has_12():
    """DMAgent.tools = 12（含 fill_chapter_*）"""
    from history_footnote.dm_agent.agent import DMAgent
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=MagicMock())

    agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
    assert len(agent.tools) == 12, f"期望 12，实际 {len(agent.tools)}"
    names = [t.name for t in agent.tools]
    assert "fill_chapter_blueprint" in names
    assert "fill_chapter_summary" in names
    return True


def test_W35_003_decision_tools_6_includes_fill_chapter():
    """decision_tools = 6，含 fill_chapter_*（v2.7+ LLM 自主决策）"""
    from history_footnote.dm_agent.agent import DMAgent
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=MagicMock())

    agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
    assert len(agent.decision_tools) == 6, f"期望 6 decision_tools，实际 {len(agent.decision_tools)}"
    names = [t.name for t in agent.decision_tools]
    assert "fill_chapter_blueprint" in names, "fill_chapter_blueprint 应在 decision_tools"
    assert "fill_chapter_summary" in names, "fill_chapter_summary 应在 decision_tools"
    assert "save_event" in names
    assert "roll_dice" in names
    return True


def test_W35_004_query_tools_6_excludes_fill_chapter():
    """query_tools = 6，不含 fill_chapter_*"""
    from history_footnote.dm_agent.agent import DMAgent
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=MagicMock())

    agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
    assert len(agent.query_tools) == 6, f"期望 6 query_tools，实际 {len(agent.query_tools)}"
    names = [t.name for t in agent.query_tools]
    assert "fill_chapter_blueprint" not in names
    assert "fill_chapter_summary" not in names
    return True


def test_W35_005_bind_tools_called_with_6_decision_tools():
    """LLM.bind_tools 接收 6 个 decision_tools（含 fill_chapter）"""
    from history_footnote.dm_agent.agent import DMAgent
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=MagicMock())

    agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
    # bind_tools 应被调（至少 1 次）
    assert llm.bind_tools.called, "bind_tools 未被调"
    # 收集所有 bind_tools 调用，最后一次应是 decision_tools
    all_calls = llm.bind_tools.call_args_list
    last_call = all_calls[-1]
    bound_tools = last_call[0][0]
    assert len(bound_tools) == 6, f"应绑 6 个，实际 {len(bound_tools)}"
    bound_names = [t.name for t in bound_tools]
    assert "fill_chapter_blueprint" in bound_names, "LLM 应能调 fill_chapter_blueprint"
    assert "fill_chapter_summary" in bound_names, "LLM 应能调 fill_chapter_summary"
    return True


def test_W35_006_fill_chapter_blueprint_callable():
    """fill_chapter_blueprint Tool 实际可调（mock LLM）"""
    from history_footnote.dm_agent.tools import make_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    tools = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
    bp_tool = next(t for t in tools if t.name == "fill_chapter_blueprint")
    result = bp_tool.invoke({"chapter_id": 1})
    assert isinstance(result, dict), f"应返 dict，实际 {type(result)}"
    return True


def test_W35_007_fill_chapter_summary_callable():
    """fill_chapter_summary Tool 实际可调"""
    from history_footnote.dm_agent.tools import make_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    tools = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
    sm_tool = next(t for t in tools if t.name == "fill_chapter_summary")
    result = sm_tool.invoke({"chapter_id": 1})
    assert isinstance(result, dict)
    return True


def test_W35_008_decision_query_split_6_6():
    """决策 6 + 查询 6 = 12（v2.7+ 拆分正确）"""
    from history_footnote.dm_agent.agent import DMAgent
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=MagicMock())

    agent = DMAgent({}, state, MagicMock(), MagicMock(), MagicMock(), llm)
    assert len(agent.decision_tools) == 6
    assert len(agent.query_tools) == 6
    assert len(agent.decision_tools) + len(agent.query_tools) == 12
    return True


def test_W35_009_fill_chapter_has_descriptions():
    """fill_chapter Tool 必有 description（LangChain 强制）"""
    from history_footnote.dm_agent.tools import make_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    tools = make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})

    for name in ["fill_chapter_blueprint", "fill_chapter_summary"]:
        tool = next(t for t in tools if t.name == name)
        assert tool.description, f"{name} 缺 description"
        assert len(tool.description) > 20, f"{name} description 太短"
    return True


def test_W35_010_dm_tools_lc_consistent():
    """chapter.dm_tools_lc 与 dm_agent.tools 都有 fill_chapter（一致性）"""
    from history_footnote.dm_agent.tools import make_tools as agent_make_tools
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"

    agent_tools = agent_make_tools(state, MagicMock(), MagicMock(), MagicMock(), {})
    lc_tools = make_chapter_dm_tools(state, MagicMock(), MagicMock(), {})

    agent_names = {t.name for t in agent_tools}
    lc_names = {t.name for t in lc_tools}

    assert "fill_chapter_blueprint" in agent_names
    assert "fill_chapter_blueprint" in lc_names
    assert "fill_chapter_summary" in agent_names
    assert "fill_chapter_summary" in lc_names
    return True
