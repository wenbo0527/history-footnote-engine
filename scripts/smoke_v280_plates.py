"""v2.8.0 段五 W17 smoke：板块格局 → 路径自动解锁

场景：
- 初始：hexi_trade 路径 locked（需价值阈值）
- 中原板块张力上升 → 通过传导规则到河西走廊
- 河西走廊 shifting → 触发 PathSwitcher 触发器 3
- hexi_trade 路径被自动 UNLOCK
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from history_footnote.game_state import GameState
from history_footnote.chapter.plates import PlateRegistry
from history_footnote.chapter.plate_engine import PlateEngine
from history_footnote.chapter.paths import PathRegistry
from history_footnote.chapter.path_switcher import PathSwitcher


def main():
    state = GameState()
    state.era_id = "wanli1587"

    era_config = {
        "narrative": {
            "paths": [
                {
                    "id": "hexi_trade",
                    "type": "corridor",
                    "name": "河西商路",
                    "unlock_condition": "value_threshold",
                    "plate_dependency": "hexi_corridor",
                },
                {
                    "id": "tax_main",
                    "type": "main",
                    "name": "抗税",
                    "unlock_condition": "always",
                    "plate_dependency": "central_plains",
                },
            ],
        },
        "plates": {
            "plate_definitions": [
                {"id": "central_plains", "type": "core", "neighbors": ["hexi_corridor"], "base_tension": 0.3},
                {"id": "hexi_corridor", "type": "corridor", "neighbors": ["central_plains"], "base_tension": 0.2},
            ],
            "corridors": [],
            "equilibrium_state": {"central_plains": 0.3, "hexi_corridor": 0.2},
            "transmission_rules": [
                {"from": "central_plains", "to": "hexi_corridor", "factor": 0.4, "delay_rounds": 1},
            ],
        },
    }

    # 初始化
    plate_registry = PlateRegistry(era_config)
    state.plate_state = plate_registry.initialize_state()
    plate_engine = PlateEngine(state, plate_registry)
    path_registry = PathRegistry(era_config)
    path_switcher = PathSwitcher(state, path_registry)

    # 初始：hexi_trade 在 locked（需价值阈值或板块 shifting 触发）
    state.path_state.locked_paths = ["hexi_trade"]
    state.path_state.active_paths = ["tax_main"]

    print("=" * 70)
    print("=== v2.8.0 段五 W17 smoke：板块格局 → 路径解锁 ===")
    print("=" * 70)
    print()
    print(f"初始状态：")
    print(f"  板块张力：{dict(state.plate_state.tensions)}")
    print(f"  路径状态：hexi_trade = locked, tax_main = active")
    print(f"  state.path_state.locked_paths = {state.path_state.locked_paths}")
    print()

    # 第 1 步：中原板块 boost（玩家行为）
    print(">>> Round 5: 中原 boost +0.5 (玩家选择上告苏州府) <<<")
    plate_engine.boost_tension("central_plains", 0.5, current_round=5)
    print(f"  板块张力：{dict(state.plate_state.tensions)}")
    print(f"  状态：central_plains = {state.plate_state.get_status('central_plains')}")
    print()

    # 第 2 步：登记传导（中→河西，delay 1）
    print(">>> 登记传导: central_plains → hexi_corridor (factor=0.4, delay=1) <<<")
    plate_engine.add_transmission("central_plains", "hexi_corridor", current_round=5)
    print(f"  pending_transmissions = {len(state.plate_state.pending_transmissions)} 条")
    print()

    # 第 3 步：推进 1 回合（round 6 触发传导）
    print(">>> Round 6: tick 推进 1 回合 <<<")
    events = plate_engine.tick(current_round=6)
    print(f"  传导事件: {len(events)} 条")
    if events:
        for e in events:
            print(f"    - {e.plate_id}: {e.old_tension:.2f} → {e.new_tension:.2f} ({e.old_status} → {e.new_status})")
    print(f"  板块张力：{dict(state.plate_state.tensions)}")
    print()

    # 反复 boost hexi_corridor 让它 shifting
    print(">>> Round 7-8: 多次 boost hexi_corridor 让它 shifting <<<")
    plate_engine.boost_tension("hexi_corridor", 0.3, current_round=7)
    plate_engine.boost_tension("hexi_corridor", 0.1, current_round=8)
    print(f"  hexi_corridor 张力: {state.plate_state.get_tension('hexi_corridor'):.2f}")
    print(f"  hexi_corridor 状态: {state.plate_state.get_status('hexi_corridor')}")
    print()

    # 第 4 步：PathSwitcher 触发器 3
    print(">>> PathSwitcher._check_plate_shifts (触发器 3) <<<")
    path_events = path_switcher._check_plate_shifts()
    print(f"  路径事件: {len(path_events)} 条")
    for e in path_events:
        print(f"    - {e.type}: {e.path_id} (priority={e.priority}, reason={e.reason[:50]})")
    print()

    # 第 5 步：应用事件
    print(">>> apply_events 应用 <<<")
    PathSwitcher.apply_events(state, path_events)
    print(f"  hexi_trade 状态: {state.path_state.get_status('hexi_trade')}")
    print(f"  state.path_state.active_paths = {state.path_state.active_paths}")
    print(f"  state.path_state.locked_paths = {state.path_state.locked_paths}")
    print()
    print("=" * 70)
    if "hexi_trade" in state.path_state.active_paths:
        print(">>> 段五 W17 交付验证通过：板块格局 → 路径解锁全流程 OK <<<")
    else:
        print(">>> ❌ 路径未被解锁，调试 <<<")
    print("=" * 70)


if __name__ == "__main__":
    main()
