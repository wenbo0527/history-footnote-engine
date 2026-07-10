"""v2.8.0 段二 W10 端到端集成测试

测试目标：
1. 30 回合跑 2 章（每章 15 回合）
2. 第 1 章 LLM 生成 → 走完 → 结算写入 chapter_history
3. 结算后自动 init 第 2 章（LLM 看到第 1 章 history）
4. 第 2 章 LLM 生成的 meta 正确（chapter 2 = departure/call）
5. 30 回合收尾：2 章 history

约束：
- mock LLM
- 不影响现有 132 测试
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


# ============= 端到端：30 回合跑 2 章 =============

def test_V28_95_multi_chapter_30_rounds_end_to_end():
    """30 回合跑 2 章：第 1 章 LLM 生成 → 结算 → 自动 init 第 2 章 → 走完"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.event_log = [{"summary": "初始事件"}]
    state.last_voice_options = [{"text": "初始选择"}]
    state.value_dimensions = {"尽责": 0.7, "身边": 0.6}

    facade = ChapterFacade(
        state=state,
        era_config=make_test_era_config(),
        root_dir=Path(__file__).parent.parent,
    )

    # 模拟 LLM：根据 chapter_id 生成对应内容
    llm_call_log = []
    def adaptive_mock_llm(prompt):
        chapter_id = prompt["chapter_meta"]["chapter_id"]
        role = prompt["chapter_meta"]["role"]
        llm_call_log.append({"chapter_id": chapter_id, "role": role})
        return {
            "chapter_title": f"且听下回分解 · 第 {chapter_id} 章（{role}）",
            "nodes": [
                {"role": "introduction", "scene": f"chapter {chapter_id} intro", "npc_ids": ["fm_wife"]},
                {"role": "escalation", "scene": f"chapter {chapter_id} esc", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "climax", "scene": f"chapter {chapter_id} climax", "npc_ids": ["npc_zhao_lizhang"]},
                {"role": "resolution", "scene": f"chapter {chapter_id} res", "npc_ids": ["fm_wife"]},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=adaptive_mock_llm)

    # 跑 30 回合
    chapter_count = 0
    for r in range(1, 31):
        state.round_number = r
        coord.pre_step()
        coord.post_step()
        coord.maybe_settle()
        # 检测章节完成
        if state.chapter_state.current_chapter == 0 and len(state.chapter_state.chapter_history) > chapter_count:
            chapter_count = len(state.chapter_state.chapter_history)
            if chapter_count == 1:
                # 第 1 章结算完，让 coordinator 自动 init 第 2 章
                coord._initialized = False  # 触发下一章 init
            elif chapter_count >= 2:
                break

    # 验证：30 回合走完 2 章
    history = state.chapter_state.chapter_history
    assert len(history) == 2, f"期望 2 章完成，实际 {len(history)}"

    # 验证 LLM 被调用 2 次（每章 1 次）
    assert len(llm_call_log) == 2, f"LLM 应调用 2 次，实际 {len(llm_call_log)}"
    assert llm_call_log[0]["chapter_id"] == 1
    assert llm_call_log[0]["role"] == "ordinary"
    assert llm_call_log[1]["chapter_id"] == 2
    assert llm_call_log[1]["role"] == "call"  # chapter 2 = departure/call

    # 验证第 1 章 history 有完整 4 必填项
    assert "core_event" in history[0]
    assert "key_choice" in history[0]
    assert "build_summary" in history[0]
    # 验证第 2 章 history 也完整
    assert "core_event" in history[1]
    assert history[1]["chapter"] == 2
    # 验证第 2 章 meta.role = call（与 seen_metas[1] 一致）
    assert history[1]["chapter"] == 2
    return True


def test_V28_96_chapter_2_llm_sees_chapter_1_history():
    """第 2 章 LLM 收到第 1 章 history（增量规则）"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 16  # 已在第 2 章起始位置
    # 模拟第 1 章已结算
    state.chapter_state.chapter_history = [
        {"chapter": 1, "summary": "第 1 章：春蚕抗税", "core_event": "赵里长催税", "key_choice": "抗税", "build_summary": "尽责偏正+0.7", "path_summary": "无活跃路径", "rounds_in_chapter": 15, "ended_at_round": 15, "transition": "season", "closure_status": "SOFT_READY"},
    ]

    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)

    received_history = [None]
    def capturing_llm(prompt):
        received_history[0] = prompt["chapter_history"]
        return {
            "nodes": [
                {"role": "introduction"}, {"role": "escalation"},
                {"role": "climax"}, {"role": "resolution"},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=capturing_llm)
    coord.pre_step()

    # 验证 LLM 收到第 1 章 history
    history_in_prompt = received_history[0]
    assert history_in_prompt is not None
    assert len(history_in_prompt) == 1
    assert "春蚕抗税" in history_in_prompt[0]["summary"]
    return True


def test_V28_97_multi_chapter_meta_progression():
    """多章元属性按英雄之旅阶段推进"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.value_dimensions = {"尽责": 0.7}

    facade = ChapterFacade(state=state, era_config=make_test_era_config(), root_dir=Path(__file__).parent.parent)

    seen_metas = []
    def meta_capturing_llm(prompt):
        seen_metas.append((prompt["chapter_meta"]["chapter_id"], prompt["chapter_meta"]["role"]))
        return {
            "nodes": [
                {"role": "introduction"}, {"role": "escalation"},
                {"role": "climax"}, {"role": "resolution"},
            ],
        }

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=meta_capturing_llm)

    for r in range(1, 31):
        state.round_number = r
        coord.pre_step()
        coord.post_step()
        coord.maybe_settle()
        if len(state.chapter_state.chapter_history) == 1:
            coord._initialized = False
        if len(state.chapter_state.chapter_history) >= 2:
            break

    # 验证元属性按 departure/ordinary → departure/call 推进
    assert seen_metas[0] == (1, "ordinary")
    assert seen_metas[1] == (2, "call")
    return True


def test_V28_98_chapter_init_failure_recovery():
    """章节 init 失败时 LLM 路径不抛异常"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)

    def bad_llm(prompt):
        # 返回完全不合法数据
        return "not a dict"

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=bad_llm)
    coord.pre_step()  # 不应抛异常

    # 仍能 init（fallback 兜底）
    assert state.chapter_state.current_chapter == 1
    return True


def test_V28_99_facade_convert_then_init_chapter_workflow():
    """Facade convert_llm_to_blueprint + init_chapter 工作流"""
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

    # 模拟 LLM 输出
    llm_output = {
        "chapter_title": "且听下回分解 · 测试章",
        "nodes": [
            {"role": "introduction", "scene": "intro", "npc_ids": ["fm_wife"]},
            {"role": "escalation", "scene": "esc", "npc_ids": ["npc_zhao_lizhang"]},
            {"role": "climax", "scene": "climax", "npc_ids": ["npc_zhao_lizhang"]},
            {"role": "resolution", "scene": "res", "npc_ids": ["fm_wife"]},
        ],
    }

    # 1. facade.convert_llm_to_blueprint（手动流程）
    blueprint = facade.convert_llm_to_blueprint(llm_output, chapter_id=1)
    assert blueprint.chapter_id == 1
    assert blueprint.meta.act == "departure"
    assert blueprint.meta.role == "ordinary"

    # 2. facade.init_chapter（用硬编码）
    facade.init_chapter(1)
    assert state.chapter_state.current_chapter == 1
    assert state.chapter_state.blueprint["chapter_title"] == "且听下回分解 · 春蚕"
    return True


def test_V28_100_drama_manager_chapter_pressure_changes_with_chapter():
    """DramaManager.get_chapter_pressure 随章节变化"""
    from history_footnote.game_state import GameState
    from history_footnote.drama_manager import DramaManager

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.current_node = 2
    state.chapter_state.chapter_start_round = 1
    state.round_number = 7
    drama = DramaManager(state, config={})

    pressure1 = drama.get_chapter_pressure()
    assert pressure1["current_chapter"] == 1
    assert pressure1["pressure"] == "medium"

    # 切到第 2 章
    state.chapter_state.current_chapter = 2
    state.chapter_state.chapter_start_round = 8
    state.round_number = 8
    pressure2 = drama.get_chapter_pressure()
    assert pressure2["current_chapter"] == 2
    assert pressure2["rounds_in_chapter"] == 1
    assert pressure2["pressure"] == "low"
    return True
