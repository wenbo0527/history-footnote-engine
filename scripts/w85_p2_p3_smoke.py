"""v2.10.1 W85 Phase 2/3 真 LLM smoke 测试

- 用真实 LLM(MiniMax Anthropic)测试 RouteDetector
- 验证未预设路线的 LLM 分类 + 收束检查

用法：
  set -a && source .env && set +a
  .venv/bin/python scripts/w85_p2_p3_smoke.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

# 项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.chapter.route_detector import RouteDetector
from history_footnote.chapter.types import ChapterBlueprint


def make_llm(provider: str = "minimax-anthropic"):
    """构造真实 LLM callable"""
    from history_footnote.llm_wrapper import get_wrapped_llm
    wrapper = get_wrapped_llm(primary_provider=provider)
    def llm(prompt: str, max_tokens: int = 200) -> str:
        messages = [
            {"role": "system", "content": "你是 JSON 输出助手,严格按用户要求输出。"},
            {"role": "user", "content": prompt},
        ]
        result = wrapper.invoke(messages)
        # 兼容 AIMessage(BaseMessage):提取 content
        if hasattr(result, "content"):
            content = result.content
        elif isinstance(result, str):
            content = result
        else:
            content = json.dumps(result, ensure_ascii=False)
        return content
    return llm


def test_phase2_improvised_route():
    """Phase 2: 未预设路线 → LLM 分类"""
    print("=== Phase 2 测试 ===")
    llm = make_llm()
    detector = RouteDetector(llm_callable=llm)
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    # 不在关键词表的输入
    result = detector.detect("投靠苏州织工", {}, bp)
    print(f"  输入: '投靠苏州织工'")
    print(f"  route_change: {result['route_change']}")
    print(f"  suggested_template: {result['suggested_template']}")
    print(f"  trigger: {result['trigger']}")
    print(f"  confidence: {result['confidence']}")
    print(f"  dm_instruction: {result['dm_instruction'][:100]}...")
    print()
    return result


def test_phase3_convergence_check():
    """Phase 3: 收束检查（无需 LLM，单元方法）"""
    print("=== Phase 3 测试：收束检查 ===")
    detector = RouteDetector()
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="opening",
        must_resolve=["抗税"],
    )
    # 测试倒退 2+ 步拒绝
    passed, reason = detector._convergence_check("opening", "crisis", ["抗税"])
    print(f"  crisis→opening（倒退 2 步）: passed={passed}, reason='{reason}'")
    assert passed is False
    # 测试前进通过
    passed, reason = detector._convergence_check("crisis", "rising_conflict", ["抗税"])
    print(f"  rising_conflict→crisis（前进 1 步）: passed={passed}, reason='{reason}'")
    assert passed is True
    # 测试倒退 1 步通过
    passed, reason = detector._convergence_check("opening", "rising_conflict", ["抗税"])
    print(f"  rising_conflict→opening（倒退 1 步）: passed={passed}, reason='{reason}'")
    assert passed is True
    print()


def test_phase3_real_llm_full_flow():
    """Phase 3: 真实 LLM 路径（带 7 字段 prompt + 收束检查）"""
    print("=== Phase 3 真实 LLM 测试 ===")
    llm = make_llm()
    detector = RouteDetector(llm_callable=llm)
    bp = ChapterBlueprint(
        chapter_id=1,
        chapter_title="春蚕",
        narrative_position="rising_conflict",
        must_resolve=["抗税"],
    )
    result = detector.detect(
        player_input="投靠苏州织工",
        value_shifts={},
        current_chapter=bp,
        route_history=[{"round": 3, "from_template": "opening", "to_template": "rising_conflict", "trigger": "keyword:抗税"}],
    )
    print(f"  输入: '投靠苏州织工' (在 rising_conflict)")
    print(f"  route_change: {result['route_change']}")
    print(f"  suggested_template: {result['suggested_template']}")
    print(f"  trigger: {result['trigger']}")
    print(f"  confidence: {result['confidence']}")
    print(f"  dm_instruction: {result['dm_instruction'][:200]}")
    print()
    return result


if __name__ == "__main__":
    print("🆕 v2.10.1 W85 Phase 2/3 真 LLM smoke\n")
    try:
        test_phase3_convergence_check()
        result_p2 = test_phase2_improvised_route()
        result_p3 = test_phase3_real_llm_full_flow()
        print("✅ All smoke tests passed")
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)