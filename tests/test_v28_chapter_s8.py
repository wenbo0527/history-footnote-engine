"""v2.8.0 段二 W8 单元测试

测试目标：
1. ChapterSettlement 4 必填项提取
2. Mock LLM 模式生成摘要
3. 真 LLM 模式（mock function）触发
4. 摘要长度 < 200 字
5. Coordinator.maybe_settle 接入 Settlement

约束：
- 0 真 LLM 调用
- 不影响现有 118 测试
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.settlement import (
    ChapterSettlement,
    settle_chapter,
    MAX_SUMMARY_LENGTH,
    REQUIRED_FIELDS,
)


# ============= 测试 1：4 必填项提取 =============

def test_V28_81_settlement_extracts_4_required_fields():
    """Settlement 提取 4 必填项"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.chapter_start_round = 1
    state.round_number = 16
    state.chapter_state.blueprint = {"transition_hint": "season"}
    state.event_log = [{"summary": "玩家被催税"}]
    state.last_voice_options = [{"text": "抗税"}]
    state.value_dimensions = {"守旧": 0.5, "尽责": 0.7}

    settlement = ChapterSettlement(state)
    record = settlement.settle(closure_status="SOFT_READY")

    assert record["chapter"] == 1
    for field in REQUIRED_FIELDS:
        assert field in record, f"必填项缺失: {field}"
    assert "抗税" in record["key_choice"] or record["key_choice"] == "无显著选择"
    assert "尽责" in record["build_summary"] or record["build_summary"] == "Build 画像不显著"
    return True


# ============= 测试 2：Mock LLM 模式生成摘要 =============

def test_V28_82_settlement_mock_summary_under_200_chars():
    """Mock 模式生成的摘要 < 200 字"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.chapter_start_round = 1
    state.round_number = 16
    state.chapter_state.blueprint = {"transition_hint": "season"}
    state.event_log = [{"summary": "玩家被催税"}]
    state.last_voice_options = [{"text": "抗税"}]
    state.value_dimensions = {"尽责": 0.7}

    settlement = ChapterSettlement(state)
    record = settlement.settle()
    assert len(record["summary"]) <= MAX_SUMMARY_LENGTH, \
        f"summary 超过 {MAX_SUMMARY_LENGTH} 字: {len(record['summary'])}"
    return True


# ============= 测试 3：真 LLM 模式（注入 mock function） =============

def test_V28_83_settlement_uses_injected_llm():
    """注入 LLM callable 时使用真 LLM 模式"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.chapter_start_round = 1
    state.round_number = 16
    state.chapter_state.blueprint = {"transition_hint": "season"}
    state.event_log = [{"summary": "test"}]
    state.last_voice_options = [{"text": "test"}]
    state.value_dimensions = {"尽责": 0.7}

    # 注入 mock LLM
    def mock_llm(prompt: str) -> str:
        return "LLM 生成的摘要（短）"

    settlement = ChapterSettlement(state, llm_callable=mock_llm)
    record = settlement.settle()
    assert record["summary"] == "LLM 生成的摘要（短）", \
        f"期望用 LLM 输出，实际: {record['summary']}"
    return True


def test_V28_84_settlement_llm_failure_falls_back_to_rule():
    """LLM 抛异常时回退到规则压缩"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.chapter_start_round = 1
    state.round_number = 16
    state.chapter_state.blueprint = {"transition_hint": "season"}
    state.event_log = [{"summary": "test"}]
    state.last_voice_options = [{"text": "test"}]
    state.value_dimensions = {"尽责": 0.7}

    def failing_llm(prompt: str) -> str:
        raise RuntimeError("LLM 调用失败")

    settlement = ChapterSettlement(state, llm_callable=failing_llm)
    record = settlement.settle()
    # 规则压缩的 summary 不为空
    assert record["summary"]
    assert "事件" in record["summary"] or "选择" in record["summary"] or "画像" in record["summary"]
    return True


# ============= 测试 4：摘要内容完整性 =============

def test_V28_85_settlement_summary_includes_event():
    """摘要包含核心事件"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.chapter_start_round = 1
    state.round_number = 16
    state.chapter_state.blueprint = {"transition_hint": "season"}
    state.event_log = [{"summary": "玩家抗税成功"}]
    state.last_voice_options = []
    state.value_dimensions = {}

    settlement = ChapterSettlement(state)
    record = settlement.settle()
    assert "抗税" in record["summary"] or "事件" in record["summary"]
    return True


def test_V28_86_settlement_handles_empty_state():
    """Settlement 处理空 state（不抛异常）"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.current_chapter = 1
    state.chapter_state.chapter_start_round = 1
    state.round_number = 16
    state.chapter_state.blueprint = {"transition_hint": "season"}
    # event_log / last_voice_options / value_dimensions 全空

    settlement = ChapterSettlement(state)
    record = settlement.settle()
    # 4 必填项都有值（即使是"无显著"占位）
    for field in REQUIRED_FIELDS:
        assert record.get(field), f"必填项为空: {field}"
    return True


# ============= 测试 5：Coordinator 接入 Settlement =============

def test_V28_87_coordinator_maybe_settle_uses_settlement():
    """Coordinator.maybe_settle 用 Settlement 生成完整记录"""
    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.round_number = 1
    state.event_log = [{"summary": "春蚕上市"}]
    state.last_voice_options = [{"text": "抗税"}]
    state.value_dimensions = {"尽责": 0.7}
    facade = ChapterFacade(state=state, era_config={}, root_dir=Path(__file__).parent.parent)
    coord = ChapterCoordinator(state=state, chapter_facade=facade)

    # 跑完第 1 章
    for r in range(1, 16):
        state.round_number = r
        coord.pre_step()
        coord.post_step()
        coord.maybe_settle()
        if state.chapter_state.current_chapter == 0:
            break

    # 验证 chapter_history 写入完整记录
    history = state.chapter_state.chapter_history
    assert len(history) == 1
    record = history[0]
    # 4 必填项都在
    for field in REQUIRED_FIELDS:
        assert field in record, f"Coordinator 写入缺字段: {field}"
    # summary 包含事件关键词
    assert "春蚕" in record["summary"] or "抗税" in record["summary"], \
        f"summary 缺核心信息: {record['summary']}"
    return True


def test_V28_88_settlement_validate_required_fields():
    """Settlement 校验 4 必填项"""
    from history_footnote.chapter.settlement import ChapterSettlement
    # 必填项都在 REQUIRED_FIELDS 常量中
    assert "core_event" in REQUIRED_FIELDS
    assert "key_choice" in REQUIRED_FIELDS
    assert "build_summary" in REQUIRED_FIELDS
    assert "path_summary" in REQUIRED_FIELDS
    assert len(REQUIRED_FIELDS) == 4
    return True
