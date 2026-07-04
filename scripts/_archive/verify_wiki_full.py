"""验证所有Wiki都已正确写入并能查询"""
import json
import sys
from pathlib import Path
sys.path.insert(0, "src")

config = json.load(open("eras/wanli1587/era.json", "r", encoding="utf-8"))

print("=" * 60)
print("Wiki完整性验证")
print("=" * 60)

entries = config["knowledge"]["entries"]
snippets = config["knowledge"]["narrative_snippets"]

# === 1. 数量统计 ===
print(f"\n[1] 数量统计")
print(f"  entries: {len(entries)}条")
print(f"  snippets: {len(snippets)}条")

# 按layer分类
from collections import Counter
layer_counts = Counter(e["layer"] for e in entries)
print(f"  entries按层级:")
for layer, count in layer_counts.items():
    print(f"    {layer}: {count}")

# 按id前缀分类
prefix_counts = Counter()
for e in entries:
    prefix = e["id"].split("_")[0]
    prefix_counts[prefix] += 1
print(f"  entries按id前缀:")
for prefix, count in prefix_counts.most_common():
    print(f"    {prefix}: {count}")

# === 2. 长度检查 ===
print(f"\n[2] 长度检查（防止context window爆）")
entries_lengths = [len(e.get("content", "")) for e in entries]
snippets_lengths = [len(s.get("snippet_text", "")) for s in snippets]

print(f"  entries.content 平均长度: {sum(entries_lengths) // len(entries_lengths)}字符")
print(f"  entries.content 最大长度: {max(entries_lengths)}字符")
print(f"  entries.content >300字符的: {sum(1 for l in entries_lengths if l > 300)}条")

print(f"  snippets.snippet_text 平均长度: {sum(snippets_lengths) // len(snippets_lengths)}字符")
print(f"  snippets.snippet_text 最大长度: {max(snippets_lengths)}字符")

# === 3. 关键Wiki是否齐全 ===
print(f"\n[3] 关键Wiki检查")
required_entry_ids = [
    # 支线v2.0
    "sc_imperial_exam_path", "pr_xiucai_privileges",
    "sc_jiangnan_underworld", "sc_dahang", "sc_ximen_qing_path",
    "sc_fujian_wind", "sc_talented_women", "sc_three_goddesses",
    # 离乡v1.0
    "bg_population_mobility", "bg_longqing_kaihai",
    "sc_yue_gang_life", "sc_nanyang_sea_route",
    "sc_grand_canal", "sc_ming_army_recruit",
]
existing_ids = {e["id"] for e in entries}
missing = [eid for eid in required_entry_ids if eid not in existing_ids]
if missing:
    print(f"  ❌ 缺失: {missing}")
else:
    print(f"  ✅ 全部{len(required_entry_ids)}条关键entries都已写入")

required_snip_ids = [
    "sn_fanjin_zhongju", "sn_xu_wei_life", "sn_wen_xiucai",
    "sn_wang_po", "sn_xue_sao", "sn_ye_family",
    "sn_yuegang_silk", "sn_lvson_silver", "sn_japan_prohibited",
    "sn_canal_danger", "sn_army_koukou",
]
existing_snip_ids = {s["id"] for s in snippets}
missing_snips = [sid for sid in required_snip_ids if sid not in existing_snip_ids]
if missing_snips:
    print(f"  ❌ 缺失snippets: {missing_snips}")
else:
    print(f"  ✅ 全部{len(required_snip_ids)}条关键snippets都已写入")

# === 4. 检索功能测试 ===
print(f"\n[4] 检索功能测试")
from history_footnote.knowledge_base import KnowledgeBase
kb = KnowledgeBase(
    entries=entries,
    snippets=snippets,
)

# 测试1: 检索科举
results = kb.query(keywords=["科举", "秀才"])
print(f"  检索'科举/秀才': {len(results)}条")
for r in results[:3]:
    print(f"    - {r['id']}")

# 测试2: 检索月港
results = kb.query(keywords=["月港", "海澄"])
print(f"  检索'月港/海澄': {len(results)}条")
for r in results[:3]:
    print(f"    - {r['id']}")

# 测试3: 检索女性
results = kb.query(keywords=["牙婆", "卖婆"])
print(f"  检索'牙婆/卖婆': {len(results)}条")
for r in results[:3]:
    print(f"    - {r['id']}")

# 测试4: 场景+性别过滤的snippets
male_snips = kb.query_snippets(scene="茶馆", top_k=5, player_gender="male")
female_snips = kb.query_snippets(scene="茶馆", top_k=5, player_gender="female")
print(f"\n  snippets性别过滤:")
print(f"    男性茶馆: {len(male_snips)}条")
print(f"    女性茶馆: {len(female_snips)}条")
print(f"    差异: {len(male_snips) - len(female_snips)}条（女性专属/男性专属）")

# === 5. era.json完整性 ===
print(f"\n[5] era.json结构完整性")
assert "knowledge" in config
assert "entries" in config["knowledge"]
assert "narrative_snippets" in config["knowledge"]
assert "player_identities" in config["world"]
assert "identity_switch_offers" in config["world"]
assert "iron_laws" in config["world"]
assert "timeline" in config["world"]
print(f"  ✅ 所有必需字段都存在")

print("\n" + "=" * 60)
print("✅ Wiki完整性验证完成")
print("=" * 60)