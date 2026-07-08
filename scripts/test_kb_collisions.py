"""专项测试：知识库关键词误匹配"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.knowledge_base import KnowledgeBase

era = json.loads((ROOT / "eras/wanli1587/era.json").read_text())
kb_entries = era.get("knowledge", {}).get("entries", [])
kb = KnowledgeBase(entries=kb_entries)

print(f"📚 知识库: {len(kb_entries)} 条")
print(f"   layers: {set(e.get('layer') for e in kb_entries)}")

# 危险输入：可能误匹配多个条目
DANGEROUS = [
    ("云南", "地名含'南'"),
    ("山高", "山"),
    ("家门", "家"),
    ("去西山", "山+西"),
    ("请客", "客"),
    ("相亲", "亲"),
    ("上路", "上"),
    ("事情", "情"),
    ("当下", "下"),
    ("明日", "日"),
    ("山上", "山"),
    ("家中", "家"),
    ("其家", "家"),
    ("日子", "日"),
    ("朝廷", "核心词: 朝廷"),
    ("皇帝", "核心词: 皇帝"),
    ("", "空字符串"),
    ("今天我", "无意义"),
    ("我准备", "无意义"),
    ("我选择", "无意义"),
]

print("\n" + "="*80)
print("🔥 关键词误匹配测试")
print("="*80)

for text, note in DANGEROUS:
    kws = kb._extract_keywords(text)
    results = kb.query(keywords=kws)
    matched_ids = [r.get('id', '?') for r in results[:5]]
    flag = "🚨" if len(results) > 3 else "  "
    print(f"{flag} '{text:10s}' ({note})")
    print(f"   关键词: {kws}")
    print(f"   匹配 {len(results):2d} 条: {matched_ids[:3]}{'...' if len(matched_ids)>3 else ''}")

# 2字 vs 4字 tokenization 行为
print("\n" + "="*80)
print("🔬 分词行为细节")
print("="*80)

# 单字 + 2字 token 是否会被同一条目双匹配？
test_2char = "我想"
test_4char = "今日天气"
test_8char = "我想吃山药"

for txt in [test_2char, test_4char, test_8char]:
    kws = kb._extract_keywords(txt)
    print(f"'{txt}' → {kws}")

# 测试：3字 词被错误切分成 2字 + 1字 残段
print("\n" + "="*80)
print("🧪 特殊 case: 重叠子串")
print("="*80)
# "万历十五年" → 2-4 字滑窗会切出 ["万历", "历十", "十五", "五年"]
# 关键看是否会乱匹配
import re
text = "万历十五年正月"
matches = list(re.finditer(r"[\u4e00-\u9fa5]{2,4}", text))
print(f"'{text}' 滑窗: {[m.group() for m in matches]}")
for m in matches:
    matched = kb.query(keywords=[m.group()])
    if matched:
        print(f"  '{m.group()}' 匹配 {len(matched)} 条 → {[r.get('id')[:30] for r in matched[:2]]}")

# 边界: 极短输入
print("\n" + "="*80)
print("🧪 边界: 极短输入")
print("="*80)
for txt in ["嗯", "好", "去", "yes", "1", "啊", "？", "!"]:
    kws = kb._extract_keywords(txt)
    results = kb.query(keywords=kws)
    print(f"  '{txt}' → kws={kws}, 匹配={len(results)}")
