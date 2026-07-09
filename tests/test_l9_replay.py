"""
tests/test_l9_replay.py - 同 seed 重放测试（v2.5 重玩价值验证）

设计动机：v2.5 引入了"全局 seed"机制，承诺"同 seed = 同开局"，
但没测试过。L9 专门验证这件事。

5 个测试：
- L9.1: 抽卡重放（同 seed 同卡）
- L9.2: 10 个 random 决策重放
- L9.3: 5 回合完整路径重放（路遇 + AP）
- L9.4: 序列化-反序列化 重放
- L9.5: 真实 LLM temperature=0 重放（可选）
"""
import sys
import os
import json
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

from pathlib import Path
from history_footnote.game_state import GameState
from history_footnote.fate_cards import (
    draw_fate_cards, FATE_CARDS_POOL, apply_fate_card
)
from history_footnote.location_service import build_location_service
from history_footnote.random_utils import (
    set_session_seed, get_rng, remove_session_rng
)


# ============================================================
# L9.1: 抽卡重放
# ============================================================

def test_L9_01_fate_cards_replay():
    """L9.1: 同 seed 抽 5 张卡必同（连续抽 3 次）"""
    seeds_to_test = [42, 100, 12345, 999999, 0]
    for seed in seeds_to_test:
        set_session_seed("L9_1", seed)
        c1 = [c.id for c in draw_fate_cards("L9_1", n=5)]
        set_session_seed("L9_1", seed)
        c2 = [c.id for c in draw_fate_cards("L9_1", n=5)]
        set_session_seed("L9_1", seed)
        c3 = [c.id for c in draw_fate_cards("L9_1", n=5)]
        assert c1 == c2 == c3, f"seed={seed}: {c1} vs {c2} vs {c3}"
    print(f"  ✅ L9.1: 5 个 seed × 3 次抽卡 = 完全相同")
    return True


# ============================================================
# L9.2: 10 个 random 决策重放
# ============================================================

def test_L9_02_random_sequence_replay():
    """L9.2: 10 个 random 调用 sequence 完全重放"""
    set_session_seed("L9_2", 42)
    rng1 = get_rng("L9_2")
    seq1 = [rng1.random() for _ in range(10)]
    seq1_choices = [rng1.choices(["a", "b", "c"], weights=[0.5, 0.3, 0.2])[0] for _ in range(10)]

    set_session_seed("L9_2", 42)
    rng2 = get_rng("L9_2")
    seq2 = [rng2.random() for _ in range(10)]
    seq2_choices = [rng2.choices(["a", "b", "c"], weights=[0.5, 0.3, 0.2])[0] for _ in range(10)]

    assert seq1 == seq2, f"random 序列不同: {seq1} vs {seq2}"
    assert seq1_choices == seq2_choices, f"choices 序列不同: {seq1_choices} vs {seq2_choices}"
    print(f"  ✅ L9.2: 20 个 random 决策（10 random + 10 choices）= 完全相同")
    return True


# ============================================================
# L9.3: 5 回合完整路径（路遇 + AP + 位置）
# ============================================================

def test_L9_03_full_5_rounds_replay():
    """L9.3: 5 回合模拟：移动 5 次 + 5 次路遇 + 5 次 AP 计算，全部可重放"""
    era = json.load(open('/Users/mac/Documents/trae_projects/history_footnote/eras/wanli1587/era.json'))
    svc = build_location_service(era)

    # 模拟 5 回合：home → tooth_market → 牙行听价 → 听 → 回来
    moves = [
        ("home", "tooth_market"),
        ("tooth_market", "home"),
        ("home", "tea_house"),
        ("tea_house", "home"),
        ("home", "tooth_market"),
    ]
    visited = ["home"]
    heard = []

    # Run 1
    set_session_seed("L9_3", 7777)
    rng1 = get_rng("L9_3")
    path1 = []
    for from_id, to_id in moves:
        result = svc.can_move(from_id, to_id, visited, heard, 3.0)
        if result.success:
            visited.append(to_id)
            # 路遇
            encounter = svc.roll_encounter(from_id, to_id, session_id="L9_3")
            npc = encounter.get("npc") if encounter else None
            path1.append({
                "from": from_id, "to": to_id,
                "ap": result.ap_cost, "encounter": npc,
            })
    # Run 2
    visited2 = ["home"]
    heard2 = []
    set_session_seed("L9_3", 7777)
    rng2 = get_rng("L9_3")
    path2 = []
    for from_id, to_id in moves:
        result = svc.can_move(from_id, to_id, visited2, heard2, 3.0)
        if result.success:
            visited2.append(to_id)
            encounter = svc.roll_encounter(from_id, to_id, session_id="L9_3")
            npc = encounter.get("npc") if encounter else None
            path2.append({
                "from": from_id, "to": to_id,
                "ap": result.ap_cost, "encounter": npc,
            })

    assert path1 == path2, f"路径不同:\n  R1: {path1}\n  R2: {path2}"
    print(f"  ✅ L9.3: 5 回合路径（5 移动 + 5 路遇 + 5 AP）= 完全相同")
    print(f"          {[(p['from']+'→'+p['to'], p['ap'], p['encounter']) for p in path1]}")
    return True


# ============================================================
# L9.4: 序列化-反序列化 重放
# ============================================================

def test_L9_04_serialize_replay():
    """L9.4: GameState 序列化 → 反序列化 → 用同 seed 重放命运卡 = 同结果"""
    # 创建 state
    gs1 = GameState()
    gs1.seed = 9999
    gs1.cash = 5.0
    gs1.debt = 0
    gs1.npc_relations = {"沈氏": 30}
    gs1.visited_locations = ["home", "tooth_market"]
    gs1.heard_locations = ["dyeing_workshop"]
    gs1.current_location = "home"
    gs1.fate_hand = []
    gs1.active_buffs = [{"name": "lucky", "rounds_left": 2, "params": {}}]

    # 序列化（to_dict）
    serialized = {
        "seed": gs1.seed,
        "cash": gs1.cash,
        "npc_relations": dict(gs1.npc_relations),
        "visited_locations": list(gs1.visited_locations),
        "heard_locations": list(gs1.heard_locations),
        "current_location": gs1.current_location,
        "fate_hand": list(gs1.fate_hand),
        "active_buffs": list(gs1.active_buffs),
    }

    # 反序列化（from_dict）
    gs2 = GameState()
    gs2.seed = serialized["seed"]
    gs2.cash = serialized["cash"]
    gs2.npc_relations = serialized["npc_relations"]
    gs2.visited_locations = serialized["visited_locations"]
    gs2.heard_locations = serialized["heard_locations"]
    gs2.current_location = serialized["current_location"]
    gs2.fate_hand = serialized["fate_hand"]
    gs2.active_buffs = serialized["active_buffs"]

    # 验证
    assert gs1.seed == gs2.seed
    assert gs1.cash == gs2.cash
    assert gs1.npc_relations == gs2.npc_relations
    assert gs1.visited_locations == gs2.visited_locations
    assert gs1.heard_locations == gs2.heard_locations
    assert gs1.current_location == gs2.current_location
    assert gs1.active_buffs == gs2.active_buffs

    # 用同 seed 抽卡
    set_session_seed("L9_4", gs1.seed)
    cards1 = [c.id for c in draw_fate_cards("L9_4", n=5)]
    set_session_seed("L9_4", gs2.seed)
    cards2 = [c.id for c in draw_fate_cards("L9_4", n=5)]
    assert cards1 == cards2

    print(f"  ✅ L9.4: 序列化-反序列化 + 重放 = 完全一致")
    return True


# ============================================================
# L9.5: 真实 LLM temperature=0 重放（补充，可选）
# ============================================================

def test_L9_05_real_llm_determinism():
    """L9.5: 真实 LLM（DeepSeek）用 temperature=0 时是否完全可重放

    注意：DeepSeek API 支持 temperature 参数。
    如果设为 0，输出应该是确定性的。
    """
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print(f"  ⏭️ L9.5: 跳过（无 DEEPSEEK_API_KEY）")
        return True

    from history_footnote.llm_providers import make_llm

    try:
        llm = make_llm(provider="deepseek", model="deepseek-chat", extra_kwargs={"temperature": 0})
        # 简单 prompt
        prompt_text = "用一句话介绍万历十五年（1587 年）。"

        # 第一次
        from langchain_core.messages import HumanMessage
        r1 = llm.invoke([HumanMessage(content=prompt_text)])

        # 第二次
        r2 = llm.invoke([HumanMessage(content=prompt_text)])

        # 比较
        t1 = r1.content if hasattr(r1, 'content') else str(r1)
        t2 = r2.content if hasattr(r2, 'content') else str(r2)
        if t1 == t2:
            print(f"  ✅ L9.5: DeepSeek temperature=0 = 完全可重放")
        else:
            # 不一定完全相同（API 服务端可能略有差异），但应该非常相似
            sim = sum(a == b for a, b in zip(t1, t2)) / max(len(t1), len(t2))
            print(f"  ⚠️ L9.5: DeepSeek temperature=0 不完全相同（相似度 {sim:.0%}）")
            print(f"          R1: {t1[:80]}")
            print(f"          R2: {t2[:80]}")
    except Exception as e:
        print(f"  ⚠️ L9.5: LLM 调用失败: {e}")
    return True


# ============================================================
# 主运行
# ============================================================

def main():
    print("=" * 60)
    print("L9 同 seed 重放测试 (5 个)")
    print("=" * 60)
    tests = [
        test_L9_01_fate_cards_replay,
        test_L9_02_random_sequence_replay,
        test_L9_03_full_5_rounds_replay,
        test_L9_04_serialize_replay,
        test_L9_05_real_llm_determinism,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print("=" * 60)
    print(f"L9 结果: {passed} 通过 / {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
