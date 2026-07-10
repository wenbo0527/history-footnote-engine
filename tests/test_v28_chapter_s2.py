"""v2.8.0 段一 W2 单元测试

测试目标：
1. ChapterClosure 4 种状态判定正确
2. ChapterClosure 复用 DramaManager 维度（emotion_state）
3. ChapterFacade 蓝图加载、初始化、查询
4. GameEngineFacade.sub_facades["chapter"] 可访问
5. 集成测试：完整章节生命周期（初始化→游玩→收束→结算）

约束：
- 不依赖 LLM
- 不影响现有 53 测试
"""
import sys
from pathlib import Path

# 让 pytest 能 import src/history_footnote
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.closure import (
    ChapterClosure,
    DEFAULT_NODES_PER_CHAPTER,
    DEFAULT_ROUNDS_PER_NODE,
    SOFT_CLOSURE_MIN_ROUNDS,
    HARD_CLOSURE_MAX_ROUNDS,
    DISTRESSED_EARLY_CLOSURE,
)
from history_footnote.chapter.types import ChapterState


# ============= 测试 1：ChapterClosure 4 种状态 =============

def test_V28_16_closure_init_state():
    """未初始化章节 → INIT"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.chapter_state.current_chapter = 0

    closure = ChapterClosure(state, drama_manager=None)
    assert closure.check() == "INIT"
    return True


def test_V28_17_closure_continue_state():
    """章节中段 → CONTINUE"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2
    state.chapter_state.chapter_start_round = 1
    state.round_number = 6  # 章节第 6 回合

    closure = ChapterClosure(state, drama_manager=None)
    assert closure.check() == "CONTINUE"
    return True


def test_V28_18_closure_soft_ready():
    """节点 4 + 停留 ≥ 3 回合 → SOFT_READY"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 4  # 最后一个节点
    state.chapter_state.chapter_start_round = 1
    state.round_number = 15  # 节点 4 从第 13 回合开始，到第 15 回合停留 3 回合

    closure = ChapterClosure(state, drama_manager=None)
    status = closure.check()
    assert status == "SOFT_READY", f"期望 SOFT_READY，实际 {status}"
    return True


def test_V28_19_closure_hard_forced_timeout():
    """16 回合还没收束 → HARD_FORCED"""
    from history_footnote.game_state import GameState
    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2  # 还在第 2 节点
    state.chapter_state.chapter_start_round = 1
    state.round_number = 17  # 超过 16 回合硬收束

    closure = ChapterClosure(state, drama_manager=None)
    status = closure.check()
    assert status == "HARD_FORCED", f"期望 HARD_FORCED，实际 {status}"
    return True


def test_V28_20_closure_hard_forced_distressed():
    """drama_manager 判定 distressed + 章节过半 → HARD_FORCED"""
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager, PlayerModel

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2
    state.chapter_state.chapter_start_round = 1
    state.round_number = 11  # 超过 DISTRESSED_EARLY_CLOSURE(10)

    # 构造 drama_manager 模拟 distressed
    drama = DramaManager(state, config={})
    drama.player_model.emotion_state = "distressed"

    closure = ChapterClosure(state, drama_manager=drama)
    status = closure.check()
    assert status == "HARD_FORCED", f"期望 HARD_FORCED，实际 {status}"
    return True


# ============= 测试 2：ChapterFacade 关键方法 =============

def test_V28_21_facade_load_blueprint():
    """ChapterFacade.load_blueprint 加载第 1 章蓝图"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
        drama_manager=None,
    )
    blueprint = facade.load_blueprint(1)
    assert blueprint.chapter_id == 1
    assert "春蚕" in blueprint.chapter_title
    return True


def test_V28_22_facade_init_chapter():
    """ChapterFacade.init_chapter 设置 chapter_state"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 5
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
        drama_manager=None,
    )
    blueprint = facade.init_chapter(1)
    cs = state.chapter_state
    assert cs.current_chapter == 1
    assert cs.current_node == 1
    assert cs.chapter_start_round == 5
    assert cs.last_closure_status == "INIT"
    assert cs.blueprint is not None
    return True


def test_V28_23_facade_get_chapter_info():
    """ChapterFacade.get_chapter_info 返回正确信息"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
        drama_manager=None,
    )
    facade.init_chapter(1)
    info = facade.get_chapter_info()
    assert info["current_chapter"] == 1
    assert info["current_node"] == 1
    assert info["total_nodes"] == 4
    assert "春蚕" in info["chapter_title"]
    return True


def test_V28_24_facade_get_progress_text():
    """ChapterFacade.get_progress_text 格式化文本"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
        drama_manager=None,
    )
    facade.init_chapter(1)
    state.chapter_state.current_node = 2
    text = facade.get_progress_text()
    assert "第 1 章" in text
    assert "节点 2/4" in text
    return True


def test_V28_25_facade_blueprint_not_exists():
    """ChapterFacade.load_blueprint 文件不存在抛 FileNotFoundError"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
        drama_manager=None,
    )
    try:
        facade.load_blueprint(99)
        assert False, "应该抛 FileNotFoundError"
    except FileNotFoundError:
        pass
    return True


# ============= 测试 3：GameEngineFacade 集成 =============

def test_V28_26_game_engine_facade_has_chapter_subfacade():
    """GameEngineFacade.sub_facades["chapter"] 可访问"""
    from history_footnote.game_engine_facade import GameEngineFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = GameEngineFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
    )
    sub = facade.sub_facades
    assert "chapter" in sub, f"sub_facades 缺 chapter: keys={list(sub.keys())}"
    return True


# ============= 测试 4：完整生命周期集成 =============

def test_V28_27_full_chapter_lifecycle():
    """完整章节生命周期：初始化→游玩→收束"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    drama = DramaManager(state, config={})
    facade = ChapterFacade(
        state=state,
        era_config={},
        root_dir=Path(__file__).parent.parent,
        drama_manager=drama,
    )

    # 1. 初始化
    facade.init_chapter(1)
    assert state.chapter_state.current_chapter == 1
    assert facade.check_closure() == "INIT"  # 刚初始化

    # 2. 章节初期：CONTINUE
    state.round_number = 3
    assert facade.check_closure() == "CONTINUE"

    # 3. 推进到节点 4
    state.chapter_state.current_node = 4
    state.round_number = 14
    assert facade.check_closure() == "CONTINUE"  # 节点 4 刚到，停留不到 3 回合

    # 4. 节点 4 停留 3 回合：SOFT_READY
    state.round_number = 16
    status = facade.check_closure()
    assert status == "SOFT_READY", f"期望 SOFT_READY，实际 {status}"
    return True


def test_V28_28_facade_closure_laziness():
    """ChapterFacade.closure 懒加载（drama_manager 后注入也能工作）"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    state.era_id = "wanli1587"
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2
    state.chapter_state.chapter_start_round = 1
    state.round_number = 12  # 超过 DISTRESSED_EARLY_CLOSURE

    # 先不传 drama_manager
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    # 第一次 check（无 drama）→ CONTINUE（drama 缺失不触发 distressed 分支）
    assert facade.check_closure() == "CONTINUE"

    # 后注入 drama_manager
    drama = DramaManager(state, config={})
    drama.player_model.emotion_state = "distressed"
    facade.drama_manager = drama

    # 第二次 check（有 drama）→ HARD_FORCED
    assert facade.check_closure() == "HARD_FORCED"
    return True
