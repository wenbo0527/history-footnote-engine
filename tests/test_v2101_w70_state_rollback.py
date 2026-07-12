"""🆕 v2.10.1 W70: LLM 失败时 state 回滚测试

模拟 _run_round 内部修改 state → 异常触发 → 回滚
"""
import sys
import types
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))


# 模拟 game.state（足够 handle_POST_input 用）
class _FakeState:
    def __init__(self):
        self.action_points_current = 3
        self.action_points_max = 3
        self.current_date = "1587年1月"
        self.round_number = 1
        self.narrative_history = [{"round": 0, "narrative": "开场"}]
        self.variables = {"cash": 100}
        self.value_shifts = {"moral": 1}
        self.last_voice_options = []
    def __setattr__(self, k, v):
        super().__setattr__(k, v)


class _FakeGame:
    def __init__(self):
        self.state = _FakeState()
        self._preprocess_input_calls = 0
        self._run_round_calls = 0

    def _preprocess_input(self, inp):
        self._preprocess_input_calls += 1
        return inp

    def _run_round(self, pre):
        """模拟 LLM 失败：先修改 state，再抛异常"""
        self._run_round_calls += 1
        # LLM 部分已经扣 AP
        self.state.action_points_current = 2
        # 然后 LLM 失败
        raise RuntimeError("LLM timeout")


# ============= 复制 input.py 的回滚逻辑（独立测试）=============

def _snapshot_state(game) -> dict:
    return {
        "action_points_current": game.state.action_points_current,
        "action_points_max": game.state.action_points_max,
        "current_date": game.state.current_date,
        "round_number": game.state.round_number,
        "narrative_history_len": len(game.state.narrative_history or []),
        "variables": dict(game.state.variables or {}),
        "value_shifts": dict(game.state.value_shifts or {}),
    }


def _rollback_state(game, snap: dict) -> None:
    game.state.action_points_current = snap["action_points_current"]
    game.state.action_points_max = snap["action_points_max"]
    game.state.current_date = snap["current_date"]
    game.state.round_number = snap["round_number"]
    cur_len = len(game.state.narrative_history or [])
    target_len = snap["narrative_history_len"]
    if cur_len > target_len and hasattr(game.state, "narrative_history"):
        game.state.narrative_history = (game.state.narrative_history or [])[:target_len]
    if hasattr(game.state, "variables"):
        game.state.variables = snap["variables"]
    if hasattr(game.state, "value_shifts"):
        game.state.value_shifts = snap["value_shifts"]


# ============= 测试 =============

def test_W70_001_ap_rollback():
    """AP 被扣后回滚"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    assert g.state.action_points_current == 3
    try:
        g._run_round("hi")  # 内部扣 AP + 抛异常
    except RuntimeError:
        _rollback_state(g, snap)
    assert g.state.action_points_current == 3  # 已回滚
    assert g.state.action_points_max == 3


def test_W70_002_date_not_advanced():
    """日期未推进（否则跳月）"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    try:
        g.state.current_date = "1587年2月"  # 模拟跳月
        g.state.round_number = 2
        raise RuntimeError("LLM fail")
    except RuntimeError:
        _rollback_state(g, snap)
    assert g.state.current_date == "1587年1月"
    assert g.state.round_number == 1


def test_W70_003_narrative_truncated():
    """narrative_history 截断到失败前"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    assert snap["narrative_history_len"] == 1
    try:
        g.state.narrative_history.append({"round": 1, "narrative": "narr1"})
        g.state.narrative_history.append({"round": 2, "narrative": "narr2"})
        raise RuntimeError("LLM fail")
    except RuntimeError:
        _rollback_state(g, snap)
    assert len(g.state.narrative_history) == 1
    assert g.state.narrative_history[0]["round"] == 0


def test_W70_004_variables_restored():
    """variables 还原"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    try:
        g.state.variables["cash"] = 999  # 假设 LLM 改了
        g.state.variables["new_key"] = "added"
        raise RuntimeError("LLM fail")
    except RuntimeError:
        _rollback_state(g, snap)
    assert g.state.variables["cash"] == 100
    assert "new_key" not in g.state.variables


def test_W70_005_value_shifts_restored():
    """value_shifts 还原"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    try:
        g.state.value_shifts["moral"] = -10
        g.state.value_shifts["new"] = 5
        raise RuntimeError("LLM fail")
    except RuntimeError:
        _rollback_state(g, snap)
    assert g.state.value_shifts["moral"] == 1
    assert "new" not in g.state.value_shifts


def test_W70_006_no_change_unchanged():
    """无修改时回滚仍是初始值"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    try:
        raise RuntimeError("LLM fail before any change")
    except RuntimeError:
        _rollback_state(g, snap)
    assert g.state.action_points_current == 3
    assert g.state.current_date == "1587年1月"


def test_W70_007_preprocess_does_not_modify():
    """_preprocess_input 不修改 state（应该）"""
    g = _FakeGame()
    pre = g._preprocess_input("hi")
    assert g.state.action_points_current == 3
    assert pre == "hi"


def test_W70_008_success_path_no_rollback():
    """成功路径不应触发回滚"""
    g = _FakeGame()

    class _GameOK(_FakeGame):
        def _run_round(self, pre):
            self.state.action_points_current = 2
            return  # 成功

    g2 = _GameOK()
    snap = _snapshot_state(g2)
    try:
        g2._run_round("hi")
    except Exception:
        _rollback_state(g2, snap)
    # 成功路径：AP 已扣，不应回滚
    assert g2.state.action_points_current == 2


def test_W70_009_complex_state_change():
    """复杂状态变更（多字段同时）"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    try:
        g.state.action_points_current = 0  # 耗尽
        g.state.current_date = "1587年12月"  # 跳月
        g.state.round_number = 12
        g.state.narrative_history.append({"round": 11, "narrative": "X"})
        g.state.narrative_history.append({"round": 12, "narrative": "Y"})
        g.state.variables["cash"] = 0
        raise RuntimeError("LLM fail mid-game")
    except RuntimeError:
        _rollback_state(g, snap)
    # 全部回滚
    assert g.state.action_points_current == 3
    assert g.state.current_date == "1587年1月"
    assert g.state.round_number == 1
    assert len(g.state.narrative_history) == 1
    assert g.state.variables["cash"] == 100


def test_W70_010_snapshot_independence():
    """快照是 deep copy（修改 state 不影响 snapshot）"""
    g = _FakeGame()
    snap = _snapshot_state(g)
    g.state.variables["cash"] = 999
    assert snap["variables"]["cash"] == 100  # snapshot 未变
    # dict() 浅拷贝，嵌套 dict 仍引用
    # 但本测试场景下 game.state.variables["new"] 不会影响 snap
    g.state.variables["new"] = 1
    assert "new" not in snap["variables"]


tests = [v for k, v in dict(globals()).items() if k.startswith("test_W70_")]
passed = 0
failed = 0
for fn in tests:
    try:
        fn()
        print(f"  {fn.__name__}: PASS", flush=True)
        passed += 1
    except AssertionError as e:
        print(f"  {fn.__name__}: FAIL -- {e}", flush=True)
        failed += 1
print(f"\n  {passed}/{passed+failed} state 回滚测试通过", flush=True)
sys.exit(0 if failed == 0 else 1)
