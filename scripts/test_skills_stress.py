"""
压力测试：8 个 DM Skill 在刁钻玩家输入下的表现
不调 LLM，只跑 skill logic（run_all_skills）+ knowledge base query
"""
import json
import sys
from pathlib import Path

# 加 src 到 path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from history_footnote.dm_skills import run_all_skills, skill_1_assess_scene
from history_footnote.knowledge_base import KnowledgeBase

# ===== 加载 era config =====
era_path = ROOT / "eras" / "wanli1587" / "era.json"
era_config = json.loads(era_path.read_text(encoding="utf-8"))
print(f"✅ 加载 era.json ({era_path.stat().st_size // 1024}KB)")

# ===== 构造 KnowledgeBase =====
# era.json 中 knowledge entries 实际在 era.knowledge.entries（不在 world 下）
kb_entries = era_config.get("knowledge", {}).get("entries", [])
narrative_snippets = era_config.get("narrative_snippets", [])
story_segments = era_config.get("story_segments", {})

# 看实际数据
print(f"  knowledge entries: {len(kb_entries)} 条")
print(f"  narrative snippets: {len(narrative_snippets)} 条")
print(f"  story segments scenes: {len(story_segments)} 个")

# 检查前几条
if kb_entries:
    print(f"\n  📄 示例 entry: {kb_entries[0].get('id')} | layer={kb_entries[0].get('layer')}")
    print(f"     trigger_keywords: {kb_entries[0].get('trigger_keywords', [])[:5]}")

# ===== 准备刁钻玩家输入 =====
# 设计原则：覆盖各类典型"塌房"场景
TEST_INPUTS = [
    # === 正常输入（对照组）===
    ("normal_01", "我去镇上看看", {"round": 1, "idle": 0, "recent_scenes": []}),
    ("normal_02", "先看看家里情况", {"round": 1, "idle": 0, "recent_scenes": []}),

    # === 空转类 ===
    ("stuck_01", "嗯", {"round": 1, "idle": 5, "recent_scenes": ["茶馆", "茶馆"]}),
    ("stuck_02", "（再想想）", {"round": 1, "idle": 4, "recent_scenes": ["作坊", "作坊"]}),

    # === 试图突破时代限制 ===
    ("iron_01", "我要去京城见皇帝", {"round": 1, "idle": 0, "recent_scenes": []}),
    ("iron_02", "我准备造反", {"round": 1, "idle": 0, "recent_scenes": []}),
    ("iron_03", "我去科举考试", {"round": 1, "idle": 0, "recent_scenes": []}),

    # === 身份不符 ===
    ("identity_01", "我去织一匹绸", {"round": 1, "idle": 0, "recent_scenes": []}),  # 商贩
    ("identity_02", "我去种田", {"round": 1, "idle": 0, "recent_scenes": []}),  # 织工

    # === 关键词误匹配（潜在塌房）===
    ("kw_01", "今日天气", {"round": 1, "idle": 0, "recent_scenes": []}),
    ("kw_02", "云南和山西哪个好", {"round": 1, "idle": 0, "recent_scenes": []}),
    ("kw_03", "我想出家当和尚", {"round": 1, "idle": 0, "recent_scenes": []}),
    ("kw_04", "我家有桑田百亩", {"round": 1, "idle": 0, "recent_scenes": []}),

    # === 高情感 + 长输入 ===
    ("emotional_01", "怎么办怎么办怎么办怎么办怎么办怎么办", {"round": 1, "idle": 0, "recent_scenes": []}),
    ("emotional_02", "我想去杭州投奔远房亲戚避乱", {"round": 1, "idle": 0, "recent_scenes": []}),

    # === 中文标点 === (测试!识别)
    ("punct_01", "太好了！我要去！", {"round": 1, "idle": 0, "recent_scenes": []}),

    # === describe (DE 风格) ===
    ("describe_01", "我叫沈青山，是个倔强的织工", {"round": 1, "idle": 0, "recent_scenes": []}),

    # === inquire (问询) ===
    ("inquire_01", "先看看家里有什么", {"round": 1, "idle": 0, "recent_scenes": []}),

    # === 史实锚点临近 ===
    ("anchor_01", "我听说矿税监要来", {"round": 38, "idle": 0, "recent_scenes": []}),  # 万历二十四年

    # === 已触发锚点（防止重复触发） ===
    ("anchor_02", "再聊聊矿税监的事", {"round": 50, "idle": 0, "recent_scenes": [],
     "triggered": ["minimax_evil_burglar_inspector_39"]}),
]

# ===== 构造 state factory =====
def make_state(round_num, idle, recent_scenes, triggered=None):
    return {
        "current_date": f"万历{14 + round_num // 12}年",
        "round_number": round_num,
        "triggered_events": triggered or [],
        "value_shifts": {"tradition_vs_change": 0, "pragmatism_vs_idealism": 1},
        "variables": {"cash": 1.2, "debt": 3.6, "reputation": 5},
        "unlocked_insights": [],
        "selected_identity": "weaving_male",
        "route_tendency": "",
        "player_idle_rounds": idle,
    }

# ===== 构造 KB =====
kb = KnowledgeBase(
    entries=kb_entries,
    snippets=narrative_snippets,
    story_segments=story_segments,
)

# ===== 跑测试 =====
print("\n" + "=" * 80)
print("🔥 压力测试：8 个 DM Skill × 20+ 玩家输入")
print("=" * 80)

RED_FLAGS = []

for test_id, player_input, ctx in TEST_INPUTS:
    print(f"\n📌 [{test_id}] {player_input[:40]}{'...' if len(player_input) > 40 else ''}")
    print(f"   round={ctx['round']} | idle={ctx['idle']} | scenes={ctx['recent_scenes']}")

    state = make_state(ctx['round'], ctx['idle'], ctx['recent_scenes'],
                       ctx.get('triggered'))

    # === 1. 跑 skill_1（最容易出问题） ===
    assessment = skill_1_assess_scene(
        player_input, state, era_config, ctx['recent_scenes'], [], ctx['idle']
    )

    print(f"   🎯 SKILL-1: 投入={assessment.engagement} 情绪={assessment.emotion} "
          f"张力={assessment.tension} 路线={assessment.route_tendency or '未明'}")

    # 红旗：检测潜在塌房
    if assessment.engagement == "high" and len(player_input) < 30 and "!" not in player_input and "！" not in player_input:
        RED_FLAGS.append(f"[{test_id}] 输入只有{len(player_input)}字却判定 high engagement")
    if assessment.route_tendency == "monk" and "和尚" not in player_input:
        RED_FLAGS.append(f"[{test_id}] 没提'和尚'但被判定 monk 路线")
    if assessment.route_tendency == "imperial_exam" and not any(kw in player_input for kw in ["科举", "考试", "秀才", "进学", "书院", "县学"]):
        RED_FLAGS.append(f"[{test_id}] 没提科举相关但被判 imperial_exam")

    # === 2. 跑 skill_2（决策） ===
    from history_footnote.dm_skills import skill_2_decide_pacing
    pacing = skill_2_decide_pacing(assessment, era_config, state, player_input)
    print(f"   ⏱️ SKILL-2: time_mode={pacing.time_mode} detail={pacing.detail_level}/5")

    # 红旗：检测决策合理性
    if pacing.time_mode == "abstract_time" and ctx['idle'] < 3:
        RED_FLAGS.append(f"[{test_id}] idle={ctx['idle']}却触发 abstract_time（>=3 才会）")
    # 🆕 v1.7.29: slow_time 应有真问询模式
    if pacing.time_mode == "slow_time" and len(player_input) < 10:
        # 8 字慢时间：必须明确是问询（"问人/打听事"）
        # 简单判定：含"问/打听/聊聊"且含"人名/事/价格/消息"等
        has_inquire_pattern = any(p in player_input for p in ["问问", "打听", "聊聊", "请教", "请问"])
        has_object_hint = any(p in player_input for p in ["王", "赵", "李", "人", "客", "事", "消息", "价", "行情"])
        if not (has_inquire_pattern and has_object_hint):
            RED_FLAGS.append(f"[{test_id}] 输入只有{len(player_input)}字却触发 slow_time（高细节）")

    # === 3. 跑 skill_4（史实锚点） ===
    from history_footnote.dm_skills import skill_4_anchor_history
    historical = skill_4_anchor_history(era_config, state, player_input)
    if historical:
        print(f"   📜 SKILL-4: 锚点={historical.anchor_id} | 阶段={'铺垫' if historical.foreshadowing_lead else '触发'}")
    else:
        print(f"   📜 SKILL-4: 无锚点")

    # === 4. 跑 skill_7（三层裁判） ===
    from history_footnote.dm_skills import skill_7_three_layer_verdict
    verdict = skill_7_three_layer_verdict(era_config, player_input, state)
    print(f"   ⚖️ SKILL-7: {verdict.layer} | {verdict.verdict}")

    if verdict.layer == "iron" and verdict.verdict == "reject_narratively":
        print(f"      → 拒绝: {verdict.narrative_constraint[:50]}")

    # === 5. 测 knowledge_base 关键词匹配 ===
    extracted_kws = kb._extract_keywords(player_input)
    matched = kb.query(keywords=extracted_kws)[:3]
    if matched:
        print(f"   📚 KB 匹配: {len(matched)} 条")
        for m in matched[:2]:
            print(f"      - {m.get('id', '?')[:40]} (layer={m.get('layer', '?')})")

    # 红旗：KB 匹配数过多 = 关键词误匹配
    if len(matched) > 5:
        RED_FLAGS.append(f"[{test_id}] KB 匹配{len(matched)}条（>5可能误匹配）")

# ===== 总结 =====
print("\n" + "=" * 80)
print("📊 测试结果")
print("=" * 80)
print(f"总测试数: {len(TEST_INPUTS)}")
print(f"红旗数: {len(RED_FLAGS)}")

if RED_FLAGS:
    print(f"\n🚨 红旗清单（潜在塌房）:")
    for flag in RED_FLAGS:
        print(f"  • {flag}")
else:
    print("\n✅ 无红旗")

# ===== 边界 case 测试 =====
print("\n" + "=" * 80)
print("🔬 边界 case 详细分析")
print("=" * 80)

# 1. 关键词误匹配 - "今日天气"
print("\n[边界 1] '今日天气' 提取的关键词:")
print(f"  {kb._extract_keywords('今日天气')}")
print(f"  匹配数: {len(kb.query(keywords=kb._extract_keywords('今日天气')))}")

# 2. 云南 / 山西 误匹配
print("\n[边界 2] '云南和山西哪个好' 提取的关键词:")
print(f"  {kb._extract_keywords('云南和山西哪个好')}")
print(f"  匹配数: {len(kb.query(keywords=kb._extract_keywords('云南和山西哪个好')))}")
print(f"  实际匹配: {[e.get('id', '?') for e in kb.query(keywords=kb._extract_keywords('云南和山西哪个好'))[:5]]}")

# 3. SKILL-1 长度判定漏洞
print("\n[边界 3] SKILL-1 engagement 边界测试:")
test_lengths = ["好", "好呀", "好呀好呀好呀", "（沉吟片刻）", ""]
for txt in test_lengths:
    state = make_state(1, 0, [])
    a = skill_1_assess_scene(txt, state, era_config, [], [], 0)
    print(f"  '{txt or '(空)':20s}' (len={len(txt):2d}) → engagement={a.engagement}")

# 4. 已触发锚点是否真的被排除
print("\n[边界 4] 已触发的史实锚点是否被排除:")
state_with_triggered = make_state(50, 0, [], triggered=["minimax_evil_burglar_inspector_39"])
hist_with = skill_4_anchor_history(era_config, state_with_triggered, "")
state_clean = make_state(50, 0, [])
hist_clean = skill_4_anchor_history(era_config, state_clean, "")
print(f"  已触发: anchor_id={hist_with.anchor_id if hist_with else 'None'}")
print(f"  未触发: anchor_id={hist_clean.anchor_id if hist_clean else 'None'}")
