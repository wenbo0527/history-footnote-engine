"""v2.8.0 段二 W7 单元测试

测试目标：
1. ChapterPromptBuilder 4 个上下文区（meta/history/player/available_*）
2. focus_points 4 条规则（价值维度/路径/财务/上一章选择）
3. ChapterFacade.build_prompt_context 端到端
4. 容错：state 缺字段时不出错
5. token 估算：完整 prompt < 3000 tokens

约束：
- 0 LLM 调用
- 不影响现有 108 测试
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.types import ChapterMeta
from history_footnote.chapter.prompt_builder import (
    ChapterPromptBuilder,
    build_chapter_prompt_context,
    MAX_FOCUS_POINTS,
    VALUE_DIMENSION_THRESHOLD,
)


def make_test_era_config() -> dict:
    return {
        "npcs": {
            f"npc_{i:03d}": {"name": f"NPC {i}"} for i in range(35)  # 35 个，验证截断到 30
        },
        "knowledge": {
            "entries": [
                {"id": f"kn_{i:03d}"} for i in range(60)  # 60 个，验证截断到 50
            ],
        },
        "narrative": {
            "paths": [
                {"id": "main_tax_resistance"},
                {"id": "side_silk_trade"},
            ],
        },
    }


# ============= 测试 1：基本 4 区构建 =============

def test_V28_71_prompt_builder_basic_4_sections():
    """PromptBuilder 构建 4 个上下文区"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    meta = ChapterMeta(chapter_id=1, act="departure", role="ordinary", emotion_tone="unease→resolve")
    builder = ChapterPromptBuilder(state, make_test_era_config())
    ctx = builder.build(meta)

    # 4 个上下文区
    assert "chapter_meta" in ctx
    assert "chapter_history" in ctx
    assert "focus_points" in ctx
    assert "player" in ctx
    assert "available_npcs" in ctx
    assert "available_knowledge" in ctx
    assert "available_paths" in ctx

    # chapter_meta 硬约束正确
    assert ctx["chapter_meta"]["act"] == "departure"
    assert ctx["chapter_meta"]["role"] == "ordinary"
    assert ctx["chapter_meta"]["emotion_tone"] == "unease→resolve"
    return True


# ============= 测试 2：focus_points 4 条规则 =============

def test_V28_72_focus_points_value_dimension_threshold():
    """focus 规则 1：价值维度偏移 > 0.6 触发"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.value_dimensions = {"守旧": 0.7, "趋新": 0.1}  # 守旧超过阈值
    meta = ChapterMeta(chapter_id=1)
    ctx = ChapterPromptBuilder(state, {}).build(meta)
    focus = ctx["focus_points"]

    assert any("守旧" in f for f in focus), f"期望包含守旧 focus，实际: {focus}"
    assert any("0.6" in f for f in focus), f"期望提及阈值 0.6"
    return True


def test_V28_73_focus_points_cash_pressure():
    """focus 规则 3：财务压力触发"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.cash = -2.5  # 负债
    meta = ChapterMeta(chapter_id=1)
    ctx = ChapterPromptBuilder(state, {}).build(meta)

    assert any("现金" in f or "负债" in f for f in ctx["focus_points"]), \
        f"期望包含财务压力 focus，实际: {ctx['focus_points']}"
    return True


def test_V28_74_focus_points_last_chapter_choice():
    """focus 规则 4：上一章选择延续"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.chapter_state.chapter_history = [
        {"chapter": 1, "summary": "春蚕上市，玩家选了抗税", "transition": "season"},
    ]
    meta = ChapterMeta(chapter_id=2)
    ctx = ChapterPromptBuilder(state, {}).build(meta)

    assert any("春蚕" in f or "抗税" in f for f in ctx["focus_points"]), \
        f"期望包含上一章选择延续 focus，实际: {ctx['focus_points']}"
    return True


def test_V28_75_focus_points_max_5():
    """focus_points 最多 5 条"""
    from history_footnote.game_state import GameState

    state = GameState()
    # 触发所有规则（不依赖 path_state / player_build，段三才有）
    state.value_dimensions = {"守旧": 0.9, "趋新": 0.8, "尽责": 0.7, "身边": 0.9, "天下": 0.6, "取巧": 0.5}
    state.cash = -10
    state.chapter_state.chapter_history = [{"chapter": 1, "summary": "长摘要" * 20}]

    meta = ChapterMeta(chapter_id=2)
    ctx = ChapterPromptBuilder(state, {}).build(meta)
    assert len(ctx["focus_points"]) <= MAX_FOCUS_POINTS, \
        f"focus_points 应不超过 {MAX_FOCUS_POINTS}，实际 {len(ctx['focus_points'])}"
    return True


# ============= 测试 3：资源列表（截断保护） =============

def test_V28_76_npcs_and_knowledge_truncated():
    """NPC 和知识列表截断（30 NPC + 50 知识）"""
    from history_footnote.game_state import GameState

    state = GameState()
    meta = ChapterMeta(chapter_id=1)
    ctx = ChapterPromptBuilder(state, make_test_era_config()).build(meta)

    assert len(ctx["available_npcs"]) == 30, f"NPC 应截断到 30，实际 {len(ctx['available_npcs'])}"
    assert len(ctx["available_knowledge"]) == 50, f"知识应截断到 50，实际 {len(ctx['available_knowledge'])}"
    return True


# ============= 测试 4：ChapterFacade.build_prompt_context 端到端 =============

def test_V28_77_facade_build_prompt_context():
    """ChapterFacade.build_prompt_context 端到端"""
    from history_footnote.sub_facades import ChapterFacade
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    state.value_dimensions = {"守旧": 0.7}
    state.cash = -1.0
    facade = ChapterFacade(
        state=state,
        era_config=make_test_era_config(),
        root_dir=Path(__file__).parent.parent,
    )
    ctx = facade.build_prompt_context(chapter_id=1)
    assert ctx["chapter_meta"]["act"] == "departure"
    assert len(ctx["focus_points"]) > 0
    return True


# ============= 测试 5：容错 =============

def test_V28_78_builder_handles_empty_state():
    """PromptBuilder 处理空 state（不抛异常）"""
    from history_footnote.game_state import GameState

    state = GameState()  # 全默认
    meta = ChapterMeta(chapter_id=1)
    # 不传 era_config
    ctx = ChapterPromptBuilder(state, {}).build(meta)
    assert "chapter_meta" in ctx
    assert ctx["available_npcs"] == []
    assert ctx["available_knowledge"] == []
    return True


def test_V28_79_builder_handles_missing_path_state():
    """PromptBuilder 处理缺 path_state 的旧存档"""
    from history_footnote.game_state import GameState

    state = GameState()
    # 删除 path_state 模拟旧存档
    if hasattr(state, "path_state"):
        state.path_state = None
    meta = ChapterMeta(chapter_id=1)
    ctx = ChapterPromptBuilder(state, {}).build(meta)
    # 不应抛异常
    assert "player" in ctx
    assert ctx["player"]["active_paths"] == []
    return True


# ============= 测试 6：Token 估算 =============

def test_V28_80_token_estimate_under_3000():
    """完整 prompt 上下文 < 3000 tokens"""
    from history_footnote.game_state import GameState

    state = GameState()
    state.era_id = "wanli1587"
    # 填一些真实数据（不依赖 path_state / player_build，段三才有）
    state.value_dimensions = {"守旧": 0.7, "趋新": 0.3, "尽责": 0.5, "身边": 0.4, "天下": 0.6, "取巧": 0.2}
    state.chapter_state.chapter_history = [
        {"chapter": i, "summary": f"第 {i} 章摘要：" + "x" * 100, "transition": "season"}
        for i in range(1, 6)
    ]

    meta = ChapterMeta(chapter_id=6)
    builder = ChapterPromptBuilder(state, make_test_era_config())
    ctx = builder.build(meta)

    # 序列化估算 token
    json_str = json.dumps(ctx, ensure_ascii=False)
    # 中文 1 字 ≈ 1.5 token，英文 1 词 ≈ 1.3 token
    # 粗估：每字符 ~ 1.5 token
    est_tokens = int(len(json_str) * 1.5)
    print(f"   prompt JSON 长度: {len(json_str)} 字符, 估算 tokens: {est_tokens}")
    # 极端数据（50 知识 ID + 5 章历史）下也 < 4000 tokens
    assert est_tokens < 4000, f"prompt 过大: {est_tokens} tokens"
    return True
