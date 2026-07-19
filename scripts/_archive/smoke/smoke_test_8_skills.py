"""8 SKILL 烟雾测试"""
import json, sys
sys.path.insert(0, "src")

from history_footnote.dm_skills import (
    run_all_skills, skill_1_assess_scene, skill_2_decide_pacing,
    skill_3_plan_lead, skill_4_anchor_history, skill_5_activate_voices,
    skill_6_handle_failure, skill_7_three_layer_verdict, skill_8_lock_cognitive_frame,
    SceneAssessment, PacingDecision,
)

# 加载 era.json
config = json.loads(open("eras/wanli1587/era.json").read())

print("=" * 60)
print("8 SKILL 烟雾测试")
print("=" * 60)

# 场景 1: 玩家第一次进入盛泽镇
print("\n【场景 1】玩家第一次进入盛泽镇，问行情")
state = {
    "round_number": 1,
    "action_points_current": 3,
    "current_date": "1587年1月",
    "variables": {"livelihood": 6, "silver_pressure": 3, "tax_burden": 4},
    "unlocked_insights": [],
    "value_shifts": {},
    "selected_identity": "weaving_male",
    "triggered_events": [],
}
ctx = run_all_skills(
    "我去镇东牙行和牙人谈今年丝价行情", state, config,
    recent_scenes=[], recent_inputs=[], idle_rounds=0,
)
print(f"  读场: engagement={ctx.scene.engagement}, tension={ctx.scene.tension}, route={ctx.scene.route_tendency or '未明'}")
print(f"  节奏: {ctx.pacing.time_mode} (detail={ctx.pacing.detail_level})")
print(f"  史实锚点: {ctx.historical.description if ctx.historical else '无'}")
print(f"  线索: {ctx.lead.lead_type if ctx.lead else '无'} - {ctx.lead.lead_content if ctx.lead else ''}")
print(f"  声音: {[v.voice_name for v in ctx.voices]}")
print(f"  框架: {ctx.cognitive_frame.frame_id if ctx.cognitive_frame else '无'}")
print(f"  三层裁判: {ctx.three_layer.layer}/{ctx.three_layer.verdict}")
print(f"  失败叙事: {ctx.failure.conversion if ctx.failure else '无（本回合无失败）'}")

# 场景 2: 玩家卡在织机前重复
print("\n【场景 2】玩家连续 3 回合做相同事（空转）")
state["round_number"] = 5
ctx = run_all_skills(
    "我去织机前织布", state, config,
    recent_scenes=["织机/作坊"]*3, recent_inputs=["我去织机前织布"]*3, idle_rounds=3,
)
print(f"  读场: engagement={ctx.scene.engagement}, deviation={ctx.scene.deviation}")
print(f"  节奏: {ctx.pacing.time_mode} (correction={ctx.pacing.correction_type})")
print(f"  扶正: {ctx.pacing.correction_needed} → 投放{ctx.lead.lead_type if ctx.lead else '无'}: {ctx.lead.lead_content if ctx.lead else ''}")

# 场景 3: 史实锚点触发（倭寇警报）
print("\n【场景 3】第 8 回合——倭寇警报（史实锚点）")
state["round_number"] = 8
ctx = run_all_skills(
    "我去看看牙行", state, config,
    recent_scenes=["牙行/市集"], recent_inputs=["我去找牙行"], idle_rounds=0,
)
print(f"  史实锚点: {ctx.historical.description if ctx.historical else '无'}")
print(f"  节奏: {ctx.pacing.time_mode} (锚点时_mode={ctx.historical.time_mode if ctx.historical else '?'})")
print(f"  线索: {ctx.lead.lead_type if ctx.lead else '无'} - {ctx.lead.lead_content if ctx.lead else ''}")

# 场景 4: 玩家说"去京城见皇帝"（触发铁律）
print("\n【场景 4】玩家说'去京城见皇帝'（违反铁律）")
ctx = run_all_skills(
    "我要去京城见皇帝", state, config,
    recent_scenes=[], recent_inputs=[], idle_rounds=0,
)
print(f"  三层裁判: {ctx.three_layer.layer}/{ctx.three_layer.verdict}")
print(f"  叙事化约束: {ctx.three_layer.narrative_constraint[:80] if ctx.three_layer.narrative_constraint else '无'}")

# 场景 5: 玩家走科举路线（被识别）
print("\n【场景 5】玩家关注科举")
state["unlocked_insights"] = ["ins_imperial_exam"]
ctx = run_all_skills(
    "我想去打听今年的乡试", state, config,
    recent_scenes=[], recent_inputs=["听说今年乡试提前了"], idle_rounds=0,
)
print(f"  路线: {ctx.scene.route_tendency}")
print(f"  框架: {ctx.cognitive_frame.frame_id if ctx.cognitive_frame else '无'}")
if ctx.cognitive_frame:
    print(f"  突出: {ctx.cognitive_frame.highlight[:2]}")
    print(f"  抑制: {ctx.cognitive_frame.suppress[:2]}")

# 场景 6: 玩家失败（如织机崩了）
print("\n【场景 6】玩家说'我织一匹好湖绫'（失败叙事化）")
ctx = run_all_skills(
    "我想织一匹上等的湖绫", state, config,
    recent_scenes=[], recent_inputs=[], idle_rounds=0,
    failure_type="action",
)
print(f"  失败类型: {ctx.failure.failure_type}")
print(f"  转化: {ctx.failure.conversion[:100] if ctx.failure.conversion else '无'}")

print("\n" + "=" * 60)
print("✅ 8 SKILL 全部跑通")
print("=" * 60)
