"""时代包校验工具

Usage:
    python tools/validate_era.py eras/wanli1587/era.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def validate_era(era_path: Path) -> list[str]:
    """校验时代包配置

    Returns:
        错误列表（空列表=通过）
    """
    errors = []

    # 1. 文件存在
    if not era_path.exists():
        return [f"[FATAL] 文件不存在: {era_path}"]

    # 2. JSON可解析
    try:
        config = json.loads(era_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"[FATAL] JSON解析失败: {e}"]

    # 3. 顶层必需字段
    for field in ["era_id", "era_name"]:
        if field not in config:
            errors.append(f"[ERROR] 缺少顶层字段: {field}")

    # 4. 顶层四组
    for group in ["world", "mechanics", "growth", "knowledge"]:
        if group not in config:
            errors.append(f"[WARN] 缺少顶层分组: {group}")

    # 5. world分组
    world = config.get("world", {})
    for sub in ["timeline", "player_identities", "iron_laws"]:
        if sub not in world:
            errors.append(f"[ERROR] world.{sub} 缺失")

    # 6. timeline
    timeline = world.get("timeline", {})
    for sub in ["start", "end", "total_rounds"]:
        if sub not in timeline:
            errors.append(f"[WARN] world.timeline.{sub} 缺失")

    # 7. player_identities（v1.1+多身份支持）
    identities = world.get("player_identities", {})
    if identities:
        # 至少要有1个身份
        if not isinstance(identities, dict):
            errors.append("[ERROR] world.player_identities 必须是字典")
        else:
            for id_key, ident in identities.items():
                if not isinstance(ident, dict):
                    errors.append(f"[ERROR] player_identities.{id_key} 不是字典")
                    continue
                for field in ["id", "label", "gender", "role", "action_boundaries"]:
                    if field not in ident:
                        errors.append(f"[ERROR] player_identities.{id_key} 缺少 {field}")
        # 校验default_identity指向存在的身份
        default_id = world.get("default_identity")
        if default_id and default_id not in identities:
            errors.append(f"[ERROR] default_identity '{default_id}' 不在 player_identities 中")
    else:
        errors.append("[ERROR] world.player_identities 缺失（v1.1+必需）")

    # 8. iron_laws
    iron_laws = world.get("iron_laws", [])
    if not iron_laws:
        errors.append("[WARN] world.iron_laws 为空（建议至少3条铁律）")
    for i, law in enumerate(iron_laws):
        if "id" not in law or "fact" not in law:
            errors.append(f"[ERROR] iron_laws[{i}] 缺少 id 或 fact")

    # 9. mechanics分组
    mechanics = config.get("mechanics", {})
    for sub in ["variables", "triggers", "historical_events", "pacing_rules"]:
        if sub not in mechanics:
            errors.append(f"[WARN] mechanics.{sub} 缺失")

    # 10. variables
    variables = mechanics.get("variables", [])
    if not variables:
        errors.append("[ERROR] mechanics.variables 为空（至少1个变量）")
    for i, v in enumerate(variables):
        for field in ["id", "name", "type", "min", "max", "initial"]:
            if field not in v:
                errors.append(f"[ERROR] variables[{i}] 缺少 {field}")

    # 11. historical_events
    events = mechanics.get("historical_events", [])
    if not events:
        errors.append("[WARN] historical_events 为空")
    for i, ev in enumerate(events):
        for field in ["round", "event_id", "event_name"]:
            if field not in ev:
                errors.append(f"[ERROR] historical_events[{i}] 缺少 {field}")

    # 12. growth分组
    growth = config.get("growth", {})
    for sub in ["insight_tree", "value_dimensions", "finale_templates"]:
        if sub not in growth:
            errors.append(f"[WARN] growth.{sub} 缺失")

    # 13. insight_tree
    insights = growth.get("insight_tree", [])
    for i, ins in enumerate(insights):
        for field in ["id", "topic", "prerequisites", "trigger_type"]:
            if field not in ins:
                errors.append(f"[ERROR] insight_tree[{i}] 缺少 {field}")
        # 验证prerequisites指向的id存在
        for prereq in ins.get("prerequisites", []):
            if not any(i["id"] == prereq for i in insights):
                errors.append(f"[ERROR] insight_tree[{i}].prerequisites 引用了不存在的id: {prereq}")

    # 14. value_dimensions
    values = growth.get("value_dimensions", [])
    for i, val in enumerate(values):
        for field in ["id", "name", "max_shift_per_round"]:
            if field not in val:
                errors.append(f"[ERROR] value_dimensions[{i}] 缺少 {field}")

    # 15. knowledge分组
    knowledge = config.get("knowledge", {})
    if "entries" not in knowledge:
        errors.append("[WARN] knowledge.entries 缺失")
    else:
        for i, e in enumerate(knowledge["entries"]):
            for field in ["id", "layer", "title", "content"]:
                if field not in e:
                    errors.append(f"[ERROR] knowledge.entries[{i}] 缺少 {field}")
            if e.get("layer") not in ("background", "scene", "entity", "principle"):
                errors.append(f"[ERROR] knowledge.entries[{i}].layer 非法: {e.get('layer')}")

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_era.py <era.json>")
        sys.exit(1)

    era_path = Path(sys.argv[1])
    print(f"\n校验时代包: {era_path}\n")

    errors = validate_era(era_path)

    if not errors:
        print("✅ 校验通过\n")
        sys.exit(0)

    # 统计错误等级
    fatal = [e for e in errors if e.startswith("[FATAL]")]
    err = [e for e in errors if e.startswith("[ERROR]")]
    warn = [e for e in errors if e.startswith("[WARN]")]

    for e in errors:
        print(e)

    print(f"\n统计: {len(fatal)}个FATAL, {len(err)}个ERROR, {len(warn)}个WARN")

    if fatal or err:
        sys.exit(1)
    else:
        print("(仅有WARN，可继续运行)")
        sys.exit(0)


if __name__ == "__main__":
    main()
