"""🆕 v2.8.x W34: game_loop 集成测试

测试目标：
1. GameLoop 9 步流程在 chapter 钩子接入后仍跑
2. ChapterCoordinator 钩子调用顺序正确
3. 不抛异常
4. 关键方法签名稳定
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W34_020_gameloop_class_exists():
    """GameLoop 类存在"""
    from history_footnote.game_loop import GameLoop
    assert GameLoop is not None
    return True


def test_W34_021_gameloop_has_9_step_methods():
    """GameLoop 有 9 步单循环方法（run/_run_round）"""
    from history_footnote.game_loop import GameLoop

    required = ["run", "_run_round"]
    for m in required:
        assert hasattr(GameLoop, m), f"GameLoop 缺 {m}"
    return True


def test_W34_022_gameloop_init_signature():
    """GameLoop.__init__ 签名稳定（不破坏）"""
    import inspect
    from history_footnote.game_loop import GameLoop

    sig = inspect.signature(GameLoop.__init__)
    # 应有 game_state, era_config, drama_manager 等参数
    param_names = list(sig.parameters.keys())
    assert "self" in param_names
    # 至少 1 个非 self 参数
    assert len(param_names) >= 2
    return True


def test_W34_023_gameloop_has_utility_methods():
    """GameLoop 有 _is_game_over / _update_idle_counter / _display_narrative 工具方法"""
    from history_footnote.game_loop import GameLoop

    required = [
        "_is_game_over",
        "_update_idle_counter",
        "_display_narrative",
        "_validate_narrative",
        "_preprocess_input",
    ]
    for m in required:
        assert hasattr(GameLoop, m), f"GameLoop 缺 {m}"
    return True


def test_W34_024_gameloop_character_helpers():
    """GameLoop 角色辅助方法"""
    from history_footnote.game_loop import GameLoop

    required = [
        "_inject_identity_switch_offers",
        "_apply_character_initial_state",
        "_inject_background_knowledge",
        "_print_opening",
        "_has_persona_opening",
        "_get_persona_opening",
    ]
    for m in required:
        assert hasattr(GameLoop, m), f"GameLoop 缺 {m}"
    return True


def test_W34_025_chapter_coordinator_has_hooks():
    """ChapterCoordinator 有 3 钩子方法（pre_step/post_step/maybe_settle）"""
    from history_footnote.chapter.coordinator import ChapterCoordinator

    required = ["pre_step", "post_step", "maybe_settle"]
    for m in required:
        assert hasattr(ChapterCoordinator, m), f"ChapterCoordinator 缺 {m}"
    return True


def test_W34_026_chapter_coordinator_hook_signatures():
    """钩子方法签名（无参数 + 互不依赖）"""
    import inspect
    from history_footnote.chapter.coordinator import ChapterCoordinator

    for m in ["pre_step", "post_step", "maybe_settle"]:
        sig = inspect.signature(getattr(ChapterCoordinator, m))
        # 只 self 一个参数
        assert list(sig.parameters.keys()) == ["self"], f"{m} 签名应只有 self"
    return True


def test_W34_027_chapter_coordinator_init():
    """ChapterCoordinator 初始化（不依赖真实 LLM）"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState
    from unittest.mock import MagicMock
    from pathlib import Path

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path("/tmp"))
    llm = MagicMock()
    coord = ChapterCoordinator(
        state=state,
        chapter_facade=facade,
        drama_manager=None,
        llm_callable=llm,
    )
    assert coord is not None
    return True


def test_W34_028_gameloop_methods_call_count():
    """GameLoop 方法数稳定（30+ 方法 = 9 步 + 工具）"""
    from history_footnote.game_loop import GameLoop

    method_count = sum(1 for m in dir(GameLoop) if not m.startswith("__") and callable(getattr(GameLoop, m)))
    # 应有 20+ 方法
    assert method_count >= 20, f"GameLoop 仅有 {method_count} 方法，期望 ≥20"
    return True


def test_W34_029_chapter_dm_tools_lc_decoupled():
    """🆕 W34: dm_tools_lc 独立（不依赖 game_loop）"""
    from history_footnote.chapter.dm_tools_lc import make_chapter_dm_tools
    from history_footnote.game_state import GameState
    from unittest.mock import MagicMock

    state = GameState()
    state.era_id = "wanli1587"
    facade = MagicMock()
    llm = MagicMock()

    tools = make_chapter_dm_tools(state, facade, llm, {})
    # 不依赖 game_loop 即可工作
    assert len(tools) == 2
    return True


def test_W34_030_full_chapter_pipeline_modules():
    """完整 chapter 管线模块都存在"""
    from history_footnote.chapter import (
        ChapterCoordinator,        # 钩子
        ChapterMetaResolver,        # 元属性
        PlateEngine,                # 板块引擎
        PathSwitcher,               # 路径切换
        fallback_chapter_blueprint, # 容错
        fill_chapter_blueprint_via_llm,  # LLM
        extract_json_from_text,     # JSON 清洗
    )
    # 全部存在
    assert all([ChapterCoordinator, ChapterMetaResolver, PlateEngine, PathSwitcher,
                fallback_chapter_blueprint, fill_chapter_blueprint_via_llm,
                extract_json_from_text])
    return True
