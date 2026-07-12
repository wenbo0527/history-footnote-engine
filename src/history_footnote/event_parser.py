"""🆕 v1.7.30 事件 ID 解析器（Event Parser）

从 LLM 输出解析 <events> 块 → 列表化事件 → apply_event 到 GameState。

3 层识别：
- Layer 1: DM 显式输出 <events> 块（100% 准确）
- Layer 2: narrative 模糊匹配（verb+amount+object）
- Layer 3: 玩家主动标注（v1.7.30+ 后续）

设计文档：docs/architecture/EventId规范.md
"""
from __future__ import annotations

import re
from typing import Any, Callable

# 事件块正则
EVENT_BLOCK_RE = re.compile(
    r"<events>(.*?)</events>",
    re.DOTALL,
)

# 单事件正则（attrs 接受 / 因为属性值可能含 /）
EVENT_RE = re.compile(
    r'<event\s+id="(?P<id>[^"]+)"\s+(?P<attrs>.*?)\s*/>',
    re.DOTALL,
)

# 属性正则
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


# ============= 事件 ID 命名空间 =============

FIN_EVENTS = {
    "sell_silk", "buy_thread", "pay_tax", "borrow", "repay",
    "deposit_interest", "debt_interest", "workshop_rent",
    "monthly_burn", "gift_in", "gift_out",
}

CITY_IDS = {"shengze", "suzhou", "hangzhou", "songjiang", "nanjing"}

FAM_STATUSES = {"healthy", "sick", "recovering", "dying", "deceased"}


# ============= 解析器 =============

def parse_events(llm_output: str) -> list[dict]:
    """从 LLM 输出解析 <events> 块

    Returns:
        事件列表 [{id, ...attrs}, ...]
    """
    events = []
    for block_match in EVENT_BLOCK_RE.finditer(llm_output or ""):
        block = block_match.group(1)
        for ev_match in EVENT_RE.finditer(block):
            eid = ev_match.group("id")
            attrs = dict(ATTR_RE.findall(ev_match.group("attrs")))
            events.append({"id": eid, **attrs})
    return events


# ============= 应用器 =============

def apply_event(state, event: dict, logger=None) -> bool:
    """应用单个事件到 GameState（带校验）

    Returns: True 成功 / False 跳过
    Raises:
        ValueError: 当事件触发业务校验失败（如金额超限）—— 透传不吞
    """
    eid = event.get("id", "")
    if not eid:
        return False
    domain = eid.split(".")[0]
    handler = _HANDLERS.get(domain)
    if handler is None:
        _log(logger, f"unknown domain: {domain} in event {eid}")
        return False
    return handler(state, event, logger)


def _log(logger, msg: str) -> None:
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
    
    🆕 v2.10.1 W74: city 改变需叙事锚定
    - LLM 输 arrive.X 会改 state.current_city → 玩家看到"突然到苏州"
    - 修复：必须 narrative 含 "船" 或 "行至/到/去 X" 才生效
    - 否则 log warning + return False（不改 city）
    """
    parts = event["id"].split(".")
    if len(parts) < 3:
        return False
    action = parts[1]  # arrive / leave
    city_id = parts[2]
    if action == "arrive" and city_id in CITY_IDS:
        # 🆕 W74: 检查 narrative 是否描述了"行至/到/船"等移动行为
        narrative = (event.get("narrative") or event.get("note") or "").strip()
        # 移动关键词：船 / 行至 / 到了 / 去了 / 来到 / 路过 / 进城
        travel_keywords = ["船", "行至", "到了", "去了", "来到", "进城", "路过", "坐船", "坐车", "行路", "赶路", "启程", "离开", "动身", "赶去", "抵达"]
        has_travel = any(kw in narrative for kw in travel_keywords)
        if not has_travel:
            if logger:
                logger.warning(f"[W74] city 突变被拦截：narrative 无移动关键词（id={event.get('id')}, narrative 前 50 字={narrative[:50]!r}）")
            # 仍标记事件"已处理"（避免 LLM 重复触发），但不改 state
            return True
        state.current_city = city_id
        return True
    if action == "leave":
        # leave 是"离开到其他城市"——只清 location 标记，city 需在 arrive 之前/之后处理
        # 这里用 note 字段记录离开信息
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


# ============= Layer 2: 模糊匹配 fallback =============

# 常用动作动词
ACTION_VERBS = {
    "卖": "sell", "售": "sell", "卖得": "sell", "售出": "sell",
    "买": "buy", "购": "buy", "买入": "buy", "购入": "buy",
    "借": "borrow", "借入": "borrow", "借款": "borrow",
    "还": "repay", "还了": "repay", "归还": "repay", "还款": "repay",
    "缴": "pay", "纳": "pay", "交": "pay", "缴纳": "pay", "交纳": "pay",
}

# 🆕 v1.7.30 城市模糊匹配（vague 模式，无显式 events 时兜底）
CITY_PATTERNS = [
    (r"去?苏州|赴苏州|入苏州|到苏州|搭船去苏州|在苏州", "suzhou"),
    (r"去?杭州|赴杭州|入杭州|到杭州|在杭州", "hangzhou"),
    (r"去?松江|赴松江|到松江|在松江", "songjiang"),
    (r"去?南京|赴南京|入南京|到南京|进京|在南京", "nanjing"),
    (r"回[到]?盛泽|回乡|回家|返[回]?盛泽|在盛泽", "shengze"),
]

# 🆕 v1.7.30 物品模糊匹配（narrative 中提到物品 → discover.item）
ITEM_PATTERNS = [
    # (pattern, name_hint, type_hint)
    (r"一?匹[湖]?绫[丝]?|绸缎[子匹]?|丝绸|绢", "绸缎", "silk_bolt"),
    (r"一?件[衣裳衣服]+|长衫|短褂", "衣物", "clothing"),
    (r"[玉]?佩|玉[器镯]?", "玉佩", "jewelry"),
    (r"织机|梭子|经线|纬线", "织机", "loom"),
    (r"[一]?[个]?[米粮谷糙]?[粮]?[饭]?[米]+|米[粮]?", "米", "rice"),
    (r"银[子两钱]|白银", "银两", "silver"),
    (r"信|家书|书信|书[一封]?", "信件", "letter"),
    (r"酒|黄酒|米酒", "酒", "alcohol"),
]

# 🆕 v1.7.30 家人模糊匹配
FAMILY_PATTERNS = [
    (r"沈氏|妻子|娘子|老婆|内人", "fm_wife"),
    (r"老娘|母亲|娘亲|妈|母", "fm_mother"),
    (r"老父|父亲|爹|父", "fm_father"),
    (r"儿子|娃|孩子|小儿", "fm_son"),
    (r"女儿|闺女|小女", "fm_daughter"),
]

# 金额正则（支持阿拉伯数字 + 简单中文数字）
CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "半": 0.5}

def _parse_amount(s: str) -> float | None:
    """解析金额字符串，支持 '5' / '5.5' / '五' / '半' / '十五' 等"""
    if not s:
        return None
    s = s.strip()
    # 阿拉伯数字
    try:
        return float(s)
    except ValueError:
        pass
    # 简单中文数字（单字 + 十几）
    if s in CN_DIGITS:
        return float(CN_DIGITS[s])
    if s.startswith("十") and len(s) == 2:
        # 十五
        return 10.0 + CN_DIGITS.get(s[1], 0)
    if s.endswith("十") and len(s) == 2:
        # 二十
        return CN_DIGITS.get(s[0], 0) * 10.0
    return None


AMOUNT_RE = re.compile(r"(\d+\.?\d*|[零一二三四五六七八九十半]+)\s*(两|钱|文|分)")


def fuzzy_match_events(narrative: str) -> list[dict]:
    """从 narrative 文本模糊匹配事件（Layer 2 fallback）

    Returns:
        推断出的事件列表
    """
    events = []
    # 匹配 "卖了一匹湖绫 + 0.5 两"
    for verb_cn, verb_en in ACTION_VERBS.items():
        if verb_cn not in narrative:
            continue
        # 找 verb 附近 50 字的 amount
        for m in re.finditer(re.escape(verb_cn), narrative):
            start = max(0, m.start() - 20)
            end = min(len(narrative), m.end() + 50)
            context = narrative[start:end]
            amt_match = AMOUNT_RE.search(context)
            if amt_match:
                amount = _parse_amount(amt_match.group(1))
                if amount is None:
                    continue
                unit = amt_match.group(2) or ""
                if unit == "钱":
                    amount = amount / 10
                elif unit == "文":
                    amount = amount / 1000
                # 推断 type
                type_ = _infer_type_from_context(context)
                events.append({
                    "id": f"fin.{type_}",
                    "amount": str(amount),
                    "note": context[:20] + "...",
                    "_fuzzy": True,
                })
    return events


def _infer_type_from_context(context: str) -> str:
    """根据上下文推断交易类型"""
    if "绸" in context or "绫" in context or "丝" in context:
        return "sell_silk" if any(v in context for v in ["卖", "售"]) else "buy_thread"
    if "税" in context or "赋" in context or "差役" in context:
        return "pay_tax"
    if "借" in context or "贷" in context:
        return "borrow"
    if "还" in context or "归" in context:
        return "repay"
    if "礼" in context or "赠" in context:
        return "gift_out" if any(v in context for v in ["送", "给"]) else "gift_in"
    return "sell_silk"  # 默认


# ============= 顶层接口 =============

def process_llm_output(state, llm_output: str, logger=None) -> dict:
    """处理 LLM 完整输出：解析 + 应用事件

    Returns:
        {"events_parsed": N, "events_applied": M, "fallback_used": K}
    """
    result = {"events_parsed": 0, "events_applied": 0, "fallback_used": 0}
    # Layer 1: 显式 <events> 块
    events = parse_events(llm_output)
    result["events_parsed"] = len(events)
    for ev in events:
        if apply_event(state, ev, logger):
            result["events_applied"] += 1
    # Layer 2: 模糊匹配（仅当 Layer 1 解析出 0 个 fin 事件时）
    if not any(e.get("id", "").startswith("fin.") for e in events):
        # 提取 narrative 部分（避免对 events 块本身做模糊匹配）
        narrative = re.sub(r"<events>.*?</events>", "", llm_output, flags=re.DOTALL)
        fuzzy_events = fuzzy_match_events(narrative)
        for ev in fuzzy_events:
            if apply_event(state, ev, logger):
                result["events_applied"] += 1
                result["fallback_used"] += 1
    # 🆕 v1.7.30 Layer 2 扩展：city.* / discover.* / fam.* 模糊匹配
    # 仅当 Layer 1 没有解析到对应类型时才触发（避免重复）
    has_city = any(e.get("id", "").startswith("city.") for e in events)
    has_discover = any(e.get("id", "").startswith("discover.") for e in events)
    has_fam = any(e.get("id", "").startswith("fam.") for e in events)
    narrative = re.sub(r"<events>.*?</events>", "", llm_output, flags=re.DOTALL)
    if not has_city:
        for ev in fuzzy_match_cities(narrative):
            if apply_event(state, ev, logger):
                result["events_applied"] += 1
                result["fallback_used"] += 1
    if not has_discover:
        for ev in fuzzy_match_discoveries(narrative, state):
            if apply_event(state, ev, logger):
                result["events_applied"] += 1
                result["fallback_used"] += 1
    if not has_fam:
        for ev in fuzzy_match_family(narrative):
            if apply_event(state, ev, logger):
                result["events_applied"] += 1
                result["fallback_used"] += 1
    return result


# ============= 🆕 v1.7.30 Layer 2 扩展函数 =============

def fuzzy_match_cities(narrative: str) -> list[dict]:
    """从 narrative 模糊匹配 city.arrive.* 事件"""
    if not narrative:
        return []
    results = []
    seen = set()
    for pattern, city_id in CITY_PATTERNS:
        if city_id in seen:
            continue
        if re.search(pattern, narrative):
            seen.add(city_id)
            results.append({
                "id": f"city.arrive.{city_id}",
                "note": f"模糊匹配：narrative 提到 {city_id}",
                "_fuzzy": True,
            })
    return results


def fuzzy_match_discoveries(narrative: str, state) -> list[dict]:
    """从 narrative 模糊匹配 discover.item 事件（物品）"""
    if not narrative:
        return []
    results = []
    seen = set()
    # 物品（限制：每个物品最多 1 次）
    for pattern, name_hint, type_hint in ITEM_PATTERNS:
        if name_hint in seen:
            continue
        m = re.search(pattern, narrative)
        if not m:
            continue
        # 已有该物品就不重复添加
        existing_items = [it.get("name") for it in state.discoveries.get("items", {}).values()]
        if name_hint in existing_items:
            seen.add(name_hint)
            continue
        seen.add(name_hint)
        results.append({
            "id": "discover.item",
            "name": name_hint,
            "type": type_hint,
            "owner": getattr(state, "current_city", "shengze"),
            "description": f"narrative 中提到（{m.group(0)}）",
            "_fuzzy": True,
        })
    return results


def fuzzy_match_family(narrative: str) -> list[dict]:
    """从 narrative 模糊匹配 fam.meet.* 事件（家人）"""
    if not narrative:
        return []
    results = []
    seen = set()
    for pattern, family_id in FAMILY_PATTERNS:
        if family_id in seen:
            continue
        if re.search(pattern, narrative):
            seen.add(family_id)
            results.append({
                "id": f"fam.meet.{family_id}",
                "note": "narrative 中提到",
                "_fuzzy": True,
            })
    return results
