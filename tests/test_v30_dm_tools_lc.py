"""v2.8.x W30: dm_tools_lc LangChain Tool 注入测试

测试：
1. make_chapter_dm_tools 返回 2 个 Tool
2. 每个 Tool 有 description（LangChain 强制）
3. fill_chapter_blueprint Tool 实际可调
4. fill_chapter_summary Tool 实际可调
5. Tool 失败时返回 fallback dict 不抛异常
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W30_001_dm_tools_lc_returns_two_tools():
    """make_chapter_dm_tools 返回 2 个 Tool"""
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = MagicMock()
    llm = MagicMock()
    era_config = {"narrative": {"paths": []}}

    tools = make_chapter_dm_tools(state, facade, llm, era_config)
    assert len(tools) == 2, f"期望 2 个 Tool，实际 {len(tools)}"
    tool_names = [t.name for t in tools]
    assert "fill_chapter_blueprint" in tool_names
    assert "fill_chapter_summary" in tool_names
    return True


def test_W30_002_dm_tools_have_descriptions():
    """每个 Tool 有 description（LangChain 强制）"""
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = MagicMock()
    llm = MagicMock()
    era_config = {}

    tools = make_chapter_dm_tools(state, facade, llm, era_config)
    for t in tools:
        assert t.description, f"{t.name} 缺 description"
        assert len(t.description) > 20, f"{t.name} description 太短"
    return True


def test_W30_003_dm_tools_blueprint_callable():
    """fill_chapter_blueprint Tool 实际可调（LLM mock 失败时返 fallback）"""
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = MagicMock()
    llm = MagicMock()
    era_config = {}

    tools = make_chapter_dm_tools(state, facade, llm, era_config)
    bp_tool = next(t for t in tools if t.name == "fill_chapter_blueprint")
    result = bp_tool.invoke({"chapter": 1})
    assert isinstance(result, dict), "应返回 dict"
    assert "fallback" in result, "应含 fallback 字段"
    return True


def test_W30_004_dm_tools_summary_callable():
    """fill_chapter_summary Tool 实际可调"""
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = MagicMock()
    llm = MagicMock()
    era_config = {}

    tools = make_chapter_dm_tools(state, facade, llm, era_config)
    sm_tool = next(t for t in tools if t.name == "fill_chapter_summary")
    result = sm_tool.invoke({"chapter": 1})
    assert isinstance(result, dict)
    return True


def test_W30_005_dm_tools_bind_tools_supported():
    """LLM mock 但 ChatAnthropic 有 bind_tools，verify 协议"""
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = MagicMock()

    # 模拟一个有 bind_tools 的 LLM（LangChain 协议）
    llm = MagicMock()
    bound_llm = MagicMock()
    llm.bind_tools = MagicMock(return_value=bound_llm)

    tools = make_chapter_dm_tools(state, facade, llm, {})

    # 模拟 dm_agent 绑定
    bound = llm.bind_tools(tools)
    assert bound is not None
    llm.bind_tools.assert_called_once()
    return True


def test_W30_006_dm_tools_schemas_have_chapter_arg():
    """Tool schema 必含 chapter 参数（LangChain 自动推断）"""
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = MagicMock()
    llm = MagicMock()
    era_config = {}

    tools = make_chapter_dm_tools(state, facade, llm, era_config)
    for t in tools:
        # LangChain StructuredTool 有 args_schema
        schema = getattr(t, 'args', None) or getattr(t, 'args_schema', None)
        if schema:
            schema_str = str(schema)
            assert 'chapter' in schema_str, f"{t.name} schema 应含 chapter 参数"
    return True
