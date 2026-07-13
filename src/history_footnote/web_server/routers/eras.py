"""GET /api/eras — 列出所有可用时代包
GET /api/identities — 列出某时代的可玩身份
"""
from __future__ import annotations

from history_footnote.resource_cache import load_era_config
from history_footnote.web_server.handler_base import safe_route


@safe_route(scope="eras")
def handle_GET_eras(handler, _query) -> bool:
    from pathlib import Path as _P
    root = Path_eras_root()
    out = []
    for era_dir in root.iterdir():
        if era_dir.is_dir() and not era_dir.name.startswith(("_", ".")):
            era_json = era_dir / "era.json"
            if era_json.exists():
                config = load_era_config(era_dir.name)
                timeline = config.get("world", {}).get("timeline", {})
                out.append({
                    "id": config.get("era_id", era_dir.name),
                    "name": config.get("era_name", "未命名"),
                    "version": config.get("version", "?"),
                    "year_range": f"{timeline.get('start', {}).get('year', '?')}-{timeline.get('end', {}).get('year', '?')}",
                    "description": timeline.get("description", "")[:200],
                    "identities_count": len(config.get("world", {}).get("player_identities", {})),
                })
    handler._json(200, {"eras": out})
    return True


@safe_route(scope="identities")
def handle_GET_identities(handler, query) -> bool:
    from urllib.parse import parse_qs
    qs = parse_qs(query)
    era_id = qs.get("era_id", ["wanli1587"])[0]
    config = load_era_config(era_id)
    ids = config.get("world", {}).get("player_identities", {})
    out = [{"id": k, "label": v.get("label", k), "role": v.get("role", ""), "gender": v.get("gender")}
           for k, v in ids.items()]
    handler._json(200, {"identities": out})
    return True


def Path_eras_root():
    """在运行时计算 eras 根目录（处理 src/ 与 tests/ 不同 cwd 的情况）"""
    from pathlib import Path as _P
    here = _P(__file__).resolve()
    # web_server/routers/eras.py → 项目根目录
    return here.parents[4] / "eras"
