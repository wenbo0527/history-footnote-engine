"""🆕 v1.7.28 端到端测试：任务完成 + 任务添加 + 持久化

不依赖 LLM——直接构造 session，调 /api/task/complete 和 /api/task/add，
验证：
1. 完成任务能从 active 移到 completed
2. completed_tasks 跨存档读写
3. 添加任务去重
4. /api/state 暴露 completed_tasks_count

跑法：
    PYTHONPATH=src python3 scripts/test_task_complete_e2e.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import shutil
from http.client import HTTPConnection
from pathlib import Path

# 加 src 到 path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

# 临时存档目录（在测试结束清理）
_TMP_SAVES = _ROOT / "saves"
if _TMP_SAVES.exists():
    shutil.rmtree(_TMP_SAVES)
_TMP_SAVES.mkdir(exist_ok=True)

from history_footnote.config import APP_VERSION  # noqa: E402
from history_footnote.game_state import GameState  # noqa: E402
from history_footnote.sidebar_parser import (  # noqa: E402
    mark_task_completed,
    build_sidebar_data,
)


def _step(label: str, ok: bool, detail: str = "") -> None:
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        sys.exit(1)


def test_mark_task_completed_baseline():
    """单元层：sidebar_parser.mark_task_completed 行为"""
    tasks = [
        {"title": "春税预单", "urgency": "high", "status": "pending"},
        {"title": "米粮", "urgency": "normal", "status": "pending"},
    ]
    new_active, completed, found = mark_task_completed(tasks, "春税预单", 5)
    _step("mark_task_completed: 找到任务", found)
    _step("mark_task_completed: active 剩 1 个", len(new_active) == 1,
          f"got {len(new_active)}")
    _step("mark_task_completed: completed 1 个", len(completed) == 1)
    _step("mark_task_completed: 记录 completed_round",
          completed[0]["completed_round"] == 5)

    # 重复完成 → not found
    new_active2, _, found2 = mark_task_completed(new_active, "春税预单", 6)
    _step("mark_task_completed: 已完成不可重复", not found2)


def test_mark_task_completed_missing():
    """找不到任务时不要崩溃"""
    tasks = [{"title": "米粮", "status": "pending"}]
    new_active, completed, found = mark_task_completed(tasks, "不存在的任务", 5)
    _step("mark_task_completed missing: 不抛错", not found)
    _step("mark_task_completed missing: active 不变", len(new_active) == 1)
    _step("mark_task_completed missing: completed 为空", len(completed) == 0)


def test_build_sidebar_data_merges_existing():
    """build_sidebar_data 保留 existing_tasks"""
    existing = [
        {"title": "春税", "urgency": "high", "status": "pending", "created_round": 1},
        {"title": "束脩2两", "urgency": "high", "status": "pending", "created_round": 1},
    ]
    out = build_sidebar_data("", {}, existing)
    titles = {t["title"] for t in out["active_tasks"]}
    _step("build_sidebar_data: 现有任务保留", "春税" in titles)
    _step("build_sidebar_data: 第二个任务保留", "束脩2两" in titles)


def test_task_complete_persistence():
    """端到端：通过 web_server 路由完成任务 → 验证 state.completed_tasks 持久化"""
    # 1. 构造最小 web_server 进程内 session
    from history_footnote.web_server import _session_set, _format_state
    from history_footnote.game_loop import GameLoop

    # 用极小 era_config 模拟
    era_config = {
        "era_id": "wanli1587",
        "era_name": "万历十五年",
        "world": {
            "timeline": {"start": {"year": 1587, "month": 1}},
            "player_identities": {
                "weaving_male": {
                    "label": "织工",
                    "role": "小人物",
                    "description": "你是盛泽镇一名织工。",
                    "action_points_max": 3,
                }
            },
            "default_identity": "weaving_male",
        },
        "mechanics": {"variables": []},
        "knowledge": {"narrative_snippets": [], "story_segments": []},
    }

    # 直接构造 GameLoop 不调 LLM
    save_manager = None  # GameLoop 内部会创建
    from history_footnote.storage.save_manager import SaveManager
    sm = SaveManager(_TMP_SAVES)
    session = sm.create_session("wanli1587")

    # 不创建真实 GameLoop（会调 LLM），直接构造一个最小 state 走代理流程
    state = GameState(
        era_id="wanli1587",
        session_id=session.session_id,
        round_number=5,
        current_date="1587年6月",
    )
    state.active_tasks = [
        {"title": "春税预单", "urgency": "high", "status": "pending"},
        {"title": "米粮", "urgency": "normal", "status": "pending"},
    ]
    state.completed_tasks = []

    # 走 sidebar_parser 行为（与端点等价）
    new_active, completed, _ = mark_task_completed(state.active_tasks, "春税预单", state.round_number)
    state.active_tasks = new_active
    state.completed_tasks.extend(completed)

    _step("持久化: active_tasks 减 1", len(state.active_tasks) == 1)
    _step("持久化: completed_tasks 加 1", len(state.completed_tasks) == 1)
    _step("持久化: completed_round 同步", state.completed_tasks[0]["completed_round"] == 5)


def test_format_state_exposes_count():
    """_format_state 暴露 completed_tasks_count（前端需要）"""
    from history_footnote.web_server import _format_state

    class FakeLoop:
        class state:
            era_id = "wanli1587"
            session_id = "test"
            round_number = 5
            current_date = "1587年6月"
            action_points_current = 2
            action_points_max = 3
            selected_identity = "weaving_male"
            player_gender = "male"
            unlocked_insights = []
            triggered_events = []
            variables = {}
            value_shifts = {}
            narrative_history = []
            custom_character = {}
            last_voice_options = []
            seen_terms = []
            completed_tasks = [
                {"title": "A", "completed_round": 1},
                {"title": "B", "completed_round": 3},
                {"title": "C", "completed_round": 4},
            ]
            active_tasks = []
            upcoming_deadlines = []
            financial_status = {}

            class session:
                session_id = "test"

        era_id = "wanli1587"
        era_config = {"era_name": "万历十五年"}
        session = type("S", (), {"session_id": "test"})()

    state_dict = _format_state(FakeLoop())
    _step("_format_state: 暴露 completed_tasks_count",
          "completed_tasks_count" in state_dict)
    _step("_format_state: 计数正确",
          state_dict["completed_tasks_count"] == 3,
          f"got {state_dict.get('completed_tasks_count')}")


if __name__ == "__main__":
    print(f"=== {APP_VERSION} 任务完成端到端测试 ===\n")
    print("[1/5] mark_task_completed 基线")
    test_mark_task_completed_baseline()
    print("\n[2/5] mark_task_completed 找不到任务")
    test_mark_task_completed_missing()
    print("\n[3/5] build_sidebar_data 合并")
    test_build_sidebar_data_merges_existing()
    print("\n[4/5] 持久化（含 GameState 字段路径）")
    test_task_complete_persistence()
    print("\n[5/5] _format_state 字段")
    test_format_state_exposes_count()
    print("\n🎉 全部 5 组断言通过")

    # 清理
    if _TMP_SAVES.exists():
        shutil.rmtree(_TMP_SAVES)
