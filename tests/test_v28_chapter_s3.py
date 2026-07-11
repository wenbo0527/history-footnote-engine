"""v2.8.0 段一 W3 单元测试

测试目标：
1. ChapterCoordinator.pre_step 首次初始化第 1 章
2. ChapterCoordinator 节点推进（每 4 回合）
3. ChapterCoordinator.maybe_settle 章节结算写入 chapter_history
4. DramaManager.evaluate_chapter 第 4 维度干预
5. DramaManager.get_chapter_pressure 压力摘要

约束：
- 不依赖 LLM
- 不影响现有 66 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.coordinator import ChapterCoordinator, NODES_ADVANCE_ROUNDS


# ============= 测试 1：Coordinator 首次初始化 =============

def test_V28_29_coordinator_pre_step_init_first_chapter():
    """Coordinator.pre_step 首次调用时初始化第 1 章"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
        drama_manager=None,
    )
    coord = ChapterCoordinator(state=state, chapter_facade=facade, drama_manager=None)

    coord.pre_step()
    cs = state.chapter_state
    assert cs.current_chapter == 1, f"期望初始化第 1 章，实际 {cs.current_chapter}"
    assert cs.current_node == 1
    assert cs.chapter_start_round == 1
    return True


def test_V28_30_coordinator_pre_step_idempotent():
    """Coordinator.pre_step 二次调用不会重复初始化"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    coord.pre_step()  # 首次
    state.round_number = 5
    coord.pre_step()  # 第二次：不应重新 init
    # chapter_start_round 应保持 1（首次 init 时的 round）
    assert state.chapter_state.chapter_start_round == 1
    return True


# ============= 测试 2：节点推进 =============

def test_V28_31_coordinator_node_advance():
    """Coordinator 每 4 回合推进一个节点"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    coord.pre_step()  # round 1: init, node=1
    assert state.chapter_state.current_node == 1

    state.round_number = 5  # 第 5 回合：节点 2
    coord.pre_step()
    assert state.chapter_state.current_node == 2, f"期望 node=2，实际 {state.chapter_state.current_node}"

    state.round_number = 9  # 第 9 回合：节点 3
    coord.pre_step()
    assert state.chapter_state.current_node == 3, f"期望 node=3，实际 {state.chapter_state.current_node}"

    state.round_number = 13  # 第 13 回合：节点 4
    coord.pre_step()
    assert state.chapter_state.current_node == 4, f"期望 node=4，实际 {state.chapter_state.current_node}"
    return True


def test_V28_32_coordinator_node_advance_max_4():
    """Coordinator 节点最多推进到 4（不会超过）"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    coord.pre_step()  # init
    state.round_number = 25  # 远超 4 节点
    coord.pre_step()
    assert state.chapter_state.current_node == 4, f"节点不应超过 4，实际 {state.chapter_state.current_node}"
    return True


# ============= 测试 3：maybe_settle 章节结算 =============

def test_V28_33_coordinator_maybe_settle_soft_ready():
    """Coordinator.maybe_settle SOFT_READY 写入 chapter_history"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    coord.pre_step()  # init 第 1 章
    # 模拟 16 回合后到达 SOFT_READY
    state.chapter_state.current_node = 4
    state.round_number = 16
    coord.post_step()  # 写回 last_closure_status = SOFT_READY
    coord.maybe_settle()  # 触发结算

    # 验证 chapter_history 追加了 1 条
    history = state.chapter_state.chapter_history
    assert len(history) == 1, f"期望 1 条历史，实际 {len(history)}"
    assert history[0]["chapter"] == 1
    # 段二 W8：summary 基于 state 提取（不是硬编码），但 closure_status 字段标记结算类型
    assert history[0]["closure_status"] == "SOFT_READY", f"期望 SOFT_READY，实际 {history[0].get('closure_status')}"
    # 结算后 current_chapter 重置为 0
    assert state.chapter_state.current_chapter == 0
    return True


def test_V28_34_coordinator_maybe_settle_hard_forced():
    """Coordinator.maybe_settle HARD_FORCED 写入 chapter_history"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    coord.pre_step()
    # 模拟 17 回合：超时硬收束
    state.round_number = 17
    coord.post_step()  # HARD_FORCED
    coord.maybe_settle()

    history = state.chapter_state.chapter_history
    assert len(history) == 1
    assert history[0]["closure_status"] == "HARD_FORCED", f"期望 HARD_FORCED，实际 {history[0].get('closure_status')}"
    return True


def test_V28_35_coordinator_maybe_settle_no_action_when_continue():
    """Coordinator.maybe_settle CONTINUE 时不结算"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    coord.pre_step()
    state.round_number = 5  # 章节中段
    coord.post_step()  # CONTINUE
    coord.maybe_settle()

    # chapter_history 应保持空
    assert len(state.chapter_state.chapter_history) == 0
    return True


# ============= 测试 4：DramaManager 章节维度 =============

def test_V28_36_drama_evaluate_chapter_no_chapter():
    """DramaManager.evaluate_chapter 无章节时返回 None"""
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    drama = DramaManager(state, config={})
    result = drama.evaluate_chapter()
    assert result is None
    return True


def test_V28_37_drama_evaluate_chapter_node_stuck():
    """DramaManager.evaluate_chapter 节点停留过久返回干预"""
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2
    state.chapter_state.chapter_start_round = 1
    state.round_number = 9  # 节点 2 停留 5 回合（> 4 阈值）

    drama = DramaManager(state, config={})
    result = drama.evaluate_chapter()
    assert result is not None
    assert result.type == "CHAPTER_NODE_HINT"
    assert result.payload["current_node"] == 2
    return True


def test_V28_38_drama_evaluate_chapter_at_last_node():
    """DramaManager.evaluate_chapter 末节点不返回干预"""
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 4
    state.chapter_state.chapter_start_round = 1
    state.round_number = 20

    drama = DramaManager(state, config={})
    result = drama.evaluate_chapter()
    assert result is None
    return True


# ============= 测试 5：DramaManager.get_chapter_pressure =============

def test_V28_39_drama_get_chapter_pressure_active():
    """DramaManager.get_chapter_pressure 章节活跃时返回完整信息"""
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2
    state.chapter_state.chapter_start_round = 1
    state.round_number = 7

    drama = DramaManager(state, config={})
    pressure = drama.get_chapter_pressure()
    assert pressure["active"] is True
    assert pressure["current_chapter"] == 1
    assert pressure["current_node"] == 2
    assert pressure["rounds_in_chapter"] == 7
    assert pressure["rounds_in_node"] == 3  # 7 - 1*4
    assert pressure["pressure"] == "medium"  # 7 in (6, 12]
    return True


def test_V28_40_drama_get_chapter_pressure_inactive():
    """DramaManager.get_chapter_pressure 章节未激活"""
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    drama = DramaManager(state, config={})
    pressure = drama.get_chapter_pressure()
    assert pressure["active"] is False
    return True


# ============= 测试 6：完整生命周期（3 钩子串联） =============

def test_V28_41_coordinator_full_lifecycle_through_chapter():
    """Coordinator 完整生命周期：init → 节点推进 → 收束 → 结算"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    # 🆕 W32: 模拟 16 回合（4 节点 × 4 回合），但卡在第 1 章内
    # 因为只有 chapter 1 hardcoded blueprint 存在，chapter 2 不存在
    for r in range(1, 16):  # 12 回合够第 1 章 SOFT_READY 触发
        state.round_number = r
        coord.pre_step()  # 初始化 / 节点推进
        # 模拟 _run_round 完成
        coord.post_step()  # 收束检查
        coord.maybe_settle()  # 条件触发结算
        # 🆕 W32: 第 1 章完成就 break（不进入 chapter 2 因为 hardcoded 不存在）
        if state.chapter_state.chapter_history:
            break

    # 验证：第 1 章已结算
    history = state.chapter_state.chapter_history
    assert len(history) >= 1, f"期望 ≥1 章完成，实际 {len(history)}"
    # 节点 4 在 round 13 推进，停留 3 回合后在 round 15 触发 SOFT_READY
    assert history[0]["rounds_in_chapter"] == 15, f"期望 15 回合，实际 {history[0]['rounds_in_chapter']}"
    return True
