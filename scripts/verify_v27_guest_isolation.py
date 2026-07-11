"""
🆕 v2.7+ 游客存档隔离验证脚本

覆盖场景：
1. 游客 A 多次调用 /api/menu → 拿到同一 guest_id（幂等）
2. 游客 A 创建存档 → 游客 B 在另一 account_id 下看不到
3. 游客 A 注册 → 旧存档迁移到新 account_id
4. 登录用户不受影响（不返回 'default' 桶污染）

需要后端在 localhost:8765 跑
"""
import json
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

BASE = "http://localhost:8765"


def http(method: str, path: str, body=None, headers=None):
    url = f"{BASE}{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Content-Type": "application/json",
        **(headers or {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"_raw": str(e)}


def assert_eq(name, got, want):
    if got != want:
        print(f"  ❌ {name}: got={got!r} want={want!r}")
        return False
    print(f"  ✅ {name}")
    return True


def main():
    failures = 0

    print("=" * 60)
    print("场景 1: /api/menu 幂等创建 guest（同 account_id 复用）")
    print("=" * 60)
    # 前端会拿响应里的 account_id 存到 localStorage，下次带上 query
    s1, d1 = http("GET", "/api/menu")
    aid1 = d1.get("user", {}).get("account_id", "")
    role1 = d1.get("user", {}).get("role", "")
    if not assert_eq("GET /api/menu #1 HTTP 200", s1, 200): failures += 1
    if not assert_eq("role = guest", role1, "guest"): failures += 1
    if not assert_eq("account_id 以 guest_ 开头", aid1.startswith("guest_"), True): failures += 1
    # 复用同一 ID → 应得到同一 account
    s2, d2 = http("GET", f"/api/menu?account_id={aid1}")
    aid2 = d2.get("user", {}).get("account_id", "")
    if not assert_eq("复用同一 ID（幂等）", aid2, aid1): failures += 1
    print(f"  → guest_id = {aid1}")

    print()
    print("=" * 60)
    print("场景 2: 不同游客拿到不同 guest_id")
    print("=" * 60)
    s3, d3 = http("GET", "/api/menu?account_id=guest_another_browser_xx")
    aid3 = d3.get("user", {}).get("account_id", "")
    if not assert_eq("GET /api/menu 伪造 account_id HTTP 200", s3, 200): failures += 1
    if not assert_eq("伪造 ID 被复用为 account_id", aid3, "guest_another_browser_xx"): failures += 1
    if not assert_eq("游客 A != 游客 B", aid1 != aid3, True): failures += 1

    print()
    print("=" * 60)
    print("场景 3: 真实 register 流程 + 游客存档迁移")
    print("=" * 60)
    # 3.1 用游客 A 创建一个伪存档（直接落盘）
    # session_id 必须匹配 SESSION_ID_PATTERN = ^([a-z0-9_]+)_(\d{8}_\d{6})$
    # 注意：必须写到 server 进程 cwd 下（Path('saves') 相对 server 的 cwd）
    saves_root = Path("saves").resolve()
    saves_root.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    # pattern 末尾必须是 \d{8}_\d{6}，所以不要再加后缀
    fake_session = saves_root / f"wanli1587_{ts}"
    fake_session.mkdir(parents=True, exist_ok=True)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    (fake_session / "meta.json").write_text(json.dumps({
        "session_id": fake_session.name,
        "era_id": "wanli1587",
        "account_id": aid1,           # 属于游客 A
        "current_round": 3,
        "current_date": "1587-08-01",
        "summary": "v2.7 游客隔离测试",
        "created_at": now_iso,
        "last_saved_at": now_iso,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"  → 已落游客 A 假存档: {fake_session.name}")
    print(f"  → exists on disk: {fake_session.is_dir()}")
    # 强制同步到磁盘
    import os; os.sync()

    # 3.2 拉游客 A 列表，确认能看到
    s, d = http("GET", f"/api/archives?account={aid1}")
    seen_a = any(a.get("session_id") == fake_session.name for a in d.get("archives", []))
    if not assert_eq("游客 A 列表含自己的存档", seen_a, True): failures += 1

    # 3.3 拉游客 B 列表，确认看不到
    s, d = http("GET", f"/api/archives?account={aid3}")
    seen_b = any(a.get("session_id") == fake_session.name for a in d.get("archives", []))
    if not assert_eq("游客 B 列表不含 A 的存档", seen_b, False): failures += 1

    # 3.4 拉 'default' 列表（旧行为污染桶），确认也不会带出 A 的存档
    s, d = http("GET", "/api/archives?account=default")
    seen_default = any(a.get("session_id") == fake_session.name for a in d.get("archives", []))
    if not assert_eq("'default' 桶不污染（不含 A 的存档）", seen_default, False): failures += 1

    # 3.5 用游客 A 身份注册 → 应该自动迁移
    # 准备邀请码
    s, d = http("GET", "/api/account/invite_codes")
    invite_code = ""
    for c in d.get("codes", []):
        if c.get("is_valid"):
            invite_code = c["code"]
            break
    if not invite_code:
        print("  ❌ 找不到有效邀请码，请先生成一个")
        return 1
    print(f"  → 使用邀请码: {invite_code}")

    new_username = f"v27user_{int(time.time()) % 100000}"
    s, d = http("POST", "/api/account/register", {
        "username": new_username,
        "invite_code": invite_code,
        "password": "test1234",
        "migrate_from_guest_id": aid1,
    })
    new_aid = d.get("account_id", "")
    migrated = d.get("migrated_archives", 0)
    if not assert_eq("register HTTP 200", s, 200): failures += 1
    if not assert_eq("新账户有 account_id", bool(new_aid), True): failures += 1
    if not assert_eq(f"迁移了游客 A 存档 (migrated={migrated})", migrated >= 1, True): failures += 1

    # 3.6 验证 meta.json 真的被改了 owner
    meta = json.loads((fake_session / "meta.json").read_text(encoding="utf-8"))
    if not assert_eq(f"meta.json account_id 已迁移到新账户", meta.get("account_id"), new_aid): failures += 1

    # 3.7 拉新账户列表，应能看见
    s, d = http("GET", f"/api/archives?account={new_aid}")
    seen_new = any(a.get("session_id") == fake_session.name for a in d.get("archives", []))
    if not assert_eq("新账户列表含迁移后的存档", seen_new, True): failures += 1

    # 3.8 拉游客 A 旧 ID 列表，应该没了
    s, d = http("GET", f"/api/archives?account={aid1}")
    seen_old = any(a.get("session_id") == fake_session.name for a in d.get("archives", []))
    if not assert_eq("游客 A 旧 ID 列表已不含该存档", seen_old, False): failures += 1

    # 清理
    import shutil
    shutil.rmtree(fake_session, ignore_errors=True)

    print()
    print("=" * 60)
    print("结果汇总")
    print("=" * 60)
    if failures == 0:
        print("🎉 全部通过")
        return 0
    else:
        print(f"💥 {failures} 项失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
