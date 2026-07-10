"""v2.8.0 段二 W9 单元测试

测试目标：
1. Coordinator 接收 llm_callable 参数
2. _init_chapter_via_llm 调 LLM → convert_llm_to_blueprint → 写入 state
3. LLM 失败回退到硬编码
4. _next_chapter_to_init 计算正确
5. 端到端：mock LLM + 16 回合走完第 1 章

约束：
- mock LLM（不真打）
- 不影响现有 126 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def make_test_era_config() -> dict:
    return {
        "npcs": {
            "npc_zhao_lizhang": {"name": "赵里长"},
            "npc_wang_sao": {"name": "王二嫂"},
            "fm_wife": {"name": "沈氏"},
        },
        "knowledge": {
            "entries": [
                {"id": "kn_silk_price_1587_spring"},
                {"id": "kn_tax_pressure_wanli"},
            ],
        },
        "narrative": {
            "hero_journey_acts": [
                {"act": "departure", "chapters": [1, 2, 3], "chapter_roles": ["ordinary", "call", "threshold"], "emotion_tone": "unease→resolve", "choice_type": "whether_to_step_out"},
            ],
        },
    }


# ============= 测试 1：Coordinator 接收 llm_callable =============

def test_V28_89_coordinator_accepts_llm_callable():
    """Coordinator __init__ 接受 llm_callable 参数"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    # 不传 llm_callable
    coord1 = ChapterCoordinator(state=state, chapter_facade=facade)
    assert coord1._llm is None

    # 传 llm_callable
    def mock_llm(prompt): return {}
    coord2 = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=mock_llm)
    assert coord2._llm is mock_llm
    return True


# ============= 测试 2：_init_chapter_via_llm 调 LLM =============

def test_V28_90_coordinator_via_llm_writes_state():
    """Coordinator 走 LLM 路径写入 state"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(
        state=state,
        era_config=make_test_era_config(),
        root_dir=Path(__file__).parent.parent,
    )

    def mock_llm(prompt):
        return {
            "chapter_title": "且听下回分解 · LLM 写的春蚕",
            "nodes": [
                {"role": "introduction", "scene": "盛泽春市", "npc_ids": ["fm_wife"], "option_directions": [{"text": "x", "path": "main_tax_resistance"}]},
                {"role": "escalation", "scene": "春税下来", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "climax", "scene": "赵里长催税", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "resolution", "scene": "春蚕上簇", "npc_ids": ["fm_wife"]},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=mock_llm)
    coord.pre_step()

    cs = state.chapter_state
    assert cs.current_chapter == 1
    assert "LLM 写的春蚕" in cs.blueprint.get("chapter_title", "")
    # meta 应从元属性规则引擎读
    assert cs.blueprint.get("meta", {}).get("act") == "departure"
    return True


# ============= 测试 3：LLM 失败回退硬编码 =============

def test_V28_91_coordinator_llm_failure_falls_back_to_hardcoded():
    """LLM 抛异常时回退到硬编码"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    def failing_llm(prompt):
        raise RuntimeError("LLM 服务挂了")

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=failing_llm)
    coord.pre_step()

    cs = state.chapter_state
    # 仍应初始化成功（用硬编码）
    assert cs.current_chapter == 1
    assert "春蚕" in cs.blueprint.get("chapter_title", "")
    return True


# ============= 测试 4：_next_chapter_to_init =============

def test_V28_92_coordinator_next_chapter_to_init():
    """_next_chapter_to_init 计算正确"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    # 无 history → 1
    assert coord._next_chapter_to_init() == 1

    # 有 1 章 history → 2
    state.chapter_state.chapter_history = [{"chapter": 1, "summary": "test"}]
    assert coord._next_chapter_to_init() == 2

    # 有 3 章 history → 4
    state.chapter_state.chapter_history = [
        {"chapter": 1, "summary": "t1"},
        {"chapter": 2, "summary": "t2"},
        {"chapter": 3, "summary": "t3"},
    ]
    assert coord._next_chapter_to_init() == 4
    return True


# ============= 测试 5：端到端 =============

def test_V28_93_end_to_end_via_mock_llm():
    """端到端：mock LLM + Coordinator 跑 16 回合"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.event_log = [{"summary": "test event"}]
    state.last_voice_options = [{"text": "test choice"}]
    state.value_dimensions = {"尽责": 0.7}

    facade = ChapterFacade(
        state=state,
        era_config=make_test_era_config(),
        root_dir=Path(__file__).parent.parent,
    )

    call_count = [0]
    def mock_llm(prompt):
        call_count[0] += 1
        return {
            "chapter_title": f"LLM 生成的第 1 章（调用 {call_count[0]} 次）",
            "nodes": [
                {"role": "introduction", "scene": "intro", "npc_ids": ["fm_wife"]},
                {"role": "escalation", "scene": "esc", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "climax", "scene": "climax", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "resolution", "scene": "res", "npc_ids": ["fm_wife"]},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=mock_llm)

    # 跑 16 回合
    for r in range(1, 17):
        state.round_number = r
        coord.pre_step()
        coord.post_step()
        coord.maybe_settle()
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) > 0:
            break

    # 验证 LLM 至少被调用 1 次
    assert call_count[0] >= 1, f"LLM 应至少被调用 1 次，实际 {call_count[0]}"
    # 验证 chapter_history 写入完整记录
    history = state.chapter_state.chapter_history
    assert len(history) == 1
    record = history[0]
    assert "core_event" in record
    assert "key_choice" in record
    assert "build_summary" in record
    return True


def test_V28_94_facade_build_prompt_called_by_coordinator():
    """Coordinator 调 LLM 之前先调 build_prompt_context"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)

    received_prompt = [None]
    def capturing_llm(prompt):
        received_prompt[0] = prompt
        return {
            "nodes": [
                {"role": "introduction"}, {"role": "escalation"},
                {"role": "climax"}, {"role": "resolution"},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=capturing_llm)
    coord.pre_step()

    # 验证 LLM 收到了完整的 prompt 上下文
    prompt = received_prompt[0]
    assert prompt is not None, "LLM 没收到 prompt"
    assert "chapter_meta" in prompt
    assert "focus_points" in prompt
    assert "chapter_history" in prompt
    return True
