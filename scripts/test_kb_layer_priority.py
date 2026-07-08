"""测试塌房 3 修复：知识库 layer 优先级"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.knowledge_base import KnowledgeBase

era = json.loads((ROOT / "eras/wanli1587/era.json").read_text())
kb = KnowledgeBase(entries=era.get("knowledge", {}).get("entries", []))

print("="*70)
print("🧪 知识库 layer 优先级测试")
print("="*70)

# === Test 1: "朝廷" 不应让 entity（人物）排在最前 ===
print("\n[1] '朝廷' 关键词匹配（应优先 background/principle）")
results = kb.query(keywords=["朝廷"])
print(f"  匹配 {len(results)} 条")
for r in results[:5]:
    print(f"  [{r.get('layer', '?'):10s}] {r.get('id', '?'):30s} - {r.get('title', '?')[:40]}")

# 验证：第 1 条不应是 entity
if results:
    first_layer = results[0].get("layer")
    assert first_layer in ("background", "principle", "scene"), f"最优先应是 background/principle/scene，实际 {first_layer}"
    print(f"  ✅ 最优先是 {first_layer}（不是 entity）")

# === Test 2: "皇帝" 同理 ===
print("\n[2] '皇帝' 关键词匹配（应优先 background/principle）")
results = kb.query(keywords=["皇帝"])
print(f"  匹配 {len(results)} 条")
for r in results[:5]:
    print(f"  [{r.get('layer', '?'):10s}] {r.get('id', '?'):30s}")

if results:
    first_layer = results[0].get("layer")
    assert first_layer in ("background", "principle", "scene"), f"最优先应是 background/principle/scene，实际 {first_layer}"
    print(f"  ✅ 最优先是 {first_layer}（不是 entity）")

# === Test 3: 没人名应该 entity 优先（如果有人名特定实体） ===
# 比如 "戚继光" 实际是 entity（人物）
print("\n[3] '戚继光' 关键词匹配")
results = kb.query(keywords=["戚继光"])
for r in results[:3]:
    print(f"  [{r.get('layer', '?'):10s}] {r.get('id', '?'):30s}")

# === Test 4: 多场景 + 关键词混合 ===
print("\n[4] scene='牙行' + keyword='价格'")
results = kb.query(keywords=["价格"], scene="牙行")
print(f"  匹配 {len(results)} 条")
for r in results[:5]:
    print(f"  [{r.get('layer', '?'):10s}] {r.get('id', '?'):30s}")

# === Test 5: layer 统计 ===
print("\n[5] layer 分布统计")
from collections import Counter
all_layers = Counter(e.get("layer", "?") for e in era.get("knowledge", {}).get("entries", []))
for layer, count in all_layers.most_common():
    print(f"  {layer:15s}: {count} 条")

print("\n" + "="*70)
print("✅ 塌房 3 修复验证")
print("="*70)
