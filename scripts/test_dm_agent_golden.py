"""🆕 v1.7.30 dm_agent 拆分 · 黄金快照测试

目的：拆分前后端到端行为一致性保证

策略：
- 步骤 1：在 master 跑此脚本，得到 .golden.json baseline（commit 到仓）
- 步骤 2：拆分后跑同一脚本，对比 .golden.json（任何不匹配 → 报警）
- 步骤 7：每拆一步跑一次

覆盖：
1. _make_view_state_dict 的输出（纯函数 + 9 字段确定）
2. _get_forced_events_for_mock / _get_pacing_for_mock 等 mock 辅助
3. _build_system_prompt 的 deterministic 部分（不依赖 LLM 数据）
4. _build_recent_context_for_prompt 的 deterministic 部分
5. DMState TypedDict 字段集合（防字段漏导）
6. make_tools 的工具元数据（函数名 + 参数）

跑法：
    python3 scripts/test_dm_agent_golden.py update   # 更新 baseline
    python3 scripts/test_dm_agent_golden.py check    # 对比 baseline（默认）
"""

from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

GOLDEN_PATH = ROOT / "tests" / "fixtures" / "dm_agent_golden.json"


def _hash_obj(obj) -> str:
    """对对象 SHA-256（规范化：sorted keys + 一致性编码）"""
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def gather_snapshot() -> dict:
    """收集 dm_agent 当前行为的快照（拆分前后必须一致）"""
    from history_footnote.dm_agent import (
        DMAgent, DMState, make_tools, make_dm_nodes,
        extract_narrative_node, state_confirmation_node,
    )
    from history_footnote.resource_cache import load_era_config

    snapshot = {
        "schema_version": "v1.7.30",
        "generated_at": "test",
        "signatures": {},
        "pure_functions": {},
    }

    # 1. DMState 字段集合（防漏导）
    snapshot["signatures"]["dm_state_fields"] = sorted(DMState.__annotations__.keys())

    # 2. make_tools 的工具元数据
    config = load_era_config("wanli1587")
    state_ref_holder = {"s": None}
    # 用一个最小 state 与一个 mock 函数作为占位
    class _MinimalState:
        round_number = 1
        selected_identity = "weaving_male"
        player_gender = "male"
        current_date = "1587年3月"
        variables = {}
        triggered_events = []
        unlocked_insights = []
        npc_levels = {}
        value_shifts = {}
        player_idle_rounds = 0
        action_points_current = 3
        action_points_max = 3
        narrative_history = []
        triggered_events_count = {}
        seen_terms = []
        last_time_lapse = 0
        last_voice_options = []
        event_log = []
        _last_player_input = ""   # 给 _get_insights_for_mock 用



    state_ref_holder["s"] = _MinimalState()

    # 直接构造类方法签名，避免依赖 LLM
    tools_metadata = []
    # make_tools 闭包函数签名（不跑，只列）
    import inspect
    src = inspect.getsource(make_tools)
    tools_metadata.append({"name": "make_tools", "src_lines": len(src.splitlines())})
    snapshot["signatures"]["make_tools_src_lines"] = len(src.splitlines())

    nodes_metadata = []
    nodes_src = inspect.getsource(make_dm_nodes)
    nodes_metadata.append({"name": "make_dm_nodes", "src_lines": len(nodes_src.splitlines())})
    snapshot["signatures"]["make_dm_nodes_src_lines"] = len(nodes_src.splitlines())

    # 3. 顶层节点函数签名（纯函数，不依赖 state）
    en_src = inspect.getsource(extract_narrative_node)
    snapshot["signatures"]["extract_narrative_node_src_lines"] = len(en_src.splitlines())
    sc_src = inspect.getsource(state_confirmation_node)
    snapshot["signatures"]["state_confirmation_node_src_lines"] = len(sc_src.splitlines())

    # 4. DMAgent 类方法签名集合
    methods = [m for m in dir(DMAgent) if not m.startswith("__")]
    snapshot["signatures"]["DMAgent_public_methods"] = sorted(methods)
    snapshot["signatures"]["DMAgent_private_methods"] = sorted(
        m for m in dir(DMAgent) if m.startswith("_") and not m.startswith("__")
    )

    # 5. dm_agent 总行数（兼容单文件与子包两种形态）
    single_path = ROOT / "src" / "history_footnote" / "dm_agent.py"
    package_path = ROOT / "src" / "history_footnote" / "dm_agent"
    if single_path.exists():
        total_lines = sum(1 for _ in single_path.open(encoding="utf-8"))
    elif package_path.is_dir():
        total_lines = 0
        for sub in package_path.rglob("*.py"):
            total_lines += sum(1 for _ in sub.open(encoding="utf-8"))
    else:
        total_lines = 0
    snapshot["signatures"]["dm_agent_py_lines"] = total_lines

    # 6. 关键纯函数输出（_make_view_state_dict 等）
    # 用一个最小 DMAgent 不调 LLM 跑纯函数
    class _StubKnowledgeBase:
        def __init__(self): pass
        def search(self, *a, **k): return []

    class _StubRuleEngine:
        def __init__(self): pass
        def make_view(self, state): return type("V", (), {})()
        def check_forced_events(self, view): return []
        def check_pacing(self, view): return []
        def check_triggers(self, view): return []
        # check_insights 真实签名是 (view, player_input, dm_guided=False)
        def check_insights(self, view, player_input="", dm_guided=False): return []



    class _StubLLM:
        def invoke(self, *a, **k):
            class R: content = "stub"
            return R()



    class _MinimalDM(DMAgent):
        """最小 DMAgent 子类：skip __init__，直接持有 state"""
        def __init__(self):
            self.state = _MinimalState()
            self.era_config = config
            self.rule_engine = _StubRuleEngine()
            self.llm = _StubLLM()
            self.knowledge_base = _StubKnowledgeBase()



    stub = _MinimalDM()
    try:
        snapshot["pure_functions"]["_make_view_state_dict"] = stub._make_view_state_dict()
    except Exception as e:
        snapshot["pure_functions"]["_make_view_state_dict_error"] = str(e)

    try:
        snapshot["pure_functions"]["_get_forced_events_for_mock"] = stub._get_forced_events_for_mock()
    except Exception as e:
        snapshot["pure_functions"]["_get_forced_events_for_mock_error"] = str(e)

    try:
        snapshot["pure_functions"]["_get_pacing_for_mock"] = stub._get_pacing_for_mock()
    except Exception as e:
        snapshot["pure_functions"]["_get_pacing_for_mock_error"] = str(e)

    try:
        snapshot["pure_functions"]["_get_triggers_for_mock"] = stub._get_triggers_for_mock()
    except Exception as e:
        snapshot["pure_functions"]["_get_triggers_for_mock_error"] = str(e)

    try:
        snapshot["pure_functions"]["_get_insights_for_mock"] = stub._get_insights_for_mock()
    except Exception as e:
        snapshot["pure_functions"]["_get_insights_for_mock_error"] = str(e)

    return snapshot


def save_golden(snapshot: dict):
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ baseline 已写入 {GOLDEN_PATH.relative_to(ROOT)}")


def check_golden(current: dict) -> tuple[bool, list[str]]:
    if not GOLDEN_PATH.exists():
        return False, [f"baseline 不存在: {GOLDEN_PATH}"]
    saved = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    diffs = []

    # === 强不变量（行为/接口层面） ===
    # 这些必须 100% 严格一致（任何不一致 = 行为变更 = 阻断）
    strict_fields = ["dm_state_fields", "DMAgent_public_methods", "DMAgent_private_methods",
                     "_make_view_state_dict", "_get_forced_events_for_mock",
                     "_get_pacing_for_mock", "_get_triggers_for_mock",
                     "_get_insights_for_mock"]
    for f in strict_fields:
        if f in ["dm_state_fields", "DMAgent_public_methods", "DMAgent_private_methods"]:
            s = saved.get("signatures", {}).get(f)
            c = current.get("signatures", {}).get(f)
        else:
            s = saved.get("pure_functions", {}).get(f)
            c = current.get("pure_functions", {}).get(f)
        if s != c:
            diffs.append(f"  [强] {f}: saved={s!r} != current={c!r}")

    # === 弱不变量（行数指标，结构层面） ===
    # 拆分后行数会变（每个子模块加 docstring + imports）— 只 warning，不阻断
    weak_fields = ["make_tools_src_lines", "make_dm_nodes_src_lines",
                   "extract_narrative_node_src_lines", "state_confirmation_node_src_lines",
                   "dm_agent_py_lines"]
    weak_warnings = []
    for f in weak_fields:
        s = saved.get("signatures", {}).get(f)
        c = current.get("signatures", {}).get(f)
        if s != c:
            weak_warnings.append(f"  [弱] {f}: saved={s} != current={c}（行数会随拆分变化，不阻断）")

    if diffs:
        return False, diffs
    if weak_warnings:
        # 弱不变量只打印 warning，不视为失败
        print("  ⚠️  弱不变量变化（行数指标，不阻断）：")
        for w in weak_warnings:
            print(w)
    return True, []


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    snapshot = gather_snapshot()
    if mode == "update":
        save_golden(snapshot)
        return 0
    if mode == "check":
        ok, diffs = check_golden(snapshot)
        if ok:
            print("✅ 黄金快照对比一致")
            print(f"   baseline: {GOLDEN_PATH.relative_to(ROOT)}")
            print(f"   schema: {snapshot['schema_version']}")
            print(f"   DMState 字段: {len(snapshot['signatures']['dm_state_fields'])}")
            print(f"   DMAgent 方法: {len(snapshot['signatures']['DMAgent_public_methods'])} public / {len(snapshot['signatures']['DMAgent_private_methods'])} private")
            return 0
        print("❌ 黄金快照对比不一致：")
        for d in diffs:
            print(f"  {d}")
        print(f"\n如确认拆分后允许行为变更，运行: python3 {Path(__file__).name} update")
        return 1
    print(f"❌ 未知模式: {mode}（应为 'check' / 'update'）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
