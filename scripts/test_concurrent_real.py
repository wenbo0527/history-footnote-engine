"""并发压力测试：5 个玩家同时进行游戏"""
import sys
import threading
import time
import requests  # 需要 pip install requests
sys.path.insert(0, "src")

from history_footnote.concurrency import (
    SESSION_POOL,
    LLM_THROTTLE,
    SAVE_QUEUE,
    SessionPool,
    LLMThrottle,
)

BASE_URL = "http://localhost:8765"

CHARACTERS = [
    {"name": "沈岐年", "hometown": "福建漳州", "background": "因倭寇扰了漳州府城，丝路断了三分，合伙人陈七卷款跑了", "family": {}, "opening_paragraph": "夜里下了场小雨，沈岐年翻了个身，竹榻嘎吱一声。"},
    {"name": "陈秀娘", "hometown": "苏州阊门", "background": "父亲是个穷秀才，去世后她立誓要把弟弟供出来", "family": {}, "opening_paragraph": "秀娘在油灯下算账，手指冻得通红。"},
    {"name": "李七斤", "hometown": "徽州歙县", "background": "徽商李家三房的小儿子，爹让他来盛泽学做丝绸生意", "family": {}, "opening_paragraph": "李七斤站在牙行门口，看着镇上来来往往的人。"},
    {"name": "王织巧", "hometown": "盛泽镇", "background": "镇西王家织坊的长女，十六岁，没说过婆家", "family": {}, "opening_paragraph": "王织巧在天还没亮时就起了，摸黑坐到织机前。"},
    {"name": "张半仙", "hometown": "茅山脚下", "background": "自称能算命，但骗不到几个钱", "family": {}, "opening_paragraph": "张半仙在巷口支起摊子，幌子上写着'铁口直断'。"},
]

INPUTS = [
    "我摸摸口袋里的散碎银子，叹了口气",
    "我问问邻居张三最近镇上有啥事",
    "我去牙行看看今年的丝价",
    "我今天不织布，去看花",
    "我给你算一卦",
]


def play_one_session(player_id: int) -> dict:
    """一个玩家完整流程"""
    import traceback
    print(f"[玩家 {player_id}] 启动")
    character = CHARACTERS[player_id]
    result = {"player_id": player_id, "success": False, "steps": []}

    try:
        # 1. Start
        start_resp = requests.post(
            f"{BASE_URL}/api/start",
            json={
                "era_id": "wanli1587",
                "identity": "weaving_male" if player_id % 2 == 0 else "weaving_female",
                "gender": "male" if player_id % 2 == 0 else "female",
                "character": character,
            },
            timeout=30,
        )
        result["steps"].append(f"start http_status={start_resp.status_code}")
        start_resp.raise_for_status()
        start_data = start_resp.json()
        sid = start_data.get("session_id")
        if not sid:
            result["steps"].append(f"start NO session_id, response: {start_resp.text[:200]}")
            return result
        result["steps"].append(f"start: session_id={sid[:8]}")
        result["session_id"] = sid

        # 2. Input
        for inp in INPUTS[player_id:player_id+1]:
            inp_resp = requests.post(
                f"{BASE_URL}/api/input",
                json={"session_id": sid, "input": inp},
                timeout=90,
            )
            result["steps"].append(f"input http_status={inp_resp.status_code}")
            inp_resp.raise_for_status()
            inp_data = inp_resp.json()
            narr = inp_data.get("last_narrative", "")
            if narr is None:
                narr = ""
            elif isinstance(narr, dict):
                # last_narrative 是 dict（narrative_history entry）→ 取 narrative 字段
                narr = narr.get("narrative", "")[:80]
            else:
                narr = str(narr)[:80]
            result["steps"].append(f"input '{inp[:10]}': {narr}...")

        result["success"] = True
        return result
    except Exception as e:
        import sys
        result["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        result["traceback"] = traceback.format_exc()[:300]
        sys.stdout.write(f"[玩家 {player_id}] 异常: {result['error']}\n")
        sys.stdout.flush()
        return result


def play_one_session_v2(player_id: int, results: list) -> dict:
    """简化版：直接发起请求，写回 results[player_id]"""
    import sys
    sys.stdout.write(f"[玩家 {player_id}] 启动\n")
    sys.stdout.flush()
    character = CHARACTERS[player_id]
    result = {"player_id": player_id, "success": False, "steps": []}
    try:
        start_resp = requests.post(
            f"{BASE_URL}/api/start",
            json={
                "era_id": "wanli1587",
                "identity": "weaving_male" if player_id % 2 == 0 else "weaving_female",
                "gender": "male" if player_id % 2 == 0 else "female",
                "character": character,
            },
            timeout=120,
        )
        sys.stdout.write(f"[玩家 {player_id}] start http={start_resp.status_code}\n")
        sys.stdout.flush()
        start_resp.raise_for_status()
        start_data = start_resp.json()
        sid = start_data.get("session_id")
        if not sid:
            sys.stdout.write(f"[玩家 {player_id}] no session_id: {start_resp.text[:200]}\n")
            sys.stdout.flush()
            results[player_id] = result
            return result
        sys.stdout.write(f"[玩家 {player_id}] sid={sid[:8]}\n")
        sys.stdout.flush()

        inp = INPUTS[player_id]
        inp_resp = requests.post(
            f"{BASE_URL}/api/input",
            json={"session_id": sid, "input": inp},
            timeout=180,
        )
        sys.stdout.write(f"[玩家 {player_id}] input http={inp_resp.status_code}\n")
        sys.stdout.flush()
        if inp_resp.status_code != 200:
            sys.stdout.write(f"[玩家 {player_id}] input body: {inp_resp.text[:300]}\n")
            sys.stdout.flush()
            results[player_id] = result
            return result
        inp_data = inp_resp.json()
        sys.stdout.write(f"[玩家 {player_id}] input narr_len={len(str(inp_data.get('last_narrative','')))}\n")
        sys.stdout.flush()
        result["success"] = True
        results[player_id] = result
        return result
    except Exception as e:
        import traceback
        sys.stdout.write(f"[玩家 {player_id}] 异常: {type(e).__name__}: {str(e)[:300]}\n")
        sys.stdout.write(f"[玩家 {player_id}] traceback: {traceback.format_exc()[:300]}\n")
        sys.stdout.flush()
        result["error"] = str(e)
        results[player_id] = result
        return result


def main():
    print("=" * 60)
    print("并发压力测试：5 个玩家同时进行游戏")
    print("=" * 60)

    # 1. 单元测试 SessionPool 性能
    print("\n[测试 1] SessionPool 压力测试")
    pool = SessionPool(max_sessions=20)

    start = time.time()
    results = [None] * 5
    print(f"  创建 5 个线程...")
    threads = [threading.Thread(target=play_one_session_v2, args=(i, results)) for i in range(5)]
    for t in threads:
        t.start()
    print(f"  启动完成，等待 join...")
    for t in threads:
        t.join()
    print(f"  join 完成")
    elapsed = time.time() - start

    success_count = sum(1 for r in results if r and r["success"])
    print(f"  ✅ {success_count}/5 个玩家完成（耗时 {elapsed:.1f}s）")
    for r in results:
        if r:
            print(f"    玩家 {r['player_id']}: {'✓' if r['success'] else '✗'} ({len(r.get('steps', []))} 步)")
            if not r["success"]:
                print(f"      错误: {r.get('error', '?')}")
                if r.get("traceback"):
                    print(f"      traceback: {r['traceback'][:200]}")
            for s in r.get("steps", []):
                print(f"      - {s[:100]}")

    # 2. 限流统计
    print("\n[测试 2] LLMThrottle 统计")
    stats = LLM_THROTTLE.stats()
    print(f"  活跃: {stats['active']}/{stats['max_concurrent']}")
    print(f"  累计: {stats['total_calls']}")

    # 3. SessionPool 状态
    print("\n[测试 3] SessionPool 状态")
    print(f"  当前 session 数: {SESSION_POOL.size()}")
    print(f"  全部 session ID:")
    for sid in SESSION_POOL.list_all()[:5]:
        print(f"    - {sid[:8]}")


if __name__ == "__main__":
    main()