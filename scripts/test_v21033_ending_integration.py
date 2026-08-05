"""🆕 v2.10.33 P0-3 验证：结局结算能在 /api/state 正确返回

覆盖：
1. _compute_ending 不抛错且返回 None（未触发时）
2. 手动改 cash < 0 后, _compute_ending 返回 bankrupt_beggar 类型
3. format_state 包含 ending 字段
4. 单元 e2e：trigger 一条破产路径, 验证 ending 出现

注意：不依赖 web_server, 直接调用 _compute_ending
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dataclasses import dataclass, field
from history_footnote.ending_system import EndingSystem
from history_footnote.web_server.views.format_state import _compute_ending


@dataclass
class FakeState:
    round_number: int = 5
    cash: float = 0.0
    debt: float = 0.0
    rice: float = 0.0
    current_city: str = "shengze"
    current_date: str = "万历十五年十月初三"
    triggered_events: list = field(default_factory=list)


@dataclass
class FakeGame:
    state: FakeState = field(default_factory=FakeState)


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def main():
    print("=== v2.10.33 P0-3 结局接入 ===\n")
    print("注：EndingSystem 在 round>=10 时总会返回某种结局 (struggling 是兜底)")
    print("    真实场景：玩家触发 ending.modal 应该在 round>=10 且满足触发条件时\n")

    # [1/6] round=1 早期: 不应触发任何 ending (early_game guard)
    print("[1/6] 早期游戏（round=1）→ ending=None（early game）")
    game = FakeGame(state=FakeState(cash=10.0, debt=0.0, round_number=1))
    ending = _compute_ending(game)
    ok = _step("ending is None (early_game)", ending is None, detail=f"got {ending}")

    # [2/6] 破产: cash 长期 < 0
    print("\n[2/6] 破产路径（cash=-5, debt=8, round=15）→ bankrupt_beggar")
    game = FakeGame(state=FakeState(cash=-5.0, debt=8.0, round_number=15))
    ending = _compute_ending(game)
    ok2 = _step("ending is not None", ending is not None)
    if ending:
        ok = _step("ending.type == 'bankrupt_beggar'", ending["type"] == "bankrupt_beggar", detail=f"got {ending['type']}")
        ok = _step("ending.name 含中文", any('\u4e00' <= c <= '\u9fff' for c in ending["name"]))
        ok = _step("ending.icon 非空", bool(ending["icon"]))
        ok = _step("ending.narrative 非空", bool(ending["narrative"]))
        ok = _step("ending.triggered_round == 15", ending["triggered_round"] == 15)
        ok = _step("ending.snapshot.cash == -5", ending["snapshot"]["cash"] == -5.0)
        ok = _step("ending.snapshot.debt == 8", ending["snapshot"]["debt"] == 8.0)
        ok = _step("ending.snapshot.city == 'shengze'", ending["snapshot"]["city"] == "shengze")
    ok = ok and ok2

    # [3/6] round=5 早期: 不应触发任何 ending
    print("\n[3/6] 中早期游戏（round=5）→ ending=None（round < 10）")
    game = FakeGame(state=FakeState(cash=0.0, debt=0.0, round_number=5))
    ending = _compute_ending(game)
    ok = _step("ending is None (round<10)", ending is None, detail=f"got {ending}") and ok

    # [4/6] round=10 健康: 触发 'struggling' 兜底结局（验证系统能返回）
    print("\n[4/6] round=10 健康状态（cash=50）→ 触发兜底结局")
    game = FakeGame(state=FakeState(cash=50.0, debt=0.0, round_number=10))
    ending = _compute_ending(game)
    ok = _step("ending is not None", ending is not None, detail=f"got {ending}") and ok

    # [5/6] _compute_ending 异常不应抛出 (防止阻塞 /api/state)
    print("\n[5/6] 异常状态不应抛错（state 缺字段）")
    @dataclass
    class MinimalState:
        round_number: int = 1
    @dataclass
    class MinimalGame:
        state: MinimalState = field(default_factory=MinimalState)

    try:
        ending = _compute_ending(MinimalGame())
        ok = _step("_compute_ending 不抛错 + 返回 None 或 ending", ending is None or "type" in (ending or {})) and ok
    except Exception as e:
        ok = _step("_compute_ending 不抛错", False, detail=f"raised {e!r}") and ok

    # [6/6] EndingSystem 与 _compute_ending 行为一致 (直接调 EndingSystem().check)
    print("\n[6/6] EndingSystem().check 与 _compute_ending 行为一致")
    es = EndingSystem()
    game = FakeGame(state=FakeState(cash=-5.0, debt=8.0, round_number=15))
    direct = es.check(game.state)
    wrapped = _compute_ending(game)
    direct_type = direct.type if direct else None
    wrapped_type = wrapped["type"] if wrapped else None
    ok = _step(
        "两者触发一致",
        direct_type == wrapped_type,
        detail=f"direct={direct_type} wrapped={wrapped_type}",
    ) and ok

    print("\n=== 汇总 ===")
    if ok:
        print("🎉 P0-3 全部 6 组测试通过")
        sys.exit(0)
    else:
        print(f"❌ 失败")
        sys.exit(1)


if __name__ == "__main__":
    main()