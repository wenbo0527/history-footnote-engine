"""v2.8.0 段三 W13 单元测试

测试目标：
1. ChapterState.just_initialized 字段
2. facade.init_chapter 设置 just_initialized=True
3. _init_chapter_via_llm 设置 just_initialized=True
4. Coordinator post_step 跑 PathSwitcher
5. 端到端：30 回合跑 2 章 + 路径切换

约束：
- mock LLM
- 不影响现有 164 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def make_test_era_config() -> dict:
    return {
        "npcs": {
            "npc_zhao_lizhang": {"name": "赵里长"},
            "fm_wife": {"name": "沈氏"},
        },
        "knowledge": {"entries": []},
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
            ],
            "paths": [
                {
                    "id": "main_tax_resistance",
                    "type": "main",
                    "name": "赋税抗争",
                    "unlock_condition": "always",
                    "chapters_applicable": [2, 3, 4, 5, 6],
                },
                {
                    "id": "side_silk_trade",
                    "type": "side",
                    "name": "丝绸贸易",
                    "unlock_condition": "always",
                    "chapters_applicable": [2, 3, 4, 5, 6, 7],
                },
            ],
        },
    }


# ============= 测试 1：just_initialized 字段 =============

def test_V28_127_chapter_state_has_just_initialized():
    """ChapterState 有 just_initialized 字段（默认 False）"""
    from history_footnote.chapter.types import ChapterState
    cs = ChapterState()
    assert hasattr(cs, "just_initialized")
    assert cs.just_initialized is False
    return True


def test_V28_128_chapter_state_serialization_with_just_initialized():
    """ChapterState 序列化含 just_initialized"""
    from history_footnote.chapter.types import ChapterState
    cs = ChapterState(current_chapter=1, just_initialized=True)
    data = cs.to_dict()
    assert data["just_initialized"] is True
    cs2 = ChapterState.from_dict(data)
    assert cs2.just_initialized is True
    return True


# ============= 测试 2：facade.init_chapter 设置标记 =============

def test_V28_129_facade_init_chapter_sets_just_initialized():
    """ChapterFacade.init_chapter 设置 just_initialized=True"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)

    # 初始化前
    assert state.chapter_state.just_initialized is False
    facade.init_chapter(1)
    # 初始化后
    assert state.chapter_state.just_initialized is True
    return True


# ============= 测试 3：Coordinator _init_chapter_via_llm 设置标记 =============

def test_V28_130_coordinator_llm_init_sets_just_initialized():
    """Coordinator LLM 路径设置 just_initialized=True"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)

    def mock_llm(prompt):
        return {
            "nodes": [
                {"role": "introduction", "npc_ids": ["fm_wife"]},
                {"role": "escalation", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "climax", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "resolution", "npc_ids": ["fm_wife"]},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=mock_llm)
    coord.pre_step()  # 触发 init
    assert state.chapter_state.just_initialized is True
    return True


# ============= 测试 4：Coordinator post_step 跑 PathSwitcher + 清空标记 =============

def test_V28_131_coordinator_post_step_clears_just_initialized():
    """Coordinator.post_step 清空 just_initialized"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    facade.init_chapter(1)
    assert state.chapter_state.just_initialized is True
    coord.post_step()
    assert state.chapter_state.just_initialized is False
    return True


def test_V28_132_coordinator_post_step_runs_path_switcher():
    """Coordinator.post_step 跑 PathSwitcher 触发 UNLOCK"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    # 玩家已满足解锁条件
    state.value_dimensions = {"尽责": 0.8}
    state.path_state.locked_paths = ["side_silk_trade"]  # 但这个是 always，应不在 locked
    # 改：用一个 value_threshold 路径
    era_config = make_test_era_config()
    era_config["narrative"]["paths"].append({
        "id": "value_path",
        "type": "side",
        "name": "价值路径",
        "unlock_condition": "value_threshold",
        "chapters_applicable": [1, 2, 3, 4, 5, 6],
    })
    state.path_state.locked_paths = ["value_path"]

    facade = ChapterFacade(state=state, era_config=era_config, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    facade.init_chapter(1)
    # 初始化后 locked_paths 应仍含 value_path
    assert "value_path" in state.path_state.locked_paths
    coord.post_step()  # 跑 PathSwitcher
    # value_path 应被 UNLOCK → active
    assert "value_path" in state.path_state.active_paths
    assert "value_path" not in state.path_state.locked_paths
    return True


# ============= 测试 5：端到端 =============

def test_V28_133_end_to_end_multi_chapter_with_path_switching():
    """30 回合跑 2 章 + 路径解锁（chapter 2 适用路径与 chapter 1 不同）"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.value_dimensions = {"尽责": 0.7}

    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)

    def mock_llm(prompt):
        return {
            "nodes": [
                {"role": "introduction", "npc_ids": ["fm_wife"]},
                {"role": "escalation", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "climax", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "resolution", "npc_ids": ["fm_wife"]},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=mock_llm)

    # 跑 30 回合
    chapter_count = 0
    for r in range(1, 31):
        state.round_number = r
        coord.pre_step()
        coord.post_step()
        coord.maybe_settle()
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) > chapter_count:
            chapter_count = len(state.chapter_state.chapter_history)
            if chapter_count < 2:
                coord._initialized = False
            else:
                break

    # 验证 2 章完成
    assert len(state.chapter_state.chapter_history) == 2

    # 验证 just_initialized 已被清空（每回合 post_step 都清）
    assert state.chapter_state.just_initialized is False

    # 验证 main_tax_resistance 路径应在 active（always 路径）
    assert "main_tax_resistance" in state.path_state.active_paths
    return True


def test_V28_134_consecutive_choices_switch_main_path():
    """连续 3 次同选项 → 主路径切换"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.path_state.main_path_focus = "main_tax_resistance"
    state.path_state.active_paths = ["main_tax_resistance", "side_silk_trade"]

    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    # 用 LLM 路径 init（避免 chapter2_blueprint.json 不存在）
    def mock_llm(prompt):
        return {
            "nodes": [
                {"role": "introduction"}, {"role": "escalation"},
                {"role": "climax"}, {"role": "resolution"},
            ],
        }
    coord._llm = mock_llm
    coord._init_chapter_via_llm(2)

    # 手动设置 recent_path_choices
    state.recent_path_choices = ["side_silk_trade", "side_silk_trade", "side_silk_trade"]
    coord.post_step()

    # 主路径应切换到 side_silk_trade
    assert state.path_state.main_path_focus == "side_silk_trade"
    return True
