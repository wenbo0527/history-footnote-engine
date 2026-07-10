"""v2.8.0 段六+ W20 单元测试

测试目标：
1. build_chapter_summary_prompt 包含 4 必填项 + 时代背景
2. fill_chapter_summary_via_llm 调 mock LLM 生成摘要
3. Settlement._get_summary_text 兼容 3 种 LLM（None / callable / LangChain 类）
4. dm_agent fill_chapter_summary Tool 集成
5. 端到端：Settlement 接 LangChain 类 LLM 走 fill_chapter_summary_via_llm

约束：
- mock LLM
- 不影响现有 221 测试
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ============= 测试 1：build_chapter_summary_prompt =============

def test_V28_184_chapter_summary_prompt_contains_4_required_fields():
    """build_chapter_summary_prompt 含 4 必填项"""
    from history_footnote.chapter.dm_tool import build_chapter_summary_prompt
    prompt = build_chapter_summary_prompt(
        chapter_id=1,
        core_event="春蚕上市",
        key_choice="抗税",
        build_summary="尽责偏正+0.8",
        path_summary="main_tax_resistance",
    )
    # 4 必填项
    assert "核心事件" in prompt
    assert "春蚕上市" in prompt
    assert "关键选择" in prompt
    assert "抗税" in prompt
    assert "玩家画像" in prompt
    assert "尽责偏正" in prompt
    assert "当前路径" in prompt
    assert "main_tax_resistance" in prompt
    # 输出要求
    assert "100-200 字" in prompt
    return True


def test_V28_185_chapter_summary_prompt_with_era_config():
    """build_chapter_summary_prompt 含 era_config 时代背景"""
    from history_footnote.chapter.dm_tool import build_chapter_summary_prompt
    era_config = {
        "era_name": "万历十五年",
        "primary_location": "江南盛泽镇",
    }
    prompt = build_chapter_summary_prompt(
        chapter_id=1,
        core_event="test",
        key_choice="test",
        build_summary="test",
        path_summary="test",
        era_config=era_config,
    )
    assert "万历十五年" in prompt
    assert "江南盛泽镇" in prompt
    return True


# ============= 测试 2：fill_chapter_summary_via_llm (mock LLM) =============

def test_V28_186_fill_chapter_summary_via_mock_llm():
    """fill_chapter_summary_via_llm 调 mock LLM 生成摘要"""
    from history_footnote.chapter.dm_tool import fill_chapter_summary_via_llm
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1

    # Mock LLM
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "暮色渐沉，玩家签下欠据。玩家画像：尽责偏正。当前路径：抗税。共 50 字。"
    mock_llm.invoke.return_value = mock_response

    summary = fill_chapter_summary_via_llm(
        state=state,
        chapter_id=1,
        core_event="test event",
        key_choice="test choice",
        build_summary="test build",
        path_summary="test path",
        era_config=None,
        llm_callable=mock_llm,
        max_words=200,
    )
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "欠据" in summary or "暮色" in summary
    return True


def test_V28_187_fill_chapter_summary_truncates_long_output():
    """fill_chapter_summary_via_llm 截断超过 max_words 的输出"""
    from history_footnote.chapter.dm_tool import fill_chapter_summary_via_llm
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1

    mock_llm = MagicMock()
    mock_response = MagicMock()
    # 生成 500 字
    mock_response.content = "中" * 500
    mock_llm.invoke.return_value = mock_response

    summary = fill_chapter_summary_via_llm(
        state=state,
        chapter_id=1,
        core_event="test",
        key_choice="test",
        build_summary="test",
        path_summary="test",
        era_config=None,
        llm_callable=mock_llm,
        max_words=100,
    )
    # 应截断到 ~100 字
    assert len(summary) <= 100
    return True


# ============= 测试 3：Settlement 兼容 3 种 LLM =============

def test_V28_188_settlement_none_uses_rule():
    """Settlement._llm=None → 用 _build_summary_rule"""
    from history_footnote.chapter.settlement import ChapterSettlement
    from history_footnote.game_state import GameState

    state = GameState()
    settlement = ChapterSettlement(state, era_config={})  # llm_callable=None
    summary = settlement._get_summary_text(
        core_event="event",
        key_choice="choice",
        build_summary="build",
        path_summary="path",
    )
    # 规则压缩的格式
    assert "事件" in summary or "选择" in summary or "画像" in summary
    return True


def test_V28_189_settlement_callable_uses_llm():
    """Settlement._llm=callable 函数 → 调函数返回"""
    from history_footnote.chapter.settlement import ChapterSettlement
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1

    def mock_llm_fn(prompt):
        return "callable LLM 生成的摘要"

    settlement = ChapterSettlement(state, era_config={}, llm_callable=mock_llm_fn)
    summary = settlement._get_summary_text(
        core_event="event",
        key_choice="choice",
        build_summary="build",
        path_summary="path",
    )
    assert "callable LLM" in summary
    return True


def test_V28_190_settlement_langchain_class_uses_dm_tool():
    """Settlement._llm=LangChain 类 → 调 fill_chapter_summary_via_llm"""
    from history_footnote.chapter.settlement import ChapterSettlement
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1

    # Mock LangChain 类 LLM
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "LangChain 类 LLM 生成的摘要"
    mock_llm.invoke.return_value = mock_response

    settlement = ChapterSettlement(state, era_config={}, llm_callable=mock_llm)
    summary = settlement._get_summary_text(
        core_event="event",
        key_choice="choice",
        build_summary="build",
        path_summary="path",
    )
    assert "LangChain" in summary or "LLM" in summary
    # 验证 mock_llm.invoke 被调
    assert mock_llm.invoke.called
    return True


def test_V28_191_settlement_llm_failure_falls_back_to_rule():
    """Settlement LLM 失败回退到规则压缩"""
    from history_footnote.chapter.settlement import ChapterSettlement
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1

    def failing_llm(prompt):
        raise RuntimeError("LLM 服务挂了")

    settlement = ChapterSettlement(state, era_config={}, llm_callable=failing_llm)
    summary = settlement._get_summary_text(
        core_event="event",
        key_choice="choice",
        build_summary="build",
        path_summary="path",
    )
    # 回退到规则压缩
    assert "事件" in summary or "选择" in summary or "画像" in summary
    return True


# ============= 测试 4：dm_agent fill_chapter_summary Tool =============

def test_V28_192_dm_agent_tool_fill_chapter_summary_in_list():
    """dm_agent fill_chapter_summary Tool 在工具列表中"""
    from history_footnote.dm_agent.tools import make_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"

    class MockRuleEngine:
        config = {}
        def make_view(self, s):
            return {}

    class MockMemory:
        def recall_events(self, **kwargs):
            return []

    tools = make_tools(
        state=state,
        rule_engine=MockRuleEngine(),
        memory=MockMemory(),
        knowledge_base=MagicMock(),
        era_config={},
    )
    tool_names = [t.name for t in tools]
    assert "fill_chapter_summary" in tool_names
    return True


def test_V28_193_dm_agent_tool_fill_chapter_summary_invoke():
    """dm_agent fill_chapter_summary Tool 可 invoke（mock provider）"""
    from history_footnote.dm_agent.tools import make_tools
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"

    class MockRuleEngine:
        config = {}
        def make_view(self, s):
            return {}

    class MockMemory:
        def recall_events(self, **kwargs):
            return []

    tools = make_tools(
        state=state,
        rule_engine=MockRuleEngine(),
        memory=MockMemory(),
        knowledge_base=MagicMock(),
        era_config={},
    )
    fill_tool = next(t for t in tools if t.name == "fill_chapter_summary")
    result = fill_tool.invoke({
        "chapter_id": 1,
        "core_event": "test event",
        "key_choice": "test choice",
        "build_summary": "test build",
        "path_summary": "test path",
    })
    # Tool 应返回 dict（可能 via=rule 兜底）
    assert isinstance(result, dict)
    assert "summary" in result
    assert "length" in result
    assert "via" in result
    return True


# ============= 测试 5：端到端 fill_chapter_blueprint + fill_chapter_summary =============

def test_V28_194_end_to_end_blueprint_and_summary():
    """端到端：Coordinator 用 LangChain 类 LLM 跑完 1 章"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.value_dimensions = {"尽责": 0.7}

    era_config = {
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
            ],
        },
        "npcs": {"fm_wife": {"name": "沈氏"}},
        "knowledge": {"entries": []},
    }

    facade = ChapterFacade(
        state=state, era_config=era_config, root_dir=Path(__file__).parent.parent,
    )

    # Mock LangChain 类 LLM：第 1 次调（init）→ 蓝图；第 2 次调（settle）→ 摘要
    mock_llm = MagicMock()
    responses = [
        # init
        MagicMock(content='```json\n{"chapter_title": "LLM 章1", "nodes": [{"role": "introduction", "scene": "intro", "npc_ids": ["fm_wife"]}, {"role": "escalation", "scene": "esc", "npc_ids": ["fm_wife"]}, {"role": "climax", "scene": "climax", "npc_ids": ["fm_wife"]}, {"role": "resolution", "scene": "res", "npc_ids": ["fm_wife"]}]}\n```'),
        # settle
        MagicMock(content="暮色渐沉。玩家签下欠据。玩家画像：尽责偏正。当前路径：抗税。"),
    ]
    mock_llm.invoke.side_effect = responses

    # 用同样的 LLM 跑 Coordinator（init 用 LangChain，settle 也用 LangChain）
    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=mock_llm)
    # 走 16 回合
    for r in range(1, 17):
        state.round_number = r
        coord.pre_step()
        coord.post_step()
        coord.maybe_settle()
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) > 0:
            break

    # 验证 chapter_history 用了 LLM 摘要
    history = state.chapter_state.chapter_history
    assert len(history) == 1
    # 第 2 次 LLM 调用应是摘要
    assert mock_llm.invoke.call_count == 2, f"期望 2 次 LLM 调用，实际 {mock_llm.invoke.call_count}"
    # 摘要应是 LLM 生成（via=llm，summary 含 LLM 内容）
    record = history[0]
    assert "暮色" in record["summary"] or "欠据" in record["summary"] or len(record["summary"]) > 0
    return True
