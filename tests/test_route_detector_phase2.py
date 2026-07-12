"""v2.10.1 W85 · RouteDetector Phase 2 LLM 意图分类单元测试

依据 spec：docs/design/v2.10.1-W85-涌现式章节设计.md §3.1 + §6.1
测试目标：
1. LLM callable 注入
2. Phase 1 未触发时才调 LLM
3. LLM 字符串返回 → JSON 解析
4. LLM dict 返回 → 直接用
5. LLM 异常 → 不触发
6. LLM 返回非 5 类 → 忽略
7. 未预设路线识别

注意：所有玩家输入刻意避开 Phase 1 关键词表（投奔/海瑞/抗税/倭寇/皇帝/朝廷 等）
否则会被 Phase 1 抢先触发,Phase 2 LLM 不会被调用。
"""
import pytest

from history_footnote.chapter.route_detector import RouteDetector
from history_footnote.chapter.types import ChapterBlueprint


def _make_bp(position: str = "opening", chapter_id: int = 1, title: str = "春蚕", must_resolve: list = None) -> ChapterBlueprint:
    return ChapterBlueprint(
        chapter_id=chapter_id,
        chapter_title=title,
        narrative_position=position,
        must_resolve=must_resolve or [],
    )


# ============= 测试 1: llm_callable 注入 =============

def test_phase2_llm_injectable():
    """RouteDetector 应能接受 llm_callable 参数"""
    def my_llm(prompt, **kwargs):
        return '{"changed_conflict": false}'
    detector = RouteDetector(llm_callable=my_llm)
    assert detector.llm is my_llm


def test_phase2_llm_default_none():
    """默认 llm=None（向后兼容 Phase 1）"""
    detector = RouteDetector()
    assert detector.llm is None


# ============= 测试 2: Phase 1 优先,Phase 2 不调 LLM =============

def test_phase1_keyword_blocks_phase2_llm():
    """Phase 1 关键词触发时,不应调 LLM"""
    llm_called = []
    def llm(prompt, **kwargs):
        llm_called.append(prompt)
        return '{"changed_conflict": true}'
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    # 用关键词"抗税",Phase 1 触发
    result = detector.detect("我要抗税", {}, bp)
    assert result["route_change"] is True
    assert result["trigger"].startswith("keyword:")  # Phase 1 触发
    assert len(llm_called) == 0, "Phase 1 触发时不应调 LLM"


def test_phase1_value_shift_blocks_phase2_llm():
    """Phase 1 价值偏移触发时,不应调 LLM"""
    llm_called = []
    def llm(prompt, **kwargs):
        llm_called.append(prompt)
        return '{"changed_conflict": true}'
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    result = detector.detect("我去看看", {"trust": -0.8}, bp)
    assert result["route_change"] is True
    assert result["trigger"].startswith("value_shift:")
    assert len(llm_called) == 0


# ============= 测试 3: LLM 字符串返回 → JSON 解析 =============

def test_phase2_llm_string_return_parsed():
    """LLM 返回 JSON 字符串应被正确解析"""
    llm_response = '{"core_intent": "投靠苏州织工", "changed_conflict": true, "suggested_template": "rising_conflict", "confidence": 0.85, "reason": "玩家选择追随他人"}'
    def llm(prompt, **kwargs):
        return llm_response
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening", must_resolve=["抗税"])
    result = detector.detect("我要去投靠苏州织工", {}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"
    assert result["trigger"] == "llm_intent:投靠苏州织工"
    assert result["confidence"] == 0.85


def test_phase2_llm_markdown_wrapped_json():
    """LLM 返回 markdown 代码块包裹的 JSON,应能提取"""
    llm_response = '好的,分析结果如下:\n\n```json\n{"core_intent": "投靠苏州织工", "changed_conflict": true, "suggested_template": "rising_conflict", "confidence": 0.9, "reason": "追随他人"}\n```\n\n如有其他问题请告诉我。'
    def llm(prompt, **kwargs):
        return llm_response
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening", must_resolve=["抗税"])
    result = detector.detect("投靠苏州织工", {}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"


# ============= 测试 4: LLM dict 返回 → 直接用 =============

def test_phase2_llm_dict_return_direct():
    """LLM 直接返回 dict 时,RouteDetector 应直接用"""
    def llm(prompt, **kwargs):
        return {
            "core_intent": "反抗官府",
            "changed_conflict": True,
            "suggested_template": "crisis",
            "confidence": 0.92,
            "reason": "玩家激烈反抗",
        }
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("rising_conflict")
    # 输入不在关键词表（不是"抗税""告官""海瑞"等）
    result = detector.detect("我绝不屈服!", {}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "crisis"
    assert result["confidence"] == 0.92


# ============= 测试 5: LLM 返回 changed_conflict=false → 不触发 =============

def test_phase2_llm_says_no_change():
    """LLM 判定玩家行为未改变冲突时,不应触发路线变更"""
    def llm(prompt, **kwargs):
        return '{"changed_conflict": false, "reason": "日常闲聊"}'
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    result = detector.detect("今天天气真好", {}, bp)
    assert result["route_change"] is False
    assert result["suggested_template"] == "opening"


# ============= 测试 6: LLM 异常 → 不触发 =============

def test_phase2_llm_exception_safe():
    """LLM 调用异常时,RouteDetector 不应崩溃,且不触发路线变更"""
    def llm(prompt, **kwargs):
        raise RuntimeError("mock LLM 失败")
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    result = detector.detect("我去投靠苏州织工", {}, bp)
    assert result["route_change"] is False
    assert result["suggested_template"] == "opening"


def test_phase2_llm_invalid_json_safe():
    """LLM 返回非 JSON 字符串时,RouteDetector 不应崩溃"""
    def llm(prompt, **kwargs):
        return "这不是 JSON,只是普通文字"
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    result = detector.detect("我去投靠苏州织工", {}, bp)
    assert result["route_change"] is False


def test_phase2_llm_non_str_non_dict_safe():
    """LLM 返回非 str/dict 类型时,RouteDetector 不应崩溃"""
    def llm(prompt, **kwargs):
        return 12345  # 数字,不合理
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    result = detector.detect("我去投靠苏州织工", {}, bp)
    assert result["route_change"] is False


# ============= 测试 7: LLM 返回非 5 类 → 忽略 =============

def test_phase2_llm_invalid_template_ignored():
    """LLM 返回非 5 类的 template 时,RouteDetector 应忽略(安全检查)"""
    def llm(prompt, **kwargs):
        return '{"changed_conflict": true, "suggested_template": "invalid_template", "confidence": 0.9}'
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    result = detector.detect("我去投靠苏州织工", {}, bp)
    # 因 suggested_template 非法,应忽略 LLM 判断 → 不触发
    assert result["route_change"] is False


# ============= 测试 8: 5 类模板都能正确触发 =============

def test_phase2_llm_all_5_templates():
    """LLM 能返回 5 类模板的任意一种"""
    for template in ["opening", "rising_conflict", "crisis", "convergence", "resolution"]:
        def make_llm(t=template):
            def llm(prompt, **kwargs):
                return f'{{"changed_conflict": true, "suggested_template": "{t}", "confidence": 0.8}}'
            return llm
        detector = RouteDetector(llm_callable=make_llm())
        bp = _make_bp("opening")
        result = detector.detect("去做某事", {}, bp)
        assert result["route_change"] is True
        assert result["suggested_template"] == template, f"{template} 失败"


# ============= 测试 9: spec §6.1 用例 - 未预设路线识别 =============

def test_phase2_spec_use_case_improvised_route():
    """spec §6.1: 未预设的路线能被 LLM 识别为新冲突(用'投靠苏州织工'避免与 Phase 1 关键词冲突)"""
    def llm(prompt, **kwargs):
        # 模拟 LLM 看到"投靠苏州织工"后判别
        return '{"core_intent": "投靠苏州织工", "changed_conflict": true, "suggested_template": "rising_conflict", "confidence": 0.88, "reason": "玩家追随他人,改变核心冲突"}'
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening", title="春蚕", must_resolve=["抗税"])
    result = detector.detect("投靠苏州织工", {}, bp)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"
    assert "投靠苏州织工" in result["trigger"]
    assert result["confidence"] == 0.88


# ============= 测试 10: 无 LLM 时 Phase 2 跳过(向后兼容) =============

def test_phase2_no_llm_unchanged_behavior():
    """无 LLM 时,Phase 1 未触发就不触发(Phase 2 跳过)"""
    detector = RouteDetector()  # 无 llm
    bp = _make_bp("opening")
    result = detector.detect("我去投靠苏州织工", {}, bp)
    # 不在关键词,价值偏移小 → 无变化
    assert result["route_change"] is False
    assert result["suggested_template"] == "opening"


# ============= 测试 11: dict current_chapter 兼容 =============

def test_phase2_llm_with_dict_chapter():
    """dict 形式的 chapter 也能用 Phase 2"""
    def llm(prompt, **kwargs):
        # prompt 应含章节标题
        assert "测试章节" in prompt or "(无显式冲突)" in prompt
        return '{"changed_conflict": true, "suggested_template": "rising_conflict"}'
    detector = RouteDetector(llm_callable=llm)
    bp_dict = {
        "chapter_id": 1,
        "chapter_title": "测试章节",
        "narrative_position": "opening",
        "must_resolve": ["抗税"],
    }
    result = detector.detect("投靠苏州织工", {}, bp_dict)
    assert result["route_change"] is True
    assert result["suggested_template"] == "rising_conflict"


# ============= 测试 12: 空 player_input 不调 LLM =============

def test_phase2_empty_input_no_llm_call():
    """空 player_input 不调 LLM（避免浪费）"""
    llm_called = []
    def llm(prompt, **kwargs):
        llm_called.append(prompt)
        return '{"changed_conflict": true}'
    detector = RouteDetector(llm_callable=llm)
    bp = _make_bp("opening")
    result = detector.detect("", {}, bp)
    assert len(llm_called) == 0
    assert result["route_change"] is False


# ============= 测试 13: coordinator 注入 _llm 链路 =============

def test_coordinator_injects_llm_into_route_detector():
    """coordinator.detect_route_change 应把 self._llm 传给 RouteDetector"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    from history_footnote.chapter.coordinator import ChapterCoordinator
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    facade = ChapterFacade(
        state=state, era_config={}, root_dir=Path(__file__).parent.parent,
    )

    llm_called = []
    def my_llm(prompt, **kwargs):
        llm_called.append(prompt)
        return '{"changed_conflict": true, "suggested_template": "rising_conflict", "confidence": 0.8}'

    coord = ChapterCoordinator(state=state, chapter_facade=facade, llm_callable=my_llm)
    # 注入蓝图,模拟 init 后的状态
    state.chapter_state.blueprint = {
        "chapter_id": 1,
        "chapter_title": "测试",
        "narrative_position": "opening",
        "must_resolve": ["抗税"],
    }
    detection = coord.detect_route_change(
        player_input="投靠苏州织工",  # 不在 Phase 1 关键词
        value_shifts={},
        historical_anchors_triggered=None,
    )
    assert len(llm_called) == 1, "coordinator 应触发 LLM"
    assert detection["route_change"] is True
    assert detection["suggested_template"] == "rising_conflict"
    # LLM 返回 dict 没 core_intent → 默认为 "unknown"
    assert detection["trigger"] == "llm_intent:unknown"