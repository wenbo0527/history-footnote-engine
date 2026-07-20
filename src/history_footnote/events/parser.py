"""🆕 v1.7.30 事件 ID 解析器（Event Parser）

从 LLM 输出解析 <events> 块 → 列表化事件 → apply_event 到 GameState。

3 层识别：
- Layer 1: DM 显式输出 <events> 块（100% 准确）
- Layer 2: narrative 模糊匹配（verb+amount+object）
- Layer 3: 玩家主动标注（v1.7.30+ 后续）

设计文档：docs/architecture/EventId规范.md
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

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

    🆕 v2.10.12+ 修复（cr30 coherence check 后）:
    - iter 变量名 bug：之前 `for verb_cn in ACTION_VERBS.items()` 直接拿 tuple 当 dict 来 for-in，
      TypeError 一直被静默 catch；现在改成 `verb_cn, verb_en`。
    - 还/归 误判：直接给"还"就 return `repay`，导致 "还让沈氏……"、"归还于……" 等被识别成 repay。
      解决：必须前后 6 字内有 "债/贷/欠/借款/本金/利/借/银/账" 等真实还款语义词才认 `repay`。
    - 排除"算田契"、"算账"、"归拢"等关键词：动作=repay 必须**先确认主语是真还款**，否则跳过。
    - 多 verb 冲突：当 narrative 同时出现 "还" + "借"（如"还了借款"），按 verb priority 排重。
    """
    events: list[dict] = []
    # 🆕 v2.10.12+: 真实还款场景必备词
    REPAY_KEYWORDS = {"债", "欠", "借", "贷", "本金", "利息", "利钱", "账", "银子欠"}
    # 🆕 v2.10.12+: 非交易的"还/归"语境
    REPAY_NEGATIVE_CTX = {"算账", "归拢", "算", "盘算", "打算", "打算", "心里", "想", "说着"}
    # 🆕 v2.10.12+: verb 优先级（数字越小越优先）
    # 用于多 verb 冲突时去重：玩家说"还了借款"应识别为"repay"而非"borrow"
    # （因为还款动作比提到旧借款更重要）
    VERB_PRIORITY = {
        # 还款类
        "归还": 1, "还清": 1, "还了": 2, "还": 3,
        # 借款类
        "借": 10, "借入": 10, "借款": 10, "贷款": 10,
        # 交易类
        "卖": 4, "售": 4, "卖得": 4, "售出": 4,
        "买": 5, "购": 5, "买入": 5, "购入": 5,
        # 缴税类
        "缴": 6, "纳": 6, "交": 6, "缴纳": 6, "交纳": 6,
        # 借出/借入
        "借出": 7, "贷出": 7,
    }

    # 第一遍：所有 verb 匹配都收，附 priority + position
    raw_hits: list[dict] = []
    for verb_cn, verb_en in ACTION_VERBS.items():
        if verb_cn not in narrative:
            continue
        # 找 verb 附近 50 字的 amount
        for m in re.finditer(re.escape(verb_cn), narrative):
            start = max(0, m.start() - 20)
            end = min(len(narrative), m.end() + 50)
            context = narrative[start:end]
            amt_match = AMOUNT_RE.search(context)
            if not amt_match:
                continue
            amount = _parse_amount(amt_match.group(1))
            if amount is None:
                continue
            unit = amt_match.group(2) or ""
            if unit == "钱":
                amount = amount / 10
            elif unit == "文":
                amount = amount / 1000
            raw_hits.append({
                "verb_cn": verb_cn,
                "verb_en": verb_en,
                "pos": m.start(),
                "context": context,
                "amount": amount,
                # 🆕 v2.10.12+: 直接从 verb_en 映射（之前 _infer_type_from_context 在
                # "还了借款" 这种情况会优先 borrow，因为 "借" 字先匹配）
                "type": _verb_en_to_fin(verb_en, context),
            })

    # 第二遍：去重（同一 amount 只能由一个 verb 负责）
    # 按 priority 排序，priority 小的先入 events
    raw_hits.sort(key=lambda x: (VERB_PRIORITY.get(x["verb_cn"], 99), x["pos"]))

    seen_amounts: set[float] = set()
    for h in raw_hits:
        # 同一金额只处理一次（避免"还了借款"既算 repay 又算 borrow）
        if h["amount"] in seen_amounts:
            continue
        seen_amounts.add(h["amount"])

        type_ = h["type"]
        context = h["context"]
        verb_cn = h["verb_cn"]

        # 🆕 v2.10.12+: 当推断出 repay，但 context 不含还款必备词时 → 转 sell_silk 兜底（保守）
        if type_ == "repay" and not any(kw in context for kw in REPAY_KEYWORDS):
            if any(k in context for k in ("绸", "绫", "丝", "布")):
                type_ = "sell_silk"
            else:
                logger.debug(
                    f"[events.parse] skip fake repay: context={context[:40]!r}"
                )
                continue

        # 🆕 v2.10.12+: 排除 "算账"/"归拢" 等名词性上下文当动词
        if any(neg in context for neg in REPAY_NEGATIVE_CTX) and verb_cn in ("还", "归"):
            continue

        events.append({
            "id": f"fin.{type_}",
            "amount": str(h["amount"]),
            "note": context[:20] + "...",
            "_fuzzy": True,
        })
    return events


def _infer_type_from_context(context: str) -> str:
    """根据上下文推断交易类型

    🆕 v2.10.12+ 重构：使用 explicit verb_evidence dict 取代单一字匹配。
    修复了"还了借款"被错归为 borrow 的 bug。
    """
    # 显式 verb evidence：每个动作的"证明词"，比纯字匹配更可靠
    VERB_EVIDENCE = (
        ("pay_tax", ("税", "赋", "差役", "秋粮", "朝廷")),
        ("repay",   ("还", "归", "清", "结清")),
        ("borrow",  ("借", "贷")),
        ("sell_silk", ("卖", "售")),
        ("buy_thread", ("买", "购", "买入")),
        ("gift_out", ("送", "给", "赠")),
        ("gift_in", ("礼", "赠")),
    )
    # 按 verb_evidence 顺序扫，第一个匹配的就 break
    for type_, kws in VERB_EVIDENCE:
        if any(kw in context for kw in kws):
            return type_
    # silk / 绸 二次判断（默认 sell）
    if any(kw in context for kw in ("绸", "绫", "丝", "帛")):
        return "sell_silk"
    return "sell_silk"  # 默认


def _verb_en_to_fin(verb_en: str, context: str) -> str:
    """从 verb_en ("sell"/"buy"/"repay"/"borrow"/...) 映射到 fin.* type

    🆕 v2.10.12+: 取代 _infer_type_from_context（不再看 narrative 文字）。
    映射：
      sell / 售 → sell_silk (默认)
      buy / 购 → buy_thread (默认)
      repay → repay
      borrow → borrow
      pay / 缴 → pay_tax
      gift_out → gift_out
      gift_in → gift_in
      lend / 借出 → lend_money (若不存在则回退到 borrow 负值)
    """
    MAPPING = {
        "sell":     "sell_silk",
        "buy":      "buy_thread",
        "repay":    "repay",
        "borrow":   "borrow",
        "pay":      "pay_tax",
        "gift_out": "gift_out",
        "gift_in":  "gift_in",
        "lend":     "borrow",  # v1.7.30 era 不支持 lend_money，借出 = 借出
    }
    base = MAPPING.get(verb_en, "sell_silk")
    # 🆕 v2.10.12+：sell 后如果有 "绫"/"丝"/"绸"/"帛" 不一定是 silk — 但默认是，按现有体系
    # 保留 sell_silk 当对象默认（era json 已经按绸缎经济设计）
    return base


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
