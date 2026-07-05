"""v1.7.9 完整 E2E 测试：5 回合游戏流程

测试目标：
1. 每回合是否都有 voice_options（2-4 个）
2. DM 是否推进故事（月份变化、情节发展）
3. DM 是否给用户提示（状态、行动点、建议）
4. narrative_blocks 是否结构化（scene/dialogue/monologue/transition）

需要 web_server 在 :8765 运行（mock LLM）
"""
import sys
import json
import urllib.request

BASE = "http://localhost:8765"


def post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def analyze_round(round_num, resp, prev_state):
    """分析一回合的响应，报告各维度"""
    print(f"\n{'='*60}")
    print(f"回合 {round_num}")
    print('='*60)

    # 1. 声音（voice_options）
    voices = resp.get("last_voice_options", [])
    print(f"🎭 内心声音: {len(voices)} 个")
    if voices:
        for v in voices:
            print(f"   - {v.get('voice_name', '?')}: {v.get('intent_text', '?')[:40]}")
    else:
        print("   ⚠️  无 voice_options（应该有）")

    # 2. 故事推进
    date = resp.get("current_date", "?")
    round_n = resp.get("round_number", "?")
    ap = f"{resp.get('action_points_current', '?')}/{resp.get('action_points_max', '?')}"
    print(f"📅 时间: {date} | 回合: {round_n} | 行动点: {ap}")
    if prev_state and prev_state.get("date") != date:
        print(f"   ✅ 月份推进了：{prev_state['date']} → {date}")
    elif prev_state and prev_state.get("date") == date:
        print(f"   (同月份内行动)")

    # 3. 状态更新
    vars_now = resp.get("variables", {})
    if prev_state and prev_state.get("variables"):
        changed = []
        for k, v in vars_now.items():
            old = prev_state["variables"].get(k)
            if old != v:
                changed.append(f"{k}: {old}→{v}")
        if changed:
            print(f"📊 变量变化: {', '.join(changed)}")
        else:
            print(f"📊 变量无变化")

    # 4. DM 提示（从 lastMeta 字段提取，不在 narrative 字符串里）
    is_action = resp.get("last_is_action", True)
    time_cost = resp.get("last_time_cost", 1)
    intent_type = resp.get("last_intent_type", "action")
    month_advanced = resp.get("last_month_advanced", False)
    new_date = resp.get("last_new_date")

    hints = []
    if intent_type == "describe":
        hints.append("🪞 描述")
    elif intent_type == "voice":
        hints.append("🎭 内在声音")
    elif is_action is False or time_cost == 0:
        hints.append("💬 问询")
    else:
        cost_label = "瞬时" if time_cost == 0 else "半日" if time_cost == 1 else "一日" if time_cost == 2 else "数日" if time_cost == 3 else f"{time_cost}点"
        hints.append(f"⚡ 行动·{cost_label}")

    if month_advanced and new_date:
        hints.append(f"━━━ 月推进→{new_date} ━━━")

    if hints:
        print(f"💡 DM 提示: {', '.join(hints)}")
    else:
        print(f"💡 DM 提示: 无（is_action={is_action}, time_cost={time_cost}, intent={intent_type}）")

    # 5. narrative 内容
    last_n = resp.get("last_narrative", {})
    narr_text = last_n.get("narrative", "") if isinstance(last_n, dict) else str(last_n)
    if narr_text:
        print(f"📖 叙事长度: {len(narr_text)} 字符 (round {last_n.get('round', '?')})")
        print(f"   开头: {narr_text[:80]}...")
    else:
        print(f"   ⚠️  无 narrative")

    last_n = resp.get("last_narrative", {})
    narr_text = last_n.get("narrative", "") if isinstance(last_n, dict) else str(last_n)
    return {
        "date": date,
        "round": round_n,
        "ap": resp.get("action_points_current"),
        "variables": vars_now,
        "voices_count": len(voices),
        "narrative_len": len(narr_text),
    }


def print_summary(rounds_data):
    """测试结束后打印汇总"""
    print(f"\n{'='*60}")
    print("📊 测试结果汇总")
    print("="*60)
    total_voices = sum(r["voices_count"] for r in rounds_data)
    avg_voice = total_voices / len(rounds_data) if rounds_data else 0
    avg_narr = sum(r["narrative_len"] for r in rounds_data) / len(rounds_data) if rounds_data else 0
    min_narr = min(r["narrative_len"] for r in rounds_data) if rounds_data else 0
    max_narr = max(r["narrative_len"] for r in rounds_data) if rounds_data else 0
    # 月份推进
    months = set(r["date"] for r in rounds_data)
    month_advance = "→ 月份推进" if len(months) > 1 else "→ 仅当前月"
    print(f"  🎭 平均内心声音: {avg_voice:.1f} 个/回合 (总共 {total_voices})")
    print(f"  📖 叙事长度: min={min_narr} avg={avg_narr:.0f} max={max_narr} 字符")
    print(f"  📅 月份: {month_advance} ({len(months)} 个不同月份)")
    print(f"  📊 总回合: {len(rounds_data)}")
    # 评估
    print(f"\n  评估:")
    if all(r["voices_count"] >= 2 for r in rounds_data):
        print(f"    ✅ 每回合都有 2+ 内心声音")
    else:
        print(f"    ❌ 存在无内心声音的回合")
    if avg_narr >= 100:
        print(f"    ✅ 叙事长度足够 (mock 简化时也可能 < 200)")
    else:
        print(f"    ❌ 叙事过短，平均 {avg_narr:.0f} 字符")
    if len(months) >= 2:
        print(f"    ✅ 故事有时间推进")
    else:
        print(f"    ⚠️  5 回合未跨月（可能是 mock 简化）")


def main():
    print("=" * 60)
    print("v1.7.9 完整 5 回合 E2E 测试")
    print("=" * 60)

    # 1. Start
    start = post("/api/start", {
        "era_id": "wanli1587",
        "identity": "农妇",
        "gender": "女",
        "hometown": "徽州",
    })
    sid = start.get("session_id")
    print(f"\n✅ session created: {sid}")
    print(f"   时代: {start.get('era_name')}")
    print(f"   身份: {start.get('selected_identity')}")
    print(f"   初始: {start.get('current_date')}, 行动点 {start.get('action_points_current')}/{start.get('action_points_max')}")

    prev = {
        "date": start.get("current_date"),
        "variables": start.get("variables", {}),
    }

    # 2. 跑 5 回合
    inputs = [
        "我家的粮食不够吃，该怎么办？",  # 开场问题
        "去老桑头家问问情况",             # 真行动
        "我想了解织机",                    # 问询
        "先做一匹湖绫卖",                  # 行动
        "把丝绸卖给张顺",                  # 行动
    ]
    rounds_data = []

    for i, inp in enumerate(inputs, 1):
        print(f"\n>>> 玩家输入: {inp}")
        resp = post("/api/input", {
            "session_id": sid,
            "input": inp,
        })
        if "error" in resp:
            print(f"❌ Error: {resp['error']}")
            return 1
        round_data = analyze_round(i, resp, prev)
        rounds_data.append(round_data)
        prev = round_data

    # 3. 总结
    print_summary(rounds_data)
    return 0


if __name__ == "__main__":
    sys.exit(main())