"""🆕 v2.10.1 W52 P1-1 followup: 事件处理器模块

把 event_parser.py 8 个 _apply_xxx 处理器拆出,主模块只保留:
- 解析(parse_events)
- 入口(apply_event / process_llm_output)
- 模糊匹配(Layer 2)

依据 docs/log/2026-07-12-HFE-W52-优化清单-v1.0.md P1-1 followup
"""
from __future__ import annotations

from typing import Any, Callable

# 🆕 命名空间常量（从 event_parser 复用）
FIN_EVENTS = {
    "sell_silk", "buy_thread", "pay_tax", "borrow", "repay",
    "deposit_interest", "debt_interest", "workshop_rent",
    "monthly_burn", "gift_in", "gift_out",
}

CITY_IDS = {"shengze", "suzhou", "hangzhou", "songjiang", "nanjing"}

FAM_STATUSES = {"healthy", "sick", "recovering", "dying", "deceased"}


def _log(logger, msg: str) -> None:
    """统一日志入口"""
    if logger:
        logger.warning(msg)


# ============= 处理器 =============

def _apply_fin_event(state, event: dict, logger=None) -> bool:
    parts = event["id"].split(".")
    if len(parts) < 2 or parts[1] not in FIN_EVENTS:
        return False
    kind = parts[1]
    try:
        amount = float(event.get("amount", 0))
    except (ValueError, TypeError):
        return False
    note = event.get("note", "")
    location = event.get("location", state.current_city)
    # 类型映射：事件 ID → (type_, signed_amount)
    type_map = {
        "sell_silk": ("sell_silk", +abs(amount)),
        "buy_thread": ("buy_thread", -abs(amount)),
        "pay_tax": ("pay_tax", -abs(amount)),
        "borrow": ("borrow", +abs(amount)),
        "repay": ("repay", -abs(amount)),
        "deposit_interest": ("deposit_interest", +abs(amount)),
        "debt_interest": ("debt_interest", -abs(amount)),
        "workshop_rent": ("workshop_rent", +abs(amount)),
        "monthly_burn": ("monthly_burn", -abs(amount)),
        "gift_in": ("gift_in", +abs(amount)),
        "gift_out": ("gift_out", -abs(amount)),
    }
    if kind not in type_map:
        return False
    type_, signed = type_map[kind]
    # 注意：apply_financial_change 会抛 ValueError（业务校验）— 透传给上层
    state.apply_financial_change(signed, type_, note, location)
    return True


def _apply_city_event(state, event: dict, logger=None) -> bool:
    """应用城市事件（arrive/leave）

    🆕 v2.10.1 W77: 城市变更需用户确认
    - 之前 W74: 拦截无 narrative 锚定的 arrive（直接拒绝）
    - 现在：保留 W74 检查 + 通过后**不发立即改 state**
    - 改为写入 state.pending_city_change 字段
    - 前端检测到 pending_city_change → 弹"是否要去 XX"确认
    - 用户确认 → 调 /api/confirm_city_change 真正改 state
    - 用户拒绝 → 调 /api/reject_city_change 保持原 city

    这样玩家不会被 LLM 自由发挥强制移动
    """
    parts = event["id"].split(".")
    if len(parts) < 3:
        return False
    action = parts[1]  # arrive / leave
    city_id = parts[2]
    if action == "arrive" and city_id in CITY_IDS:
        # 同 city → 不需要确认
        if state.current_city == city_id:
            return True
        # W74 检查：narrative 必须含移动关键词（仍保留）
        narrative = (event.get("narrative") or event.get("note") or "").strip()
        travel_keywords = ["船", "行至", "到了", "去了", "来到", "进城", "路过", "坐船", "坐车", "行路", "赶路", "启程", "离开", "动身", "赶去", "抵达"]
        has_travel = any(kw in narrative for kw in travel_keywords)
        if not has_travel:
            if logger:
                logger.warning(f"[W77] arrive 拦截：narrative 无移动关键词（id={event.get('id')}, narrative 前 50 字={narrative[:50]!r}）")
            return True  # 拦截，不进 pending
        # W77: 写入 pending_city_change，等用户确认
        state.pending_city_change = {
            "from_city": state.current_city,
            "to_city": city_id,
            "narrative": narrative[:200],
        }
        if logger:
            logger.info(f"[W77] arrive 待确认：{state.current_city} → {city_id}")
        return True
    if action == "leave":
        if logger:
            logger.info(f"player leave {city_id}")
        return True
    return False


def _apply_fam_event(state, event: dict, logger=None) -> bool:
    parts = event["id"].split(".")
    if len(parts) < 3:
        return False
    action = parts[1]
    if action == "meet" and len(parts) >= 3:
        member_id = parts[2]
        return state.update_family_member(member_id, last_meet_round=state.round_number) is not None
    if action == "health" and len(parts) >= 4:
        member_id = parts[2]
        status = parts[3]
        if status in FAM_STATUSES:
            return state.update_family_member(member_id, health=status) is not None
    if action == "death" and len(parts) >= 3:
        member_id = parts[2]
        return state.update_family_member(member_id, alive=False) is not None
    if action == "relationship" and len(parts) >= 3:
        # fam.relationship.{member_id}.{+/-N}
        member_id = parts[2]
        try:
            delta_str = parts[3] if len(parts) >= 4 else event.get("delta", "0")
            delta = int(delta_str)
            current = state.get_family_member(member_id)
            if not current:
                return False
            new_score = max(0, min(100, current.get("relationship_score", 50) + delta))
            return state.update_family_member(member_id, relationship_score=new_score) is not None
        except (ValueError, IndexError):
            return False
    return False


def _apply_gen_event(state, event: dict, logger=None) -> bool:
    parts = event["id"].split(".")
    if len(parts) < 4 or parts[1] != "ancestor":
        return False
    action = parts[3]  # known / location
    if action == "known":
        entry_id = parts[2]
        # 把 entry 标记为已知
        for e in state.genealogy:
            if e.get("id") == entry_id:
                e["is_known_to_player"] = True
                return True
        return False
    if action == "location":
        entry_id = parts[2]
        new_loc = event.get("location", "shengze")
        return state.update_genealogy_entry(entry_id, location=new_loc) is not None
    return False


def _apply_prop_event(state, event: dict, logger=None) -> bool:
    parts = event["id"].split(".")
    if len(parts) < 3:
        return False
    action = parts[1]
    city_id = parts[2]
    if city_id not in CITY_IDS and city_id != "shengze":
        return False
    if action == "buy":
        prop_id = event.get("prop_id", f"prop_{len(state.city_properties.get(city_id, []))+1:03d}")
        prop_type = event.get("type", "shop")
        prop_name = event.get("name", f"{city_id}新财产")
        try:
            value = float(event.get("value", 0))
            rent = float(event.get("rent_per_month", 0))
        except (ValueError, TypeError):
            return False
        return state.add_property(city_id, {
            "id": prop_id, "type": prop_type, "name": prop_name,
            "value": value, "rent_per_month": rent, "status": "own",
        }) is not None
    if action == "sell":
        prop_id = parts[3] if len(parts) >= 4 else event.get("prop_id", "")
        if not prop_id:
            return False
        # 移除财产
        props = state.city_properties.get(city_id, [])
        before = len(props)
        state.city_properties[city_id] = [p for p in props if p.get("id") != prop_id]
        return len(state.city_properties[city_id]) < before
    if action == "rent_change":
        if len(parts) < 4:
            return False
        prop_id = parts[3]
        try:
            new_rent = float(event.get("rent_per_month", 0))
        except (ValueError, TypeError):
            return False
        for p in state.city_properties.get(city_id, []):
            if p.get("id") == prop_id:
                p["rent_per_month"] = new_rent
                return True
        return False
    return False


def _apply_inv_event(state, event: dict, logger=None) -> bool:
    parts = event["id"].split(".")
    if len(parts) < 3:
        return False
    action = parts[1]
    if action == "buy":
        city_id = parts[2]
        try:
            qty = float(event.get("qty", 0))
        except (ValueError, TypeError):
            return False
        item_id = event.get("item_id", f"inv_{city_id}_{len(state.inventory.get(city_id, []))+1:03d}")
        return state.add_inventory_item(city_id, {
            "id": item_id,
            "type": event.get("type", "goods"),
            "name": event.get("name", "新货"),
            "qty": qty,
            "unit_value": float(event.get("unit_value", 0)),
            "location_in_city": event.get("location_in_city", ""),
        }) is not None
    if action == "sell":
        city_id = parts[2]
        try:
            sell_qty = float(event.get("qty", 0))
        except (ValueError, TypeError):
            return False
        item_id = parts[3] if len(parts) >= 4 else event.get("item_id", "")
        # 从库存减量
        for it in state.inventory.get(city_id, []):
            if it.get("id") == item_id:
                it["qty"] = max(0, it.get("qty", 0) - sell_qty)
                if it["qty"] == 0:
                    state.inventory[city_id] = [x for x in state.inventory[city_id] if x.get("id") != item_id]
                return True
        return False
    if action == "transfer":
        # inv.transfer.{item_id}.{from_city}_{to_city}
        if len(parts) < 4:
            return False
        item_id = parts[2]
        cities = parts[3].split("_")
        if len(cities) != 2:
            return False
        from_city, to_city = cities
        return state.transfer_inventory(item_id, from_city, to_city) is not None
    if action == "consume":
        if len(parts) < 3:
            return False
        item_id = parts[2]
        try:
            consume_qty = float(event.get("qty", 0))
        except (ValueError, TypeError):
            return False
        for items in state.inventory.values():
            for it in items:
                if it.get("id") == item_id:
                    it["qty"] = max(0, it.get("qty", 0) - consume_qty)
                    if it["qty"] == 0:
                        # 移除
                        for city, lst in state.inventory.items():
                            state.inventory[city] = [x for x in lst if x.get("id") != item_id]
                    return True
        return False
    return False


# 处理器映射
_HANDLERS: dict[str, Callable] = {
    "fin": _apply_fin_event,
    "city": _apply_city_event,
    "fam": _apply_fam_event,
    "gen": _apply_gen_event,
    "prop": _apply_prop_event,
    "inv": _apply_inv_event,
}


# ============= 🆕 v1.7.30 discover.* 处理器 =============

def _apply_discover_event(state, event: dict, logger=None) -> bool:
    """discover.* 事件 → state.discoveries（place/person/item/letter/event/fact）"""
    parts = event["id"].split(".")
    if len(parts) < 2:
        return False
    kind = parts[1]
    valid_kinds = {"place", "person", "item", "letter", "event", "fact"}
    if kind not in valid_kinds:
        return False
    # 提取 data 字段（排除 id / source）
    data = {k: v for k, v in event.items() if k not in ("id", "source")}
    source = event.get("source", "save")
    try:
        state.add_discovery(kind, data, source)
        return True
    except ValueError as e:
        _log(logger, f"discover.* failed: {e}")
        return False


# 扩展 HANDLERS
_HANDLERS["discover"] = _apply_discover_event


# ============= 🆕 v1.7.30 evt.* 处理器（重大历史事件） =============

# evt.* 事件 ID → fin.* 内部路由（事件落地）
EVT_ROUTING = {
    # evt.tax.* → fin.*
    "evt.tax.weaving_machine": ("fin.pay_tax", "织机加征 0.3两/机"),
    "evt.tax.silk_per_pi": ("fin.pay_tax", "绸缎加税 0.03-0.05两/匹"),
    "evt.tax.checkpoint": ("fin.pay_tax", "关卡重税"),
    "evt.tax.liao_taxes": ("fin.pay_tax", "辽饷加征"),
    # evt.flood.* → fin.* + state
    "evt.flood.mulberry_loss": ("fin.pay_tax", "桑叶涨价（缺叶年）"),
    "evt.flood.rice_price_spike": ("fin.pay_tax", "米价飞涨"),
    "evt.flood.silk_price_down": ("fin.sell_silk", "丝价跌（被压价）"),
    # evt.war.* → fin.*
    "evt.war.silver_outflow": ("fin.pay_tax", "白银外流（银根紧缩）"),
    "evt.war.transit_disrupted": ("fin.pay_tax", "运河征用（运费涨）"),
    "evt.war.army_demand": ("fin.sell_silk", "军需物资涨价（松江棉布受益）"),
    # evt.chaos.* → fin.* / state
    "evt.chaos.worker_revolt": ("fin.gift_out", "葛贤抗税（织工暴动）"),
    "evt.chaos.armed_conflict": ("fin.pay_tax", "武装冲突"),
}


def _apply_evt_event(state, event: dict, logger=None) -> bool:
    """evt.* 事件 → fin.* 路由（重大历史事件落地）

    例：evt.tax.weaving_machine → fin.pay_tax 写入 state.financial_log
    """
    eid = event.get("id", "")
    if eid not in EVT_ROUTING:
        return False
    type_, default_note = EVT_ROUTING[eid]
    try:
        amount = float(event.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0
    note = event.get("note", default_note)
    location = event.get("location", state.current_city)
    # 路由到 apply_financial_change
    state.apply_financial_change(amount, type_, note, location)
    return True


# 扩展 HANDLERS
_HANDLERS["evt"] = _apply_evt_event


__all__ = ["_HANDLERS", "FIN_EVENTS", "CITY_IDS", "FAM_STATUSES"]
