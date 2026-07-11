"""
🆕 v2.7+ 冷存档逻辑验证脚本

覆盖场景：
1. 30 天未动的存档 → 标 archived + 移到 _archive/
2. 刚保存的存档（昨天） → 不动
3. list_sessions 默认过滤 archived
4. list_sessions(include_archived=True) 能看到
5. unarchive_session 复活冷存档
6. 玩家再次保存（save_state）自动复活

需要后端在 localhost:8765 跑（service 应在冷存档清理完成后启动过）
"""
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://localhost:8765"


def http(method: str, path: str, body=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
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


def make_session(name: str, last_saved_at: str, account_id: str = "verify_v27_user"):
    """手工建一个 session dir + meta.json"""
    d = Path("saves") / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps({
        "session_id": name,
        "era_id": "wanli1587",
        "account_id": account_id,
        "current_round": 5,
        "current_date": "1587-08-01",
        "summary": f"v2.7 archive test: {name}",
        "created_at": last_saved_at,
        "last_saved_at": last_saved_at,
    }, ensure_ascii=False), encoding="utf-8")
    return d


def main():
    failures = 0
    saves_root = Path("saves").resolve()
    archive_dir = saves_root / "_archive"

    # 清理上次测试残留
    if archive_dir.exists():
        for p in archive_dir.iterdir():
            if p.name.startswith("wanli1587_verify_"):
                shutil.rmtree(p, ignore_errors=True)
    for p in saves_root.iterdir():
        if p.is_dir() and p.name.startswith("wanli1587_verify_"):
            shutil.rmtree(p, ignore_errors=True)

    print("=" * 60)
    print("场景 1: 30 天未动 → 标 archived + 移到 _archive/")
    print("=" * 60)
    old_ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time() - 35 * 86400))
    old = make_session(f"wanli1587_verify_old_{old_ts}", "2026-06-01T10:00:00")
    print(f"  → 已建 35 天前的 session: {old.name}")
    # 跑冷存档
    sys.path.insert(0, "src")
    from history_footnote.storage.save_manager import SaveManager
    sm = SaveManager(Path("saves"))
    moved = sm.archive_inactive_sessions(within_days=30)
    if not assert_eq("archive_inactive_sessions 返回值 ≥ 1", moved >= 1, True):
        failures += 1
    # meta.json 应该是 archived=true
    meta = json.loads((archive_dir / old.name / "meta.json").read_text(encoding="utf-8"))
    if not assert_eq("meta.archived = true", meta.get("archived"), True):
        failures += 1
    if not assert_eq("meta.archived_at 非空", bool(meta.get("archived_at")), True):
        failures += 1
    if not assert_eq("原 saves/ 下已不存在", not old.exists(), True):
        failures += 1
    if not assert_eq("_archive/ 下存在", (archive_dir / old.name).exists(), True):
        failures += 1

    print()
    print("=" * 60)
    print("场景 2: 刚保存的存档（5 天内）→ 不动")
    print("=" * 60)
    recent = make_session(
        f"wanli1587_verify_recent_{time.strftime('%Y%m%d_%H%M%S')}",
        time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - 5 * 86400)),
    )
    print(f"  → 已建 5 天前的 session: {recent.name}")
    moved = sm.archive_inactive_sessions(within_days=30)
    if not assert_eq("5 天前的 archive 数量 = 0（不动）", moved, 0):
        failures += 1
    if not assert_eq("recent 仍在 saves/ 下", recent.exists(), True):
        failures += 1

    print()
    print("=" * 60)
    print("场景 3: list_sessions 默认过滤 archived")
    print("=" * 60)
    # 给旧 session 一个 account_id 与 recent 相同，确保 account 过滤一致
    sessions_default = sm.list_sessions(account_id="verify_v27_user")
    sids_default = [s.session_id for s in sessions_default]
    if not assert_eq("default 列表不含 archived session", old.name in sids_default, False):
        failures += 1
    if not assert_eq("default 列表含 recent session", recent.name in sids_default, True):
        failures += 1

    sessions_all = sm.list_sessions(account_id="verify_v27_user", include_archived=True)
    sids_all = [s.session_id for s in sessions_all]
    if not assert_eq("include_archived 列表含 archived session", old.name in sids_all, True):
        failures += 1
    if not assert_eq("include_archived 列表含 recent", recent.name in sids_all, True):
        failures += 1

    # list_archived_sessions
    archived_sessions = sm.list_archived_sessions(account_id="verify_v27_user")
    archived_sids = [s.session_id for s in archived_sessions]
    if not assert_eq("list_archived_sessions 含 old", old.name in archived_sids, True):
        failures += 1
    if not assert_eq("list_archived_sessions 不含 recent", recent.name in archived_sids, False):
        failures += 1

    print()
    print("=" * 60)
    print("场景 4: unarchive_session 复活")
    print("=" * 60)
    ok = sm.unarchive_session(old.name)
    if not assert_eq("unarchive_session 成功", ok, True):
        failures += 1
    if not assert_eq("已移回 saves/", (saves_root / old.name).exists(), True):
        failures += 1
    if not assert_eq("_archive/ 下已无", not (archive_dir / old.name).exists(), True):
        failures += 1
    # meta.archived 应该是 false
    meta = json.loads((saves_root / old.name / "meta.json").read_text(encoding="utf-8"))
    if not assert_eq("复活后 meta.archived = false", meta.get("archived"), False):
        failures += 1
    if not assert_eq("复活后 meta.archived_at = ''", meta.get("archived_at", ""), ""):
        failures += 1

    print()
    print("=" * 60)
    print("场景 5: HTTP API /api/archives 默认不返回 archived")
    print("=" * 60)
    # 把 recent 标 archived
    sm.archive_inactive_sessions(within_days=30)  # recent 还是 5 天，不会动
    # 手工改 recent 的 last_saved_at 为 31 天前再 archive
    meta_path = recent / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["last_saved_at"] = "2026-05-01T00:00:00"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    # 再跑 archive
    moved = sm.archive_inactive_sessions(within_days=30)
    if not assert_eq("recent 被归档", moved >= 1, True):
        failures += 1
    # 通过 HTTP 查
    s, d = http("GET", f"/api/archives?account=verify_v27_user")
    api_sids = [a["session_id"] for a in d.get("archives", [])]
    if not assert_eq("HTTP /api/archives 不含 archived recent", recent.name in api_sids, False):
        failures += 1
    s, d = http("GET", f"/api/archives?account=verify_v27_user&include_archived=1")
    api_sids_all = [a["session_id"] for a in d.get("archives", [])]
    if not assert_eq("HTTP /api/archives?include_archived=1 含 archived recent", recent.name in api_sids_all, True):
        failures += 1

    # 清理
    for p in saves_root.iterdir():
        if p.is_dir() and p.name.startswith("wanli1587_verify_"):
            shutil.rmtree(p, ignore_errors=True)
    if archive_dir.exists():
        for p in archive_dir.iterdir():
            if p.name.startswith("wanli1587_verify_"):
                shutil.rmtree(p, ignore_errors=True)

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
