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




# 🆕 v2.10.1 W52 P1-1 followup: 处理器已拆到 event_handlers.py
from history_footnote.event_handlers import _HANDLERS, _log, FIN_EVENTS, CITY_IDS, FAM_STATUSES



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
