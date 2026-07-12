"""v2.10.1 W52 真 LLM 20 回合端到端测试发现 bug 修复

bug 3: extract_narrative_node 未定义（dm_agent/nodes/factory.py:291）
- 原因：factory.py 调 extract_narrative_node(state) 但未 import
- 影响：真 LLM 路径每回合都 NameError（被 try/except 吞掉）
- 修复：factory.py 顶部加 from ... import extract_narrative_node

修复后回归测试（不调真 LLM，用结构验证）。
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def test_factory_imports_extract_narrative_node():
    """dm_agent/nodes/factory.py 必须 import extract_narrative_node

    修复前：闭包 extract_narrative_node_inner 调未定义的 extract_narrative_node
    修复后：import 存在
    """
    from history_footnote.dm_agent.nodes import factory

    src = Path(factory.__file__).read_text(encoding="utf-8")
    assert "extract_narrative_node" in src
    # 必须是 import 形式，不是注释或字符串
    assert "from history_footnote.dm_agent.nodes.extract import extract_narrative_node" in src \
        or "import extract_narrative_node" in src


def test_factory_callable_with_mock_state():
    """factory.make_dm_nodes 应返回 5 个节点，第 5 个能调到底层 extract_narrative_node（mock state）"""
    from history_footnote.dm_agent.nodes.factory import make_dm_nodes
    from history_footnote.dm_agent.state import DMState

    # 构造极简 state
    state = DMState(
        messages=[],
        view_state={},
        forced_events=[],
        triggered_rules=[],
        pacing_directives=[],
        insight_candidates=[],
        drama_hint="",
        narrative_skill_hints=[],
    )

    # 拿到 5 个节点（最后是 extract_narrative_node_inner 闭包）
    nodes = make_dm_nodes(state_ref=[state], llm_with_tools=None)
    assert len(nodes) == 5, f"make_dm_nodes 应返回 5 节点，实际 {len(nodes)}"
    extract_node = nodes[4]  # extract_narrative_node_inner

    # 调闭包版 — 修复前抛 NameError
    try:
        extract_node(state)
    except NameError as e:
        if "extract_narrative_node" in str(e):
            pytest.fail(f"extract_narrative_node bug 未修复: {e}")
    except Exception:
        # 其他错误（如 missing field）可接受
        pass


def test_real_llm_smoke_1_round(monkeypatch):
    """真 LLM 1 回合应不抛 extract_narrative_node 异常

    仅当 REAL_LLM=1 且凭据存在时运行。
    """
    import os
    if os.environ.get("REAL_LLM") != "1":
        pytest.skip("设 REAL_LLM=1 启用真 LLM 测试")
    if not os.environ.get("MINIMAX_API_KEY"):
        pytest.skip("MINIMAX_API_KEY 未设置")

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from history_footnote.llm_wrapper import get_wrapped_llm
    from history_footnote.game_loop import GameLoop

    real_llm = get_wrapped_llm(primary_provider="minimax-anthropic")
    era_config = json.loads(
        Path("eras/wanli1587/era.json").read_text(encoding="utf-8")
    )
    loop = GameLoop(
        era_id="wanli1587",
        era_config=era_config,
        llm_model=real_llm,
        selected_identity="weaving_male",
    )

    try:
        loop._run_round("我织了一匹湖绫")
    except NameError as e:
        if "extract_narrative_node" in str(e):
            pytest.fail(f"extract_narrative_node bug 回归: {e}")
        raise
    # 验证 narrative 生成
    nh = getattr(loop.state, "narrative_history", [])
    assert len(nh) >= 1, "真 LLM 应生成 narrative"
