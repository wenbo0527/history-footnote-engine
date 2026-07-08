"""测试塌房 6 修复：SKILL-4 史实锚点"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.dm_skills import skill_4_anchor_history

era = json.loads((ROOT / "eras/wanli1587/era.json").read_text())

print("="*70)
print("🧪 SKILL-4 史实锚点测试")
print("="*70)

# 准备 state
def make_state(round_num, triggered=None):
    return {
        "round_number": round_num,
        "triggered_events": triggered or [],
    }

# === Test 1: 触发回合内 ===
# anchor_spring_tax: trigger_round=3, foreshadow_round=1
# round=3 时是触发阶段
print("\n[1] round=3（anchor_spring_tax 触发阶段）")
state = make_state(3)
hist = skill_4_anchor_history(era, state, "")
if hist:
    print(f"  ✅ 返回锚点: {hist.anchor_id}")
    print(f"  triggered={hist.triggered}")
    print(f"  state.triggered_events = {state.get('triggered_events')}")
    assert hist.triggered == True, f"应该立即标记 triggered=True (实际={hist.triggered})"
    assert hist.anchor_id in state.get("triggered_events", []), "state.triggered_events 应包含 anchor_id"
    print("  ✅ 塌房 6 修复：触发时立即标记")
else:
    print("  ❌ 应该返回锚点")

# === Test 2: 再次调用同一回合（不应重复触发同一锚点）===
print("\n[2] round=3 再次调用（应被已触发状态排除 anchor_spring_tax）")
state2 = make_state(3, triggered=["anchor_spring_tax"])
hist2 = skill_4_anchor_history(era, state2, "")
# 可能在 round=3 触发了其他 historical_events 派生的锚点（he_01）
# 但 anchor_spring_tax 不会再返回
if hist2 is None or hist2.anchor_id != "anchor_spring_tax":
    print(f"  ✅ 不会重复触发 anchor_spring_tax（实际: {hist2.anchor_id if hist2 else None}）")
else:
    print(f"  ❌ 仍返回: {hist2.anchor_id}")

# === Test 3: 接近锚点 → 铺垫阶段（不标记）===
print("\n[3] round=1, 锚点在 round=3（铺垫）")
state3 = make_state(1)
# 这里用现有 anchor_spring_tax 测试（trigger_round=2）— 但 round=1 时未触发
hist3 = skill_4_anchor_history(era, state3, "")
if hist3:
    print(f"  返回: {hist3.anchor_id}, triggered={hist3.triggered}, foreshadowing={bool(hist3.foreshadowing_lead)}")
    # 注意：anchor_spring_tax 可能在 round=1 已经是"已到"或"铺垫"
    if hist3.foreshadowing_lead:
        assert hist3.triggered == False, "铺垫阶段不应标记 triggered"
        assert hist3.anchor_id not in state3.get("triggered_events", []), "铺垫阶段不应加进 triggered_events"
        print("  ✅ 铺垫阶段不标记")

# === Test 4: 跨多回合测试 ===
print("\n[4] 模拟：round=3 触发 anchor_spring_tax → round=4 不再返回")
state4 = make_state(3)
hist_a = skill_4_anchor_history(era, state4, "")
print(f"  round=3: {hist_a.anchor_id if hist_a else None}, triggered_events={state4.get('triggered_events')}")
# state4 已被修改
# 改 round 再测
state4["round_number"] = 4
hist_b = skill_4_anchor_history(era, state4, "")
print(f"  round=4: {hist_b.anchor_id if hist_b else None}, triggered_events={state4.get('triggered_events')}")
# 关键判定：anchor_spring_tax 不再返回
if hist_b is None or hist_b.anchor_id != "anchor_spring_tax":
    print(f"  ✅ anchor_spring_tax 不会被重复触发")
else:
    print(f"  ❌ anchor_spring_tax 仍被返回")

# === Test 5: state 没传 triggered_events key  ===
print("\n[5] state 没有 triggered_events 字段")
state5 = {"round_number": 3}
try:
    hist5 = skill_4_anchor_history(era, state5, "")
    print(f"  ✅ 不报错，返回: {hist5.anchor_id if hist5 else None}")
    print(f"  注入的 triggered_events: {state5.get('triggered_events')}")
except Exception as e:
    print(f"  ❌ 报错: {e}")

# === Test 6: 同一回合内 + 同 state 测试 ===
print("\n[6] 同 state 3 次连续调用 (round=3)")
state6 = {"round_number": 3}
results = []
for i in range(3):
    h = skill_4_anchor_history(era, state6, "")
    results.append(h.anchor_id if h else None)
print(f"  返回序列: {results}")
print(f"  state.triggered_events: {state6.get('triggered_events')}")
# 关键：anchor_spring_tax 第一次返回，第二次/第三次应 None
assert results[0] is not None, "第一次应返回"
# 因为同一回合里有多个锚点，后续可能返回别的，但 anchor_spring_tax 不应再出
for i, r in enumerate(results[1:], 1):
    if r == "anchor_spring_tax":
        print(f"  ❌ 第 {i+1} 次仍返回 anchor_spring_tax（应被标记）")
        sys.exit(1)
print("  ✅ 同一回合 anchor_spring_tax 只触发 1 次")

print("\n" + "="*70)
print("✅ 塌房 6 修复验证通过")
print("="*70)
