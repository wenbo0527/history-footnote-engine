"""测试 _detect_intent_type 关键词识别"""
import sys
sys.path.insert(0, "src")
from history_footnote.dm_skills import _detect_intent_type

tests = [
    ('我在织机前织布', 'action'),
    ('我去看看窗外', 'inquire'),
    ('我所在的盛泽镇是江南最繁华的丝织市镇', 'describe'),
    ('我是从福建逃难来的破产绸缎商人', 'describe'),
    ('我家在盛泽镇西市巷', 'describe'),
    ('我问问邻居张三', 'inquire'),
    ('我去苏州城里一趟', 'action'),
    ('我瞧瞧外面的情况', 'inquire'),
    ('我去打听科举消息', 'inquire'),
    ('我去牙行和牙人谈丝价', 'inquire'),
    ('我去织机前织布', 'action'),
    ('我把织好的湖绫拿去卖了', 'action'),
]

passed = 0
for inp, expected in tests:
    actual = _detect_intent_type(inp)
    mark = '✅' if actual == expected else '❌'
    if actual == expected:
        passed += 1
    print(f"{mark} {inp[:35]:35} → {actual:10} (期望 {expected})")

print(f"\n通过率: {passed}/{len(tests)} = {passed/len(tests)*100:.0f}%")