"""🆕 v1.7.6 回归测试：make_dm_nodes 必须返回 5 个节点

修复历史：
- v1.7.6 用户报告 /api/start 返回 internal server error
- 根因：make_dm_nodes() 没有 return → 返回 None
- _build_graph() 期望解包 5 个节点，但解包 None 失败
- 这个 bug 之前没人发现，因为单元测试没测过完整 graph 构建

防回归：
1. make_dm_nodes() 必须返回 5 元素元组
2. _build_graph() 必须成功构建（不抛异常）
3. DMAgent.__init__() 必须成功
"""
import sys
sys.path.insert(0, "src")

import history_footnote  # noqa: F401  # 触发 logging
import logging
logger = logging.getLogger(__name__)


def test_make_dm_nodes_returns_5_nodes():
    """make_dm_nodes 必须返回 5 元素元组"""
    from history_footnote.dm_agent import make_dm_nodes
    from history_footnote.llm_providers import make_llm

    # 用 mock LLM（避免真实 API）
    llm = make_llm("mock")
    state_ref = {}  # 占位

    result = make_dm_nodes(llm, state_ref)
    assert result is not None, "make_dm_nodes 返回 None（致命）"
    assert isinstance(result, tuple), f"应返回 tuple，实际 {type(result)}"
    assert len(result) == 5, f"应返回 5 元素元组，实际 {len(result)}"
    skill_node, situation_node, should_continue, narrative_node, extract_node = result
    # 每个元素都应该可调用
    for name, node in [("skill", skill_node), ("situation", situation_node),
                       ("should_continue", should_continue), ("narrative", narrative_node),
                       ("extract", extract_node)]:
        assert callable(node), f"{name} 节点不可调用"
    print("✅ test_make_dm_nodes_returns_5_nodes: 5 个节点齐")


def test_dm_agent_init_no_error():
    """DMAgent.__init__ 必须成功（核心 smoke test）"""
    from history_footnote.dm_agent import DMAgent
    from history_footnote.llm_providers import make_llm
    from history_footnote.game_state import GameState

    # 准备最小依赖
    llm = make_llm("mock")
    state = GameState()
    state.identity = "女商人"
    state.gender = "女"
    state.hometown = "徽州"
    state.era_id = "wanli1587"

    # 用 mock era_config（避免依赖真实 era.json）
    era_config = {
        "era_id": "wanli1587",
        "era_name": "万历十五年",
        "iron_laws": [],
        "identity": {
            "role": "小人物",
            "social_class": "平民",
            "action_boundaries": {
                "can_access": ["茶馆"],
                "cannot_access": ["皇宫"],
                "can_interact_with": ["张顺"],
                "cannot_influence": ["皇帝"],
            },
        },
    }
    # 准备其他依赖（用 None 占位，DMAgent 不在 __init__ 中实际调用）
    try:
        agent = DMAgent(
            era_config=era_config,
            state=state,
            rule_engine=None,
            memory=None,
            knowledge_base=None,
            llm_model=llm,
        )
        assert agent.graph is not None, "graph 未构建"
        print(f"✅ test_dm_agent_init_no_error: DMAgent 初始化成功")
    except Exception as e:
        raise AssertionError(f"DMAgent 初始化失败: {e}")


def test_api_start_full_flow():
    """端到端：/api/start 完整流程（需要 web_server 运行）"""
    import urllib.request
    import urllib.error
    import json

    BASE = "http://localhost:8765"
    body = json.dumps({
        "era_id": "wanli1587",
        "identity": "女商人",
        "gender": "女",
        "hometown": "徽州",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/start", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise AssertionError(f"HTTP {e.code}: {body}")
    except Exception as e:
        raise AssertionError(f"请求失败: {e}")

    assert "session_id" in data, f"无 session_id: {data}"
    assert "error" not in data, f"返回 error: {data.get('error', '?')}"
    assert data.get("round_number") == 1, f"初始 round 应为 1，实际 {data.get('round_number')}"
    print(f"✅ test_api_start_full_flow: session={data['session_id'][:20]}...")


if __name__ == "__main__":
    print("=" * 50)
    print("DM Graph 回归测试（v1.7.6）")
    print("=" * 50)
    test_make_dm_nodes_returns_5_nodes()
    test_dm_agent_init_no_error()
    test_api_start_full_flow()
    print("\n✅ 所有 DM Graph 回归测试通过")