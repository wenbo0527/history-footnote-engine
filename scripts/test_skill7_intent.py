"""测试塌房 5 修复：SKILL-7 意图铁律"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.dm_skills import skill_7_three_layer_verdict, _detect_intent

era = json.loads((ROOT / "eras/wanli1587/era.json").read_text())

# === 意图检测 ===
test_intents = [
    ("我去科举考试", "participate_imperial_exam"),
    ("我要考秀才", "participate_imperial_exam"),
    ("我去进学", "participate_imperial_exam"),
    ("我去府学读书", "participate_imperial_exam"),
    ("我想见皇帝", "audience_emperor"),
    ("面圣", "audience_emperor"),
    ("我去参军", "join_army"),
    ("告御状", "appeal_to_emperor"),
    ("去京城", "go_capital"),
    ("我准备出家当和尚", "become_monk"),
    ("我先看看家里情况", None),
    ("我去镇上看看", None),
    ("我想出家", None),  # 单独"出家"不命中
    ("我想了一下", None),
]

print("="*70)
print("🧪 意图检测测试")
print("="*70)

passed = 0
failed = 0
for text, expected in test_intents:
    actual = _detect_intent(text)
    status = "✅" if actual == expected else "❌"
    if actual == expected:
        passed += 1
    else:
        failed += 1
    print(f"{status} '{text}' → {actual} (期望 {expected})")

print(f"\n📊 intent: {passed} 通过 / {failed} 失败")

# === 身份铁律 ===
print("\n" + "="*70)
print("🧪 身份铁律测试")
print("="*70)

test_cases = [
    # (text, identity, expected_verdict, note)
    ("我去科举考试", "weaving_male", "rejected", "织工科举"),
    ("我想考秀才", "weaving_male", "rejected", "织工考秀才"),
    ("我想见皇帝", "weaving_male", "rejected", "织工见皇帝"),
    ("我要去京城", "weaving_male", "rejected", "织工去京城"),
    ("我准备参军", "weaving_male", "rejected", "织工参军"),
    ("我去镇上看看", "weaving_male", "allowed", "织工正常行动"),
    ("我去织一匹绸", "weaving_male", "allowed", "织工正常行动"),
    # 商贩
    ("我去科举考试", "merchant_male", "rejected", "商贩科举"),
    ("我要去京城", "merchant_male", "allowed", "商贩去京城（商人）"),
    # 农户
    ("我去科举考试", "farmer_male", "rejected", "农户科举"),
    ("我要去京城", "farmer_male", "rejected", "农户去京城"),
    # 秀才
    ("我想考举人", "scholar_male", "allowed", "秀才考举人（应允许）"),
    ("我想见皇帝", "scholar_male", "rejected", "秀才见皇帝（不允许）"),
]

passed2 = 0
failed2 = 0
for text, identity, expected, note in test_cases:
    state = {"selected_identity": identity}
    result = skill_7_three_layer_verdict(era, text, state)
    actual = "rejected" if result.verdict == "reject_narratively" else "allowed"
    status = "✅" if actual == expected else "❌"
    if actual == expected:
        passed2 += 1
    else:
        failed2 += 1
    print(f"{status} [{identity[:8]}] '{text}' ({note})")
    print(f"   期望: {expected}  实际: {actual}  layer={result.layer}")
    if result.verdict == "reject_narratively":
        print(f"   拒绝: {result.narrative_constraint[:80]}...")

print(f"\n📊 铁律: {passed2} 通过 / {failed2} 失败")
print(f"\n📊 合计: {passed+passed2} 通过 / {failed+failed2} 失败")
