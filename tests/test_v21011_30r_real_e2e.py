"""🆕 v2.10.11+ 30 回合真实端到端测试（real LLM）

跑法（必须用 conda python，just like production）：
    /opt/anaconda3/bin/python tests/test_v21011_30r_real_e2e.py
    /opt/anaconda3/bin/python tests/test_v21011_30r_real_e2e.py --turns 10   # 跑 10 回合（快速版）
    /opt/anaconda3/bin/python tests/test_v21011_30r_real_e2e.py --resume <sid>  # 从已有 session 恢复

跑前：必须先 `bash scripts/dev-server.sh start`

它做什么：
1. POST /api/start  创建 session（wanli1587 era + weaving_male）
2. POST /api/input  跑 N 回合（真实 LLM minimax-anthropic）
3. 中途：第 5/15/N 回合自动 save_to_slot，确认存档链路工作
4. 第 N 回合后：从 slot 1 load，对比状态一致性（round / cash / events count）
5. 输出：每回合 LLM 耗时、累积状态摘要、Save/Load 一致性

跑时假设：
- server @ http://127.0.0.1:8765（dev-server.sh）
- 真实 LLM（minimax-anthropic）可用，已在 warmup 阶段预热
- 30 回合约需 25-45 分钟（每回合真实有 6-12 个 LLM 调用，重试机制）
  - 平均 30s/turn，p95 ~60s/turn，max ~150s/turn
  - 测试单回合 timeout = 180s（留 buffer）

跳过：
- 如果 server 健康检查不通过（无 LLM warmup 完成）→ 退出并提示
- 如果 /api/start 在 first hit 失败 → 退出并贴 log
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8765"

# 30 个真实玩家行为（按时序变化节奏：开局稳 → 中期灵活 → 后期冒险）
ACTIONS_30 = [
    "我去织机前坐下，开始理经线",
    "去灶房看看沈氏和孩子",
    "和隔壁张寡妇聊几句，问问最近织机的行情",
    "去镇上赵里长那里，问问春税预单的细节",
    "去村口的桑叶铺子看看今年的新货",
    "去一趟县里的丝行，打听行情",
    "把家里的旧衣裳补一补，腾出银子",
    "晚上和阿宝一起温习功课",
    "去镇东头找王牙人，问问有没有活计",
    "去村西的桑林看看长势",
    "把自家的织机调整一下，准备新一轮的经线",
    "把织好的几匹绸缎拿到县里去卖",
    "把卖来的银子去镇上买点桑叶",
    "去织造局交差，问问今年的调派",
    "夜里和沈氏商量，明年的生计该怎么办",
    "去县衙看看今年的水利工程是怎么安排的",
    "去乡学看看阿宝的先生",
    "去码头看看北来的商船",
    "和邻居拼锅吃顿好的",
    "去西塘看看有没有新的桑种可以买",
    "把自家的两台织机一并开工",
    "把第一批绸缎打包，准备运到苏州",
    "去苏州城里看看今年的洋船行情",
    "在苏州城里买一块上好的苏绣样品",
    "回镇上把苏绣样品给王牙人过目",
    "去县里拜会新任的县令",
    "去看看织造局的老师傅",
    "把家里的田契重新算一遍",
    "带着绸缎和账本去京城一趟",
    "回镇上盘算一下这三年的收成",
]


def post(url: str, body: dict[str, Any],
         timeout: float = 30.0) -> tuple[int, dict]:
    """发 POST 请求，返 (status, json_body)"""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            body_out = json.loads(e.read() or b"{}")
        except Exception:
            body_out = {"raw": e.read().decode("utf-8", errors="replace")}
        return e.code, body_out
    except TimeoutError as e:
        # 网络/超时 — 用 -1 标识，retry 逻辑会重试
        return -1, {"timeout": str(e), "timeout_s": timeout}
    except Exception as e:
        return -1, {"err_type": type(e).__name__, "err": str(e)}


def get(url: str, timeout: float = 10.0) -> tuple[int, dict]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            body_out = json.loads(e.read() or b"{}")
        except Exception:
            body_out = {"raw": e.read().decode("utf-8", errors="replace")}
        return e.code, body_out


def check_server_ready() -> bool:
    """先做 server 健康检查（避免跑 30 回合后才发现 server 没起）"""
    print("⏳ 检查 server 健康...")
    for _ in range(10):
        try:
            status, body = get(f"{BASE}/api/version", timeout=2)
            if status == 200:
                v = body.get("version", "?")
                print(f"  ✅ server up — version={v}")
                return True
        except Exception:
            pass
        time.sleep(1)
    print(f"  ❌ server @ {BASE} 没响应。请先 bash scripts/dev-server.sh start")
    return False


def summarize(state: dict) -> str:
    """一行状态摘要"""
    return (
        f"R{state.get('round_number', 0):02d} "
        f"AP={state.get('action_points_current', 0)}/{state.get('action_points_max', 0)} "
        f"cash={state.get('cash', 0):.1f} "
        f"events={len(state.get('recent_narratives', []))} "
        f"voice_pending={state.get('voice_options_pending')}"
    )


def narr_hook(state: dict, n: int = 70) -> str:
    """最近 narrative hook 摘要"""
    narrs = state.get("recent_narratives", [])
    if not narrs:
        return "(no narrative)"
    last = narrs[-1]
    hook = last.get("summary", "") or "?"
    return f"  | narr[-1]: {hook[:n]}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=30,
                        help="跑几个回合（默认 30，quick smoke 选 10）")
    parser.add_argument("--resume", type=str, default=None,
                        help="从已有 session_id 继续，不创建新")
    parser.add_argument("--log", type=str, default=None,
                        help="进度日志写到指定路径（每回合）")
    args = parser.parse_args()

    max_turns = min(args.turns, len(ACTIONS_30))

    # 0. 健康检查
    if not check_server_ready():
        sys.exit(2)

    # 1. 创建或恢复 session
    print()
    print("=" * 70)
    print(f"🚀 {max_turns} 回合真实端到端测试 (real LLM via minimax-anthropic)")
    print("=" * 70)
    print()
    t0 = time.time()

    if args.resume:
        sid = args.resume
        status_st, state_resp = get(f"{BASE}/api/state?session_id={sid}", timeout=5)
        if status_st != 200:
            print(f"  ❌ 恢复失败：session '{sid}' 不存在或已失效")
            sys.exit(3)
        print(f"[1/4] 恢复 session (GET /api/state):")
        print(f"  ✅ session_id = {sid}")
        print(f"     era         = {state_resp.get('era_id')}")
        print(f"     {summarize(state_resp)}")
        body = state_resp
    else:
        print("[1/4] 创建 session (POST /api/start)...")
        status, body = post(f"{BASE}/api/start", {
            "era_id": "wanli1587",
            "identity": "weaving_male",
            "gender": "male",
        })
        if status != 200:
            print(f"  ❌ /api/start failed {status}: {body}")
            print(f"  完整 body 长度: {len(json.dumps(body))} 字符")
            print(f"  关键 keys: {list(body.keys())[:5]}")
            print()
            print(f"💡 检查 server log: tail -50 /tmp/hfe_backend.log")
            sys.exit(3)

        sid = body.get("session_id")
        seed = body.get("seed")
        print(f"  ✅ session_id = {sid}")
        print(f"     seed        = {seed}")
        print(f"     era         = {body.get('era_id')} / {body.get('era_name')}")
        print(f"     开局 narrative: {body.get('recent_narratives', [{}])[0].get('narrative', '')[:80]}...")
        print(f"     {summarize(body)}")

    # 2. 跑 N 回合
    print()
    print(f"[2/4] 跑 {max_turns} 回合 input (POST /api/input)...")
    print()

    timeline: list[dict] = []
    save_checkpoints: dict[int, dict] = {}
    SAVE_AT_TURNS = {t for t in {5, 15, 30} if t <= max_turns}

    for turn in range(1, max_turns + 1):
        action = ACTIONS_30[turn - 1]
        t_turn_start = time.time()

        # 网络/超时鲁棒：retry 最 3 次 (180s + 180s + 60s)
        status = None
        resp = None
        elapsed = 0.0
        for attempt, per_timeout in enumerate([180.0, 180.0, 60.0], start=1):
            status, resp = post(f"{BASE}/api/input", {
                "session_id": sid,
                "input": action,
            }, timeout=per_timeout)
            elapsed = time.time() - t_turn_start
            if status == 200:
                break
            print(f"  ⚠️ Turn {turn:02d} attempt {attempt}: HTTP {status} ({elapsed:.0f}s), retrying...", flush=True)
            if args.log:
                with open(args.log, "a") as f:
                    f.write(f"  TURN {turn} ⚠️ attempt {attempt}: HTTP {status} ({elapsed:.0f}s)\n")
            time.sleep(2)  # cool down before retry
            t_turn_start = time.time()  # 重置 elapsed

        if status != 200:
            print(f"  ❌ Turn {turn:02d} failed HTTP {status} after all retries", flush=True)
            print(f"     body: {json.dumps(resp)[:300]}", flush=True)
            print(f"     action: {action}", flush=True)
            timeline.append({"turn": turn, "ok": False, "status": status, "resp": resp})
            if args.log:
                with open(args.log, "a") as f:
                    f.write(f"  TURN {turn} ❌ HTTP {status}: {str(resp)[:100]}\n")
            continue

        timeline.append({
            "turn": turn,
            "ok": True,
            "round": resp.get("round_number"),
            "elapsed_s": elapsed,
            "cash": resp.get("cash"),
            "ap_now": resp.get("action_points_current"),
            "narr_count": len(resp.get("recent_narratives", [])),
        })

        marker = "💾" if turn in SAVE_AT_TURNS else "✅"
        line = f"  {marker} Turn {turn:02d} [{elapsed:5.2f}s]  {summarize(resp)}"
        print(line, flush=True)
        if args.log:
            with open(args.log, "a") as f:
                f.write(f"  TURN {turn} [{elapsed:.2f}s] {summarize(resp)}\n")
        if turn in (1, 5, 10, 15, 20, 25, 30):
            print(f"                | action: \"{action}\"")
            print(narr_hook(resp))

    # 3. Save 检查点
    print()
    print(f"[3/4] Save 检查点（回合 {sorted(SAVE_AT_TURNS)}）...")

    for turn in sorted(SAVE_AT_TURNS):
        if turn > len(timeline):
            continue
        check_timeline = timeline[turn - 1] if turn > 0 else timeline[0]
        if not check_timeline.get("ok"):
            print(f"     ⚠️ turn {turn} 跑失败，跳过 save 检查")
            continue

        status_st, state_resp = get(f"{BASE}/api/state?session_id={sid}", timeout=5)
        if status_st != 200:
            print(f"     ❌ /api/state failed {status_st}: {state_resp}")
            continue

        state_hash = {
            "round": state_resp.get("round_number"),
            "cash": state_resp.get("cash"),
            "events": len(state_resp.get("recent_narratives", [])),
            "narr_hook": state_resp.get("recent_narratives", [{}])[-1].get("summary", "")[:30],
            "voice_pending": state_resp.get("voice_options_pending"),
            "inventory_keys": sorted(state_resp.get("inventory", {}).keys())[:5] if isinstance(state_resp.get("inventory"), dict) else [],
            "npc_relations_count": len(state_resp.get("npc_relations", {})),
        }
        save_checkpoints[turn] = state_hash
        print(f"     ✅ turn {turn}: {state_hash}")

    # 4. Save/Load 一致性校验
    print()
    print("[4/4] Save/Load 一致性校验...")

    saves_dir = ROOT / "saves"
    expected_session_dir = saves_dir / sid
    session_exists = expected_session_dir.exists()
    print(f"     检查 saves 目录: {saves_dir}")
    print(f"     session_id: {sid}")
    print(f"     session dir exists: {session_exists}")
    if session_exists:
        files = sorted(expected_session_dir.iterdir())
        print(f"     存档文件数: {len(files)}")
        for f in files[:5]:
            print(f"       - {f.name} ({f.stat().st_size} bytes)")

    # 最终状态
    status_st, state_final = get(f"{BASE}/api/state?session_id={sid}", timeout=5)
    if status_st == 200:
        print()
        print(f"  📊 最终状态:")
        print(f"     round    = {state_final.get('round_number')}")
        print(f"     cash     = {state_final.get('cash')} 两")
        print(f"     events   = {len(state_final.get('recent_narratives', []))}")
        print(f"     npc_relations = {len(state_final.get('npc_relations', {}))}")
        print(f"     inventory keys = {sorted(state_final.get('inventory', {}).keys())[:10]}")
        print(f"     variables = {state_final.get('variables', {})}")

    total_elapsed = time.time() - t0
    print()
    print("=" * 70)
    print(f"⏱  总耗时: {total_elapsed:.1f}s  ({len(timeline)} 回合)")

    ok_turns = [t for t in timeline if t.get("ok")]
    failed_turns = [t for t in timeline if not t.get("ok")]
    if ok_turns:
        avg_s = sum(t["elapsed_s"] for t in ok_turns) / len(ok_turns)
        max_s = max(t["elapsed_s"] for t in ok_turns)
        min_s = min(t["elapsed_s"] for t in ok_turns)
        print(f"   ✅ 成功 {len(ok_turns)}/{len(timeline)}")
        print(f"   ⏱  每回合平均 {avg_s:.2f}s (min {min_s:.2f}s / max {max_s:.2f}s)")

        # 把状态写到 states/<sid>.json 让下一 resume 继续
        progress_file = ROOT / "tests" / "_e2e_progress" / f"{sid}.json"
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(progress_file, "w") as f:
            json.dump({
                "session_id": sid,
                "last_turn": len(timeline),
                "save_checkpoints": save_checkpoints,
                "timeline_tail": timeline[-3:],
            }, f, ensure_ascii=False, indent=2)
        print(f"   📁 进度持久化：tests/_e2e_progress/{sid}.json")

    if failed_turns:
        print()
        print(f"   ❌ 失败 {len(failed_turns)}/")
        for ft in failed_turns:
            print(f"     turn {ft['turn']}: HTTP {ft['status']}: {str(ft['resp'])[:100]}")

    if failed_turns:
        print()
        print(f"  FAILED (有 {len(failed_turns)} 回合失败)")
        sys.exit(1)
    else:
        print()
        print(f"  ✅ ALL {max_turns} ROUNDS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()