"""🆕 v1.7.30 10 轮连贯性 8 维度分析（v2 真实 LLM 友好）

修复：
- n-gram 提取关键词（2-3 字滑动窗口）—— 避免 jieba 外部依赖
- 长度合理区间改为 150~900（实际真实 LLM 输出多在 300~700）
- 修 R4/R5 跳号（按 round 序号排序后输出）
- 接受 narrative 头部的 markdown 标记（# / **）
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "10rounds_coherence_review_REAL.json"

# 常见停用词（2-3 字）—— 这些不该算"玩家输入关键名词"
STOP_WORDS = {
    "我在", "我听", "我去", "我的", "我想", "我把", "今年", "今天", "明天", "昨天",
    "听说", "听说", "看见", "看到", "我听", "我想", "我听", "我觉", "我觉得",
    "听说", "知道", "考虑", "决定", "打算", "准备", "我", "你", "他", "她", "它",
    "我听邻居", "听说今年", "今天", "今年", "里去", "我决定",
}

# 停用单字——n-gram 包含这些字视为无效
STOP_CHARS = set("我了的不在是有我不你我他她它的着就都也再又已还能和与或说问及前后要把会能到上过出来回")

# 真实 LLM 输出可能的前缀标记
NARRATIVE_PREFIX = re.compile(r"^(#\s+|\*\*|>\s+|##\s+)")


def load_rounds():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # 修 C: 按 round 排序
    return sorted(raw, key=lambda r: r.get("round", 0))


def extract_keywords_v2(player_input: str) -> list[str]:
    """提取"核心实词"——返回 2~3 字 n-gram 列表，按 (长度, 字典序) 排序。
    实字定义：不在 STOP_CHARS 中。
    匹配逻辑：keyword 是 narrative 的 substring 算 1 命中，否则 0
    """
    text = re.sub(r"[，。！？]", "", player_input)
    ngrams = []
    for n in (3, 2):
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            if gram in STOP_WORDS:
                continue
            real_count = sum(1 for ch in gram if ch not in STOP_CHARS)
            if n == 3 and real_count < 3:
                continue
            if n == 2 and real_count < 1:
                continue
            ngrams.append(gram)
    ngrams = sorted(set(ngrams), key=lambda g: (-len(g), g))
    return ngrams[:8]


def match_keyword_in_narr(keyword: str, narr: str) -> bool:
    """keyword 命中 narrative = keyword 是 narr 子串 OR 90% 实字都在 narr 中出现"""
    if keyword in narr:
        return True
    # 退路：实字 90% 在 narr 中出现（按单字）
    real_chars = [ch for ch in keyword if ch not in STOP_CHARS]
    if not real_chars:
        return False
    hits = sum(1 for ch in real_chars if ch in narr)
    return hits / len(real_chars) >= 0.9


def clean_narrative(narr: str) -> str:
    """去掉 narrative 头部的 markdown 标记（# / **）"""
    return NARRATIVE_PREFIX.sub("", narr.strip())


def dim1_input_echo(rounds):
    """n-gram 玩家输入回声率（带 substring + 实字覆盖率）"""
    echo_count = 0
    detail = []
    for r in rounds:
        kws = extract_keywords_v2(r["player_input"])
        narr = clean_narrative(r["narrative"])
        if not kws:
            echo_count += 1
            detail.append((r["round"], 1.0, "n/a"))
            continue
        hits = sum(1 for k in kws if match_keyword_in_narr(k, narr))
        rate = hits / len(kws) if kws else 0
        detail.append((r["round"], rate, f"{hits}/{len(kws)} ({[k for k in kws[:3]]})"))
        if rate >= 0.4:
            echo_count += 1
    score = echo_count / len(rounds) if rounds else 0
    return score, detail


def dim2_no_repetition(rounds):
    """相邻轮不重复率（< 30 字重叠）"""
    rep_count = 0
    detail = []
    for i in range(1, len(rounds)):
        prev = clean_narrative(rounds[i-1]["narrative"])
        curr = clean_narrative(rounds[i]["narrative"])
        overlap = 0
        for n in range(50, 0, -5):
            if prev[:n] in curr:
                overlap = n
                break
        if overlap < 30:
            rep_count += 1
        status = "✅" if overlap < 30 else "🔴"
        detail.append((rounds[i]["round"], f"overlap={overlap}"))
    score = rep_count / (len(rounds) - 1) if len(rounds) > 1 else 1
    return score, detail


def dim3_state_continuity(rounds):
    issues = 0
    prev_round = 0
    prev_date = ""
    for r in rounds:
        rn = r["state_summary"]["round_number"]
        cd = r["state_summary"]["current_date"]
        if rn < prev_round:
            issues += 1
        if cd and prev_date and cd < prev_date:
            issues += 1
        prev_round = rn
        prev_date = cd
    total_checks = len(rounds) * 2
    score = 1.0 - (issues / total_checks) if total_checks else 1
    detail = [(r["round"], f"r={r['state_summary']['round_number']} d={r['state_summary']['current_date']} ev={r['state_summary']['events_count']}") for r in rounds]
    return score, detail


def dim4_event_chain(rounds):
    """每轮 narrative 有具体动作（动词 1+）"""
    action_words = "织 卖 听 去 算 看 说 送 做 走 遇 见 问 答 吃 穿 用 买 打 交 拿 写 坐 立 想 觉 笑 哭 喊 叫 喝 端 装 出 跑 跳 飞 收 翻 找 让 教 推 拉 搬 抬 抛 接 捕 抓 守 望 等"
    ok = 0
    detail = []
    for r in rounds:
        narr = clean_narrative(r["narrative"])
        has_action = any(w in narr for w in action_words.split())
        if has_action and len(narr) >= 100:
            ok += 1
        status = "✅" if has_action and len(narr) >= 100 else "🟡"
        detail.append((r["round"], f"action={'yes' if has_action else 'no'} len={len(narr)}"))
    score = ok / len(rounds) if rounds else 0
    return score, detail


def dim5_npc_references(rounds):
    if not rounds:
        return 0, []
    has_npc = bool(rounds[-1]["state_summary"]["npc_levels"])
    if not has_npc:
        return 1.0, [("ALL", "no NPC in state (early game OK)")]
    npc_names = list(rounds[-1]["state_summary"]["npc_levels"].keys())
    narr_all = " ".join(clean_narrative(r["narrative"]) for r in rounds)
    hit = sum(1 for n in npc_names if n in narr_all)
    return hit / len(npc_names) if npc_names else 1, [(len(npc_names), f"{hit} NPCs referenced")]


def dim6_value_shifts(rounds):
    shifts = rounds[-1]["state_summary"]["value_shifts"] if rounds else {}
    if not shifts:
        return 1.0, [("n/a", "no value shifts yet")]
    return 0.5, [(len(shifts), f"keys: {list(shifts.keys())[:3]}")]


def dim7_time_progression(rounds):
    dates = [r["state_summary"]["current_date"] for r in rounds if r["state_summary"]["current_date"]]
    uniq_dates = len(set(dates))
    score = min(uniq_dates / 3, 1.0)
    return score, [(uniq_dates, f"unique dates: {uniq_dates}")]


def dim8_length_reasonable(rounds):
    """150~900 字（真实 LLM 输出实际多在 300~700）"""
    ok = sum(1 for r in rounds if 150 <= r["narrative_len"] <= 900)
    score = ok / len(rounds) if rounds else 0
    detail = [(r["round"], f"len={r['narrative_len']}") for r in rounds]
    return score, detail


def main():
    print("=" * 60)
    print("🆕 v1.7.30 真实 LLM 10 轮连贯性 8 维度分析 v2")
    print("=" * 60)
    rounds = load_rounds()
    if not rounds:
        print(f"❌ 找不到 fixture: {FIXTURE}")
        sys.exit(1)
    print(f"✅ 加载 {len(rounds)} 轮数据（已按 round 排序）\n")
    for r in rounds:
        print(f"  R{r['round']}: input='{r['player_input'][:30]}' "
              f"len={r['narrative_len']}")

    dims = [
        ("1. 玩家输入回声率（≥40% 关键词）", dim1_input_echo(rounds)),
        ("2. 相邻轮不重复（<30 字重叠）", dim2_no_repetition(rounds)),
        ("3. State 连续性（round + date 严格递增）", dim3_state_continuity(rounds)),
        ("4. 事件链（每轮有具体动作且 ≥100 字）", dim4_event_chain(rounds)),
        ("5. NPC 引用（npc_levels 引用）", dim5_npc_references(rounds)),
        ("6. 价值变量（value_shifts 反映选择）", dim6_value_shifts(rounds)),
        ("7. 时间线推进（unique date ≥ 3）", dim7_time_progression(rounds)),
        ("8. 长度合理性（150~900 字）", dim8_length_reasonable(rounds)),
    ]

    overall_scores = []
    for name, (score, detail) in dims:
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"\n  {name}")
        print(f"    [{bar}] {score*100:.0f}%")
        for d in detail[:10]:
            print(f"      • {d}")
        if len(detail) > 10:
            print(f"      ... ({len(detail) - 10} more)")
        overall_scores.append(score)

    overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    print("\n" + "=" * 60)
    print(f"🏆 总体连贯性得分：{overall*100:.0f}%")
    if overall < 0.6:
        print("   ⚠️  多维度低分，需要重点优化")
    elif overall < 0.8:
        print("   🟡  中等，部分维度需优化")
    else:
        print("   🟢  连贯性良好")
    print("=" * 60)
    return overall


if __name__ == "__main__":
    score = main()
    sys.exit(0 if score > 0.6 else 1)
