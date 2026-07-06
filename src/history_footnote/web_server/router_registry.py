"""🆕 v1.7.29 路由注册表

用 (method, path) -> handler 的 dict 把所有路由集中到一处，
方便新增路由、AI/工具扫描、OpenAPI 自动生成。

每个 handler 签名：
- handle_POST(handler, body: dict) -> bool
- handle_GET(handler, query: str) -> bool
  （True = 已处理；web_server.Handler 据此决定是否再尝试别处）

调用约定：
- 路由 handler 必须通过 handler._json() 返回响应
- handler 内部不直接用 self.client_address，统一用 handler._rate_limit_or_429()
"""
from __future__ import annotations

from urllib.parse import parse_qs

from history_footnote.web_server.routers import (
    account as _account,
    admin as _admin,
    character as _character,
    eras as _eras,
    glossary as _glossary,
    input as _input,
    misc as _misc,
    observability as _observability,
    session as _session_router,
    state as _state,
    tasks as _tasks,
    trial as _trial,
    voice_suggest as _voice_suggest,
)


def _q(query_str: str, key: str, default=""):
    qs = parse_qs(query_str)
    return qs.get(key, [default])[0]


# ============================================================
# 路由表：(method, path_substring) -> handler
# ============================================================

# GET 路由：路径直接映射到处理函数
GET_ROUTES = {
    "/metrics": _observability.handle_GET_metrics,
    "/health": _observability.handle_GET_health,
    "/api/eras": _eras.handle_GET_eras,
    "/api/identities": _eras.handle_GET_identities,
    "/api/state": _state.handle_GET_state,
    "/api/feedback_categories": _misc.handle_GET_feedback_categories,
    "/api/llm/stats": _observability.handle_GET_llm_stats,
    "/api/llm/reset_stats": _observability.handle_GET_llm_reset_stats,
    "/api/monitor/health": _observability.handle_GET_monitor_health,
    "/api/monitor/stats": _observability.handle_GET_monitor_stats,
    "/api/archives": _session_router.handle_GET_archives,
    "/api/character_wiki": _character.handle_GET_character_wiki,
    # 🆕 v1.7.30 账户系统
    "/api/account/saves": _account.handle_GET_account_saves,
    "/api/account/info": _account.handle_GET_account_info,
    "/api/account/invite_codes": _account.handle_GET_account_invite_codes,
    # 🆕 v1.7.30 管理员
    "/api/admin/users": _admin.handle_GET_admin_users,
    "/api/admin/saves": _admin.handle_GET_admin_saves,
    "/api/admin/tokens": _admin.handle_GET_admin_tokens,
    "/api/admin/config": _admin.handle_GET_admin_config,
    # 🆕 v1.7.30 体验版
    "/api/trial/current": _trial.handle_GET_trial_current,
    "/api/trial/feedback_required": _trial.handle_GET_trial_feedback_required,
    "/api/trial/history": _trial.handle_GET_trial_history,
    # 🆕 v1.7.30 体验版管理（admin）
    "/api/admin/trials": _admin.handle_GET_admin_trials,
}

# POST 路由
POST_ROUTES = {
    "/api/generate_character": _misc.handle_POST_generate_character,
    "/api/generate_world_dwell": _misc.handle_POST_generate_world_dwell,
    "/api/lore": _misc.handle_POST_lore,
    "/api/start": _session_router.handle_POST_start,
    "/api/recap": _character.handle_POST_recap,
    "/api/glossary": _glossary.handle_POST_glossary,
    "/api/extract_terms": _glossary.handle_POST_extract_terms,
    "/api/mark_term_seen": _glossary.handle_POST_mark_term_seen,
    "/api/sanitize": _glossary.handle_POST_sanitize,
    "/api/dilemma": _input.handle_POST_dilemma,
    "/api/task/complete": _tasks.handle_POST_task_complete,
    "/api/task/add": _tasks.handle_POST_task_add,
    "/api/sanitize_patterns": _glossary.handle_GET_sanitize_patterns,
    "/api/version": _misc.handle_GET_version,  # 原 do_POST 中也响应这 3 个 GET 端点（向后兼容）
    "/api/feedback": _misc.handle_POST_feedback,
    "/api/feedback_categories": _misc.handle_GET_feedback_categories,  # 同上
    "/api/merge_voice_options": _input.handle_POST_merge_voice_options,
    "/api/render_narrative": _input.handle_POST_render_narrative,
    "/api/character_wiki_update": _character.handle_POST_character_wiki_update,
    "/api/input": _input.handle_POST_input,
    "/api/load": _state.handle_POST_load,
    "/api/archive/delete": _session_router.handle_POST_archive_delete,
    "/api/archives/clear": _session_router.handle_POST_archives_clear,
    "/api/input_stream": _input.handle_POST_input_stream,
    "/api/voice_options/suggest": _voice_suggest.handle_POST_voice_options_suggest,
    # 🆕 v1.7.30 账户系统
    "/api/account/register": _account.handle_POST_account_register,
    "/api/account/login": _account.handle_POST_account_login,
    "/api/account/saves": _account.handle_POST_account_create_save,
    # 🆕 v1.7.30 管理员
    "/api/admin/config": _admin.handle_POST_admin_config,
    "/api/admin/users/role": _admin.handle_POST_admin_user_role,
    "/api/admin/users/delete": _admin.handle_DELETE_admin_user,
    "/api/admin/saves/delete": _admin.handle_DELETE_admin_save,
    # 🆕 v1.7.30 体验版
    "/api/trial/start": _trial.handle_POST_trial_start,
    "/api/trial/increment": _trial.handle_POST_trial_increment,
    "/api/trial/feedback": _trial.handle_POST_trial_feedback,
    "/api/trial/end": _trial.handle_POST_trial_end,
    # 🆕 v1.7.30 体验版管理（admin）
    "/api/admin/grant_trial_invite": _admin.handle_POST_admin_grant_trial_invite,
}


# ============================================================
# 派发
# ============================================================

def dispatch_GET(handler, path: str, query: str) -> bool:
    """按 GET_ROUTES 派发；返回 True 表示已处理（包括发 404）。

    没有命中的 path 不视为已处理，由 Handler 返回 404 兜底。
    """
    # 静态资源（/static/*）— 必须先匹配
    if path.startswith("/static/"):
        handler._serve_static(path)
        return True
    if path == "/" or path == "/index.html":
        from history_footnote.web_server.static_assets import INDEX_HTML
        handler._html(INDEX_HTML)
        return True
    handler_fn = GET_ROUTES.get(path)
    if handler_fn is None:
        return False
    # 真函数签名约定：
    #   handle_GET_xxx(handler)         — 无 query 参数（如 /metrics /health）
    #   handle_GET_xxx(handler, query)   — 需 query 参数（带 ?xxx=）
    sig = _inspect_signature(handler_fn)
    if sig == 1:
        handler_fn(handler)
    else:
        handler_fn(handler, query)
    return True


def dispatch_POST(handler, path: str, body: dict) -> bool:
    handler_fn = POST_ROUTES.get(path)
    if handler_fn is None:
        return False
    handler_fn(handler, body)
    return True


def _inspect_signature(fn) -> int:
    """通过函数名前缀决定参数个数，避开 inspect 反射开销。

    约定：所有 routers 函数遵循 handle_<METHOD>_<name> 命名。
    - handle_GET_*(): 1 参数（handler）
    - handle_POST_*: 2 参数（handler, body）
    - handle_GET_*:  2 参数（handler, query）默认
    """
    name = fn.__name__
    # 例外列表（不接 query 参数的）
    NO_QUERY_FNS = {
        "handle_GET_metrics",
        "handle_GET_health",
        "handle_GET_llm_reset_stats",
        "handle_GET_monitor_health",
        "handle_GET_monitor_stats",
        "handle_GET_version",
        "handle_GET_feedback_categories",
        "handle_GET_sanitize_patterns",
    }
    if name in NO_QUERY_FNS:
        return 1
    if name.startswith("handle_POST_"):
        return 2
    if name.startswith("handle_GET_"):
        return 2
    # 其它：默认 1
    return 1
