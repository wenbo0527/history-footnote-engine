"""
🆕 v2.7+ 游客 Cookie 持久化验证脚本
"""
import json
import sys
import time
import urllib.request as urlreq
import urllib.error
import http.cookiejar
from pathlib import Path

BASE = "http://localhost:8765"


def make_opener():
    cj = http.cookiejar.CookieJar()
    return urlreq.build_opener(urlreq.HTTPCookieProcessor(cj), urlreq.HTTPRedirectHandler())


def call(opener, method, path, body=None, headers=None, cookie_value=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    h = {"Content-Type": "application/json", **(headers or {})}
    if cookie_value:
        h["Cookie"] = f"hfe_guest={cookie_value}"
    req = urlreq.Request(
        f"{BASE}{path}", data=data, method=method,
        headers=h,
    )
    try:
        resp = opener.open(req, timeout=10)
        return resp.status, json.loads(resp.read().decode("utf-8")), dict(resp.headers)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8")), dict(e.headers)
        except Exception:
            return e.code, {"_raw": str(e)}, dict(e.headers)


def assert_eq(name, got, want):
    if got != want:
        print(f"  ❌ {name}: got={got!r} want={want!r}")
        return False
    print(f"  ✅ {name}")
    return True


def find_cookie_in_headers(headers, name="hfe_guest"):
    sc = headers.get("Set-Cookie", "")
    if not sc:
        return None
    for part in sc.split(","):
        if "=" in part and name in part:
            kv = part.strip().split(";", 1)[0]
            return kv.split("=", 1)[1]
    return None


def _get_cj(opener):
    for h in opener.handlers:
        if isinstance(h, urlreq.HTTPCookieProcessor):
            return h.cookiejar
    raise RuntimeError("opener 缺 HTTPCookieProcessor")


def add_cookie(opener, name, value, domain="localhost"):
    cj = _get_cj(opener)
    cj.set_cookie(http.cookiejar.Cookie(
        version=0, name=name, value=value,
        port=None, port_specified=False,
        domain=domain, domain_specified=False, domain_initial_dot=False,
        path="/", path_specified=True,
        secure=False, expires=None,
        discard=True, comment=None, comment_url=None,
        rest={}, rfc2109=False
    ))


def main():
    failures = 0
    opener = make_opener()

    print("=" * 60)
    print("场景 1: 无 cookie 调 /api/menu → Set-Cookie 下发 guest_id")
    print("=" * 60)
    s, d, h = call(opener, "GET", "/api/menu")
    aid1 = d.get("user", {}).get("account_id", "")
    if not assert_eq("HTTP 200", s, 200): failures += 1
    if not assert_eq("返回 user.account_id", aid1.startswith("guest_"), True): failures += 1
    cookie = find_cookie_in_headers(h)
    if not assert_eq("Set-Cookie 下发", bool(cookie), True): failures += 1
    if not assert_eq("cookie 长度 > 0（签名后 base64）", bool(cookie and len(cookie) > 20), True): failures += 1
    s, d, _ = call(opener, "GET", "/api/menu")
    aid2 = d.get("user", {}).get("account_id", "")
    if not assert_eq("复用同一 guest_id（幂等）", aid2, aid1): failures += 1

    print()
    print("=" * 60)
    print("场景 2: cookie 关联后能拉取自己的存档")
    print("=" * 60)
    saves_root = Path("saves").resolve()
    ts = time.strftime("%Y%m%d_%H%M%S")
    fake = saves_root / f"wanli1587_{ts}"
    fake.mkdir(parents=True, exist_ok=True)
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S")
    (fake / "meta.json").write_text(json.dumps({
        "session_id": fake.name,
        "era_id": "wanli1587",
        "account_id": aid1,
        "current_round": 5,
        "current_date": "1587-08-01",
        "summary": "v2.7 cookie test",
        "created_at": now_iso,
        "last_saved_at": now_iso,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"  → 已建存档: {fake.name} (account_id={aid1})")
    s, d, _ = call(opener, "GET", "/api/archives")
    sids = [a["session_id"] for a in d.get("archives", [])]
    if not assert_eq("HTTP 200", s, 200): failures += 1
    if not assert_eq("能看到自己的存档", fake.name in sids, True): failures += 1

    print()
    print("=" * 60)
    print("场景 3: 模拟'清 localStorage，但 cookie 还在'")
    print("=" * 60)
    new_opener = make_opener()
    s, d, _ = call(new_opener, "GET", "/api/menu", cookie_value=cookie)
    aid3 = d.get("user", {}).get("account_id", "")
    if not assert_eq("新 opener 带原 cookie 仍能拿同一 ID", aid3, aid1): failures += 1
    s, d, _ = call(new_opener, "GET", "/api/archives", cookie_value=cookie)
    sids = [a["session_id"] for a in d.get("archives", [])]
    if not assert_eq("新 opener 也能看到自己的存档", fake.name in sids, True): failures += 1

    print()
    print("=" * 60)
    print("场景 4: 篡改 cookie → 服务端识别失败")
    print("=" * 60)
    tamper_opener = make_opener()
    s, d, h = call(tamper_opener, "GET", "/api/menu", cookie_value="guest_fake.tampersig")
    aid4 = d.get("user", {}).get("account_id", "")
    if not assert_eq("篡改 cookie 后仍 200（不抛错）", s, 200): failures += 1
    if not assert_eq("服务端识别失败，新建 guest", aid4.startswith("guest_") and aid4 != "guest_fake", True): failures += 1
    new_cookie = find_cookie_in_headers(h)
    if not assert_eq("新 Set-Cookie 已签发", bool(new_cookie), True): failures += 1

    print()
    print("=" * 60)
    print("场景 5: 没用 cookie 但用 query 兜底（向后兼容）")
    print("=" * 60)
    compat_opener = make_opener()
    s, d, _ = call(compat_opener, "GET", f"/api/archives?account={aid1}")
    sids = [a["session_id"] for a in d.get("archives", [])]
    if not assert_eq("query 兜底也能看到存档", fake.name in sids, True): failures += 1

    print()
    print("=" * 60)
    print("场景 6: register 用 cookie 自动迁移游客存档")
    print("=" * 60)
    s, d, h = call(opener, "GET", "/api/account/invite_codes")
    invite_code = ""
    for c in d.get("codes", []):
        if c.get("is_valid"):
            invite_code = c["code"]
            break
    if not invite_code:
        print("  ❌ 找不到有效邀请码"); return 1
    print(f"  → 邀请码: {invite_code}")
    s, d, h = call(opener, "POST", "/api/account/register", {
        "username": f"v27user_{int(time.time()) % 100000}",
        "invite_code": invite_code,
        "password": "test1234",
    })
    if not assert_eq("register HTTP 200", s, 200): failures += 1
    new_aid = d.get("account_id", "")
    migrated = d.get("migrated_archives", 0)
    if not assert_eq("新 account_id 不空", bool(new_aid), True): failures += 1
    if not assert_eq(f"从 cookie 关联的 guest 迁移 {migrated} 个存档", migrated >= 1, True): failures += 1
    meta = json.loads((fake / "meta.json").read_text(encoding="utf-8"))
    if not assert_eq("meta.account_id 已迁到新账户", meta.get("account_id"), new_aid): failures += 1

    import shutil
    shutil.rmtree(fake, ignore_errors=True)

    print()
    print("=" * 60)
    print("结果汇总")
    print("=" * 60)
    if failures == 0:
        print("🎉 全部通过")
        return 0
    print(f"💥 {failures} 项失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
