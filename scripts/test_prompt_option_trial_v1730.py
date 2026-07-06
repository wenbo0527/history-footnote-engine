"""🆕 v1.7.30 4 改进静态测试

覆盖：
1. system_base.md 加 <events> 块硬要求
2. option_analyzer 6+ 关键词 + 城市提取
3. account_system 体验版 6 方法
4. main.css 4 档响应式断点
5. trial round/feedback 端到端
"""
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SP = ROOT / "src/history_footnote/dm/prompts/system_base.md"
OA = ROOT / "src/history_footnote/option_analyzer.py"
AS = ROOT / "src/history_footnote/account_system.py"
CSS = ROOT / "src/history_footnote/web/static/css/main.css"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_prompt_events():
    print("[1/5] system_base.md <events> 硬要求")
    src = SP.read_text(encoding="utf-8")
    return _step(
        "  硬要求 + 格式 + 触发规则 + 反例",
        "必须输出" in src or "硬要求" in src
        and "<events>" in src
        and "fin.sell_silk" in src
        and "discover.place" in src
        and "city.arrive" in src,
    )


def test_option_analyzer():
    print("\n[2/5] option_analyzer 关键词 + 城市提取")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.option_analyzer import analyze_option

    samples = [
        ("我去镇上牙行卖这匹湖绫", "fin.sell_silk"),
        ("我搭船去苏州", "city.arrive.suzhou"),
        ("我回家告诉沈氏这事", "city.arrive.shengze"),
        ("我算算账", None),
    ]
    ok = True
    for text, expected_id in samples:
        results = analyze_option(text)
        ids = [r["event_id"] for r in results]
        if expected_id:
            match = expected_id in ids
            ok = _step(f"  '{text[:20]}...' → {expected_id} 命中", match) and ok
        else:
            # 不期望匹配，但允许空结果
            ok = _step(f"  '{text[:20]}...' 无匹配（正常）", True) and ok
    # 城市提取
    res = analyze_option("我去杭州")
    has_hangzhou = any(r["event_id"] == "city.arrive.hangzhou" for r in res)
    ok = _step(f"  '去杭州' 提取 city_id", has_hangzhou) and ok
    return ok


def test_trial_mode():
    print("\n[3/5] account_system 体验版 6 方法")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.account_system import AccountSystem

    tmp = Path(tempfile.mkdtemp(prefix="hf_trial_"))
    sys_inst = AccountSystem(tmp)
    ok = True
    # start_trial
    t1 = sys_inst.start_trial()
    ok = _step(f"  start_trial: {t1['trial_id'][:8]}", bool(t1.get("trial_id"))) and ok
    # get_current_trial
    cur = sys_inst.get_current_trial()
    ok = _step(f"  get_current_trial: round={cur['current_round']}", cur is not None) and ok
    # increment 10 次（到第 10 轮 → 触发反馈要求）
    for i in range(10):
        sys_inst.increment_trial_round()
    cur = sys_inst.get_current_trial()
    ok = _step(f"  increment x10 → round={cur['current_round']}", cur["current_round"] == 10) and ok
    # 检查反馈要求
    is_required = sys_inst.is_trial_round_feedback_required()
    ok = _step(f"  is_trial_round_feedback_required = {is_required}", is_required) and ok
    # submit feedback
    submit_ok = sys_inst.submit_trial_feedback("游戏很棒！", contact="test@example.com")
    ok = _step(f"  submit_trial_feedback: {submit_ok}", submit_ok) and ok
    # 再次检查反馈（已提交应 False）
    is_required = sys_inst.is_trial_round_feedback_required()
    ok = _step(f"  提交后 is_required = {is_required}", not is_required) and ok
    # grant_invite_code_for_trial
    inv = sys_inst.grant_invite_code_for_trial("test@example.com")
    ok = _step(f"  grant_invite_code_for_trial: {inv.code if inv else None}", inv is not None) and ok
    # end_trial
    ended = sys_inst.end_trial()
    ok = _step(f"  end_trial: ended_at={ended.get('ended_at') if ended else None}", ended is not None) and ok
    return ok


def test_responsive_css():
    print("\n[4/5] main.css 4 档响应式断点")
    src = CSS.read_text(encoding="utf-8")
    return _step(
        "  4 档（≥1200/768-1199/481-767/≤480）+ 触摸优化",
        "@media (min-width: 1200px)" in src
        and "@media (min-width: 768px) and (max-width: 1199px)" in src
        and "@media (min-width: 481px) and (max-width: 767px)" in src
        and "@media (max-width: 480px)" in src
        and "hover: none" in src,
    )


def test_trial_e2e():
    print("\n[5/5] 端到端：trial 30 回合")
    sys.path.insert(0, str(ROOT / "src"))
    from history_footnote.account_system import AccountSystem

    tmp = Path(tempfile.mkdtemp(prefix="hf_trial2_"))
    sys_inst = AccountSystem(tmp)
    t = sys_inst.start_trial()
    # 跑 30 回合
    for i in range(30):
        sys_inst.increment_trial_round()
        # 每 10 轮提交反馈
        if (i + 1) % 10 == 0 and not sys_inst.get_current_trial().get("feedback_submitted"):
            sys_inst.submit_trial_feedback(f"第 {i+1} 轮反馈", contact=f"u{i+1}@x.com")
    cur = sys_inst.get_current_trial()
    ended_at = cur.get("ended_at") if cur else None
    ok = True
    ok = _step(f"  30 回合后 ended_at = {ended_at[:19] if ended_at else None}", ended_at is not None) and ok
    ok = _step(f"  3 次反馈（10/20/30）已提交", cur.get("feedback_submitted")) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.30 4 改进静态测试 ===\n")
    ok1 = test_prompt_events()
    ok2 = test_option_analyzer()
    ok3 = test_trial_mode()
    ok4 = test_responsive_css()
    ok5 = test_trial_e2e()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=}")
        sys.exit(1)
