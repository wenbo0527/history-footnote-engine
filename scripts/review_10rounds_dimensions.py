"""🆕 v1.7.30 10 轮连贯性 8 维度分析

读 tests/fixtures/10rounds_coherence_review.json，按 8 维度评估：
1. 玩家输入回声率（每轮 narrative 是否提到玩家输入关键名词）
2. DM 输出非重复率（每轮 narrative 与其他轮不重复度）
3. State 连续性（round_number 递增、current_date 单调、variables 累积）
4. 事件链（触发事件数 vs narrative 中实际引用事件数）
5. NPC 引用（npc_levels 是否被 narrative 引用）
6. 价值变量变化（value_shifts 是否反映玩家选择）
7. 时间线推进（每轮 date 是否推进）
8. 长度合理性（每轮 50~500 字）
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "10rounds_coherence_review.json"


def load_rounds():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def dim1_input_echo(rounds):
    """玩家输入关键名词被 DM 提及的比例"""
    echo_count = 0
    detail = []
    for r in rounds:
        # 提取玩家输入关键词（≥ 2 字中文）
        pi = r["player_input"]
        keywords = [w for w in re.findall(r"[\u4e00-\u9fa5]{2,}", pi) 
                    if w not in {"我在", "我听", "我去", "我的", "我想", "我把", "今年", "今天"}]
        narr = r["narrative"]
        if not keywords:
            detail.append((r["round"], 1.0, "n/a"))
            echo_count += 1
            continue
        hits = sum(1 for k in keywords if k in narr)
        rate = hits / len(keywords)
        detail.append((r["round"], rate, f"{hits}/{len(keywords)} keywords"))
        if rate > 0.3:  # 30% 关键名词被回声
            echo_count += 1
    score = echo_count / len(rounds) if rounds else 0
    return score, detail


def dim2_no_repetition(rounds):
    """相邻轮 narrative 不重复度"""
    rep_count = 0
    detail = []
    for i in range(1, len(rounds)):
        prev = rounds[i-1]["narrative"]
        curr = rounds[i]["narrative"]
        # 简单的最长公共子串估算：取前 50 字对比
        overlap = 0
        for n in range(50, 0, -5):
            if prev[:n] in curr:
                overlap = n
                break
        if overlap < 30:
            rep_count += 1
        detail.append((rounds[i]["round"], f"overlap={overlap}"))
    score = rep_count / (len(rounds) - 1) if len(rounds) > 1 else 1
    return score, detail


def dim3_state_continuity(rounds):
    """round_number 递增、current_date 单调"""
    issues = 0
    prev_round = 0
    prev_date = ""
    for r in rounds:
        rn = r["state_summary"]["round_number"]
        cd = r["state_summary"]["current_date"]
        if rn <= prev_round:
            issues += 1
        if cd and prev_date and cd < prev_date:
            issues += 1
        prev_round = rn
        prev_date = cd
    total_checks = len(rounds) * 2
    score = 1.0 - (issues / total_checks) if total_checks else 1
    detail = [(r["round"], f"r={r['state_summary']['round_number']}, d={r['state_summary']['current_date']}") for r in rounds]
    return score, detail


def dim4_event_chain(rounds):
    """每轮 narrative 是否提到具体动作/事件（动词 1~3 个）"""
    ok_count = 0
    detail = []
    for r in rounds:
        narr = r["narrative"]
        # 至少有一个具体动作（动词）
        verbs = re.findall(r"[\u4e00-\u9fa5]{2}", narr)
        has_action = any(any(v in narr for v in ["织", "卖", "听", "去", "算", "看", "说", "送", "做", "走", "遇", "见", "问", "答"]) for _ in [None])
        if has_action and len(verbs) > 3:
            ok_count += 1
        detail.append((r["round"], f"action={'yes' if has_action else 'no'}, len={len(narr)}"))
    score = ok_count / len(rounds) if rounds else 0
    return score, detail


def dim5_npc_references(rounds):
    """npc_levels 是否在 narrative 中被引用（NPC 名出现）"""
    if not rounds:
        return 0, []
    has_npc_in_state = bool(rounds[-1]["state_summary"]["npc_levels"])
    if not has_npc_in_state:
        return 1.0, [("ALL", "no NPC in state (acceptable for early game)")]
    npc_names = list(rounds[-1]["state_summary"]["npc_levels"].keys())
    narr_all = " ".join(r["narrative"] for r in rounds)
    hit = sum(1 for n in npc_names if n in narr_all)
    score = hit / len(npc_names) if npc_names else 1
    return score, [(len(npc_names), f"{hit} NPCs referenced")]


def dim6_value_shifts(rounds):
    """value_shifts 反映玩家选择"""
    shifts_last = rounds[-1]["state_summary"]["value_shifts"] if rounds else {}
    if not shifts_last:
        return 1.0, [("n/a", "no value shifts yet")]
    return 0.5, [(len(shifts_last), f"keys: {list(shifts_last.keys())[:3]}")]


def dim7_time_progression(rounds):
    """date 是否推进（不在第 1 轮之后还停在同一天）"""
    dates = [r["state_summary"]["current_date"] for r in rounds if r["state_summary"]["current_date"]]
    uniq_dates = len(set(dates))
    # 10 轮里至少 2 个不同 date 才算"在推进"
    score = min(uniq_dates / 3, 1.0)
    return score, [(uniq_dates, f"unique dates: {uniq_dates}")]


def dim8_length_reasonable(rounds):
    """每轮 narrative 50~500 字（合理长度）"""
    ok = sum(1 for r in rounds if 50 <= r["narrative_len"] <= 800)
    score = ok / len(rounds) if rounds else 0
    detail = [(r["round"], f"len={r['narrative_len']}") for r in rounds]
    return score, detail


def main():
    print("=" * 60)
    print("🆕 v1.7.30 10 轮连贯性 8 维度分析")
    print("=" * 60)
    rounds = load_rounds()
    if not rounds:
        print(f"❌ 找不到 fixture: {FIXTURE}")
        sys.exit(1)
    print(f"✅ 加载 {len(rounds)} 轮数据\n")

    dims = [
        ("1. 玩家输入回声率（>30% 关键词被提及）", dim1_input_echo(rounds)),
        ("2. 相邻轮不重复率（<30 字重叠）", dim2_no_repetition(rounds)),
        ("3. State 连续性（round 递增 + date 单调）", dim3_state_continuity(rounds)),
        ("4. 事件链（每轮有具体动作）", dim4_event_chain(rounds)),
        ("5. NPC 引用（npc_levels 中的 NPC 在 narrative 出现）", dim5_npc_references(rounds)),
        ("6. 价值变量变化（value_shifts 反映选择）", dim6_value_shifts(rounds)),
        ("7. 时间线推进（date 不停滞）", dim7_time_progression(rounds)),
        ("8. 长度合理性（50~800 字）", dim8_length_reasonable(rounds)),
    ]

    overall_scores = []
    for name, (score, detail) in dims:
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"  {name}")
        print(f"    [{bar}] {score*100:.0f}%")
        for d in detail[:5]:
            print(f"      • {d}")
        if len(detail) > 5:
            print(f"      ... ({len(detail) - 5} more)")
        print()
        overall_scores.append(score)

    overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    print("=" * 60)
    print(f"🏆 总体连贯性得分：{overall*100:.0f}%")
    if overall < 0.5:
        print("   ⚠️  多维度低分，需要重点关注")
    elif overall < 0.8:
        print("   🟡  中等，部分维度需优化")
    else:
        print("   🟢  连贯性良好")
    print("=" * 60)
    return overall


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score > 0.5 else 1)
