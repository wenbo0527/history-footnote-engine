"""🆕 v1.7.47 Menu Router

登录后通用菜单端点：
- GET /api/menu → 返回 4 板块信息（开始游戏/存档/系统/admin）
- GET /api/saves/list → 返回用户存档列表

设计：
- 玩家 vs admin 角色差异
- 存档按 account_id 隔离
- 通用 menu 结构
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from pathlib import Path
from history_footnote.account_system import AccountSystem
from history_footnote.web_server.routers.admin import _check_admin_token, _require_admin

_ACCOUNTS_DIR = Path("saves")
_ACCOUNT_SYSTEM_SINGLETON: Optional[AccountSystem] = None


def _get_account_system_local() -> AccountSystem:
    """🆕 v1.7.47 每次新建 AccountSystem（不缓存，确保读到最新 accounts.json）

    Singleton 缓存会导致 admin 账户创建后被漏读
    """
    return AccountSystem(storage_root=_ACCOUNTS_DIR)


def handle_GET_menu(handler, query: str) -> bool:
    """GET /api/menu

    Returns:
        {
          "user": {"account_id", "username", "role"},
          "sections": [
            {"id": "new_game", "title": "开始新游戏", "icon": "/icons/nav/home.webp"},
            {"id": "saves", "title": "我的存档", "icon": "/icons/nav/archive.webp"},
            {"id": "settings", "title": "系统", "icon": "/icons/nav/settings.webp"},
            {"id": "admin", "title": "管理员面板", "icon": "/icons/stats/reputation.webp", "admin_only": true},
          ],
          "stats": {"saves_count", "saves_max"}
        }

    🆕 v2.7+ 持久化：cookie 优先（Signed HttpOnly），query 兜底
    """
    sys_inst = _get_account_system_local()

    # 🆕 v2.7+: 优先从 cookie 拿 account_id（持久化身份）；fallback 到 query / 创建
    account_id = handler._get_guest_id_from_cookie_or_query(query)

    account = sys_inst.get_account(account_id)
    # 找不到 account → 自动建 guest（不返 404）
    if not account:
        account = sys_inst.create_guest(account_id=account_id)
        account_id = account.account_id

    # 4 板块
    sections = [
        {"id": "new_game", "title": "开始新游戏", "icon": "/icons/nav/home.webp",
         "description": "选择时代和身份开始新游戏"},
        {"id": "saves", "title": "我的存档", "icon": "/icons/nav/archive.webp",
         "description": "继续之前的游戏"},
        {"id": "settings", "title": "系统", "icon": "/icons/nav/settings.webp",
         "description": "关于、反馈、退出登录"},
    ]
    is_admin = account.role == "admin"
    if is_admin:
        sections.append({
            "id": "admin", "title": "管理员面板", "icon": "/icons/stats/reputation.webp",
            "description": "用户管理 / 存档管理 / 系统配置",
            "admin_only": True,
        })
    # 统计
    saves_dir = Path("saves") / account_id
    saves_count = 0
    if saves_dir.exists():
        saves_count = len([d for d in saves_dir.iterdir() if d.is_dir()])
    # 返回
    result = {
        "user": {
            "account_id": account.account_id,
            "username": account.username,
            "role": account.role,
        },
        "sections": sections,
        "stats": {
            "saves_count": saves_count,
            "saves_max": 10,
        },
    }
    # _get_guest_id_from_cookie_or_query 已自动处理 Set-Cookie
    handler._json_with_cookies(200, result)
    return True


def handle_GET_saves_list(handler, query: str) -> bool:
    """GET /api/saves/list

    Returns:
        {
          "saves": [
            {"id": "save_001", "name": "万历十五年", "round": 5, "date": "1587-08", "created_at": "..."},
            ...
          ],
          "total": int
        }

    🆕 v2.7+: cookie 优先
    """
    sys_inst = _get_account_system_local()
    # 🆕 v2.7+: 优先 cookie
    account_id = handler._get_guest_id_from_cookie_or_query(query)
    account = sys_inst.get_account(account_id)
    if not account:
        account = sys_inst.create_guest(account_id=account_id)
        account_id = account.account_id
    saves_dir = Path("saves") / account_id
    saves = []
    if saves_dir.exists():
        for save_path in sorted(saves_dir.iterdir(), reverse=True):
            if not save_path.is_dir():
                continue
            save_json = save_path / "state.json"
            if not save_json.exists():
                continue
            try:
                with open(save_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = data.get("state", {})
                saves.append({
                    "id": save_path.name,
                    "name": f"{data.get('era_id', '万历十五年')}",
                    "round": state.get("round_number", 0),
                    "city": state.get("current_city", ""),
                    "date": state.get("current_date", ""),
                    "cash": round(state.get("cash", 0), 2),
                    "saved_at": data.get("saved_at", ""),
                })
            except (json.JSONDecodeError, OSError):
                continue
    handler._json_with_cookies(200, {"saves": saves, "total": len(saves)})
    return True
