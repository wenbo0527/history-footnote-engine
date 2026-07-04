"""🆕 v1.6.3 剧情回顾单元测试"""
import sys
from pathlib import Path
sys.path.insert(0, "src")

from history_footnote.game_state import GameState


def test_basic_append():
    """基础追加 + recent 保留"""
    state = GameState(current_date="1587年1月")
    for i in range(5):
        state.append_narrative(i + 1, f"叙事 {i+1}", f"摘要 {i+1}")
    assert len(state.narrative_recent) == 5
    assert len(state.narrative_history) == 5
    assert state.narrative_recent[-1]["round"] == 5
    print(f"✅ test_basic_append: 5 回合 → 5 narrative_recent")


def test_recent_size_limit():
    """recent 超过 20 回合 → 弹出到 archive"""
    state = GameState(current_date="1587年1月")
    # 加 30 回合
    for i in range(30):
        state.append_narrative(i + 1, f"完整叙事 {i+1}", f"摘要 {i+1}")

    # recent 应该只有 20
    assert len(state.narrative_recent) == state.NARRATIVE_RECENT_SIZE == 20
    # archive 应该有 10 条（30 - 20）
    assert len(state.narrative_archive) == 10
    # narrative_archive 第一条应该是回合 1
    assert state.narrative_archive[0]["round"] == 1
    # narrative_recent 最后一条应该是回合 30
    assert state.narrative_recent[-1]["round"] == 30
    print(f"✅ test_recent_size_limit: 30 回合 → recent=20 + archive=10")


def test_archive_size_limit():
    """archive 超过 100 → LRU 淘汰"""
    state = GameState(current_date="1587年1月")
    # 加 150 回合
    for i in range(150):
        state.append_narrative(i + 1, f"完整叙事 {i+1}", f"摘要 {i+1}")

    # recent 20 + archive 最多 100
    assert len(state.narrative_recent) == 20
    assert len(state.narrative_archive) == 100
    # narrative_archive 应该从回合 31 开始（最旧的已淘汰）
    assert state.narrative_archive[0]["round"] == 31
    print(f"✅ test_archive_size_limit: 150 回合 → recent=20 + archive=100")


def test_get_recap_basic():
    """get_recap() 返回双层结构"""
    state = GameState(current_date="1587年1月", round_number=15)
    for i in range(15):
        state.append_narrative(i + 1, f"回合 {i+1} 的详细叙述内容" * 3, f"摘要 {i+1}")

    recap = state.get_recap(recent_count=5, archive_count=50)

    assert recap["round_number"] == 15
    assert recap["current_date"] == "1587年1月"
    assert recap["total_narratives"] == 15
    assert len(recap["recent"]) == 5
    assert len(recap["archive"]) == 0  # 15 - 20 < 0，没有 archive
    assert recap["recent"][-1]["round"] == 15
    print(f"✅ test_get_recap_basic: 15 回合 → recent=5 + archive=0")


def test_get_recap_with_archive():
    """get_recap() 跨 recent + archive"""
    state = GameState(current_date="1587年1月", round_number=35)
    for i in range(35):
        state.append_narrative(i + 1, f"详细 {i+1}", f"摘要 {i+1}")

    recap = state.get_recap(recent_count=10, archive_count=50)

    assert recap["round_number"] == 35
    assert recap["total_narratives"] == 35
    assert len(recap["recent"]) == 10
    assert len(recap["archive"]) == 15  # 35 - 20
    # recent 最后一条 = round 35
    assert recap["recent"][-1]["round"] == 35
    # archive 第一条 = round 1（最早弹出）
    assert recap["archive"][0]["round"] == 1
    # archive 最后一条 = round 15（最近弹出）
    assert recap["archive"][-1]["round"] == 15
    print(f"✅ test_get_recap_with_archive: 35 回合 → recent=[26-35] + archive=[1-15]")


def test_archive_summary():
    """archive 摘要包含叙事预览 + summary"""
    state = GameState(current_date="1587年1月")
    # 加 25 回合：第一回合有 300 字叙事
    for i in range(25):
        narrative = f"回合 {i+1}: " + "x" * 300
        state.append_narrative(i + 1, narrative, f"摘要 {i+1}")

    # 回合 1-5 被归档
    assert len(state.narrative_archive) >= 5
    first_archive = state.narrative_archive[0]
    assert first_archive["round"] == 1
    # narrative_preview 应该 ≤ 200 字符
    assert len(first_archive["narrative_preview"]) <= 200
    # summary 应该非空
    assert first_archive["summary"]
    print(f"✅ test_archive_summary: 归档叙事预览 {len(first_archive['narrative_preview'])} chars")


def test_get_recap_edge_cases():
    """边界条件"""
    state = GameState(current_date="1587年1月")

    # 0 回合
    recap = state.get_recap()
    assert recap["total_narratives"] == 0
    assert len(recap["recent"]) == 0
    assert len(recap["archive"]) == 0

    # 仅 1 回合
    state.append_narrative(1, "first", "first summary")
    recap = state.get_recap(recent_count=5)
    assert recap["total_narratives"] == 1
    assert len(recap["recent"]) == 1
    print(f"✅ test_get_recap_edge_cases: 0/1 回合边界正确")


def test_dataclass_serialization():
    """to_dict() 包含新字段"""
    state = GameState(current_date="1587年1月")
    for i in range(3):
        state.append_narrative(i + 1, f"narrative {i+1}", f"summary {i+1}")

    d = state.to_dict()
    assert "narrative_history" in d
    assert "narrative_recent" in d
    assert "narrative_archive" in d
    assert "NARRATIVE_RECENT_SIZE" in d
    assert "NARRATIVE_ARCHIVE_SIZE" in d
    assert d["NARRATIVE_RECENT_SIZE"] == 20
    assert d["NARRATIVE_ARCHIVE_SIZE"] == 100
    print(f"✅ test_dataclass_serialization: to_dict 包含所有 v1.6.3 新字段")


if __name__ == "__main__":
    print("=" * 50)
    print("剧情回顾 单元测试（v1.6.3）")
    print("=" * 50)
    test_basic_append()
    test_recent_size_limit()
    test_archive_size_limit()
    test_get_recap_basic()
    test_get_recap_with_archive()
    test_archive_summary()
    test_get_recap_edge_cases()
    test_dataclass_serialization()
    print("\n✅ 所有剧情回顾测试通过")