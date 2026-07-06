"""🆕 v1.7.30 体验版（trial）API 路由

POST /api/trial/start              — 开始体验版
GET  /api/trial/current            — 获取当前 trial
POST /api/trial/increment          — 增加 round（每回合结束）
GET  /api/trial/feedback_required  — 是否需要反馈
POST /api/trial/feedback           — 提交反馈
POST /api/trial/end                — 结束 trial
GET  /api/trial/history            — trial 历史
"""
from __future__ import annotations

from urllib.parse import parse_qs

from history_footnote.account_system import AccountSystem
from history_footnote.web_server.handler_base import logger
from history_footnote.web_server.views.session import _storage_root_for_account


def _get_account_system() -> AccountSystem:
    from history_footnote.web_server.routers.account import _get_account_system
    storage_root = _storage_root_for_account()
    return _get_account_system(storage_root)


def handle_POST_trial_start(handler, body: dict) -> bool:
    """POST /api/trial/start"""
    try:
        sys_inst = _get_account_system()
        trial = sys_inst.start_trial()
        handler._json(200, trial)
    except Exception as e:
        logger.exception(f"[/api/trial/start] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_trial_current(handler, query: str) -> bool:
    """GET /api/trial/current"""
    try:
        sys_inst = _get_account_system()
        trial = sys_inst.get_current_trial()
        handler._json(200, {"trial": trial})
    except Exception as e:
        logger.exception(f"[/api/trial/current] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_trial_increment(handler, body: dict) -> bool:
    """POST /api/trial/increment"""
    try:
        sys_inst = _get_account_system()
        trial = sys_inst.increment_trial_round()
        if trial is None:
            handler._json(404, {"error": "no active trial"})
            return True
        # 检查是否需要反馈
        is_required = sys_inst.is_trial_round_feedback_required()
        handler._json(200, {
            "trial": trial,
            "feedback_required": is_required,
        })
    except Exception as e:
        logger.exception(f"[/api/trial/increment] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_trial_feedback_required(handler, query: str) -> bool:
    """GET /api/trial/feedback_required"""
    try:
        sys_inst = _get_account_system()
        is_required = sys_inst.is_trial_round_feedback_required()
        handler._json(200, {"feedback_required": is_required})
    except Exception as e:
        logger.exception(f"[/api/trial/feedback_required] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_trial_feedback(handler, body: dict) -> bool:
    """POST /api/trial/feedback
    Body: {feedback, contact}
    """
    feedback = (body.get("feedback") or "").strip()
    contact = (body.get("contact") or "").strip()
    if not feedback:
        handler._json(400, {"error": "feedback 必填"})
        return True
    try:
        sys_inst = _get_account_system()
        ok = sys_inst.submit_trial_feedback(feedback, contact)
        if not ok:
            handler._json(404, {"error": "no active trial"})
            return True
        handler._json(200, {"ok": True})
    except Exception as e:
        logger.exception(f"[/api/trial/feedback] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_POST_trial_end(handler, body: dict) -> bool:
    """POST /api/trial/end"""
    try:
        sys_inst = _get_account_system()
        trial = sys_inst.end_trial()
        handler._json(200, {"trial": trial})
    except Exception as e:
        logger.exception(f"[/api/trial/end] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True


def handle_GET_trial_history(handler, query: str) -> bool:
    """GET /api/trial/history"""
    try:
        from pathlib import Path
        sys_inst = _get_account_system()
        # _load_trial 私有
        trial = sys_inst._load_trial()
        handler._json(200, {
            "current": trial.get("current"),
            "history": trial.get("history", []),
        })
    except Exception as e:
        logger.exception(f"[/api/trial/history] 失败: {e}")
        handler._json(500, {"error": str(e)})
    return True
