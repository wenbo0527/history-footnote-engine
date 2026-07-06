"""🆕 v1.7.32 玩家输入解析器 + ActionResolver

核心思路：游戏引擎驱动状态变化，LLM 只生成 narrative 文案。

数据流：
1. parse_player_input(text) → PlayerAction {verb, object, amount, target, modifiers}
2. resolve_action(state, action, config) → {state_changes, events, narrative_hints}
3. game_loop 调 LLM 把 narrative_hints 包装成"故事"
4. LLM 不再输出 events（不依赖）

PlayerAction 类型：
- SELL: 卖（object=物品, amount=数量, target=买家）
- BUY: 买
- GIVE: 给
- BORROW: 借
- REPAY: 还
- TRAVEL: 去某地
- MEET: 见某人
- IDLE: 闲聊/观察
- UNKNOWN: 引擎无法判定（fallback 给 LLM）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# ============= 玩家动作 =============

@dataclass
class PlayerAction:
    """玩家动作的结构化表示"""
    raw_text: str
    verb: str = "UNKNOWN"  # SELL/BUY/GIVE/BORROW/REPAY/TRAVEL/MEET/IDLE/UNKNOWN
    object: str = ""  # 物品/对象（湖绫/银子/织机）
    amount: float = 0.0  # 数量/银两
    target: str = ""  # 目标（买家/人物/地点）
    location: str = ""  # 地点（盛泽/苏州/家里）
    modifiers: dict = field(default_factory=dict)  # 其他修饰（"用织机"等）
    confidence: float = 0.0  # 解析 confidence 0-1
    hint: str = ""  # 给 LLM 的叙事提示


# ============= 解析规则（关键词 + 正则）============

# 动词正则（不要求 ^ 开头——通常有"我"前缀）
VERB_PATTERNS = [
    # 卖
    (r"卖[了]?[一]?[匹件]?|出售[了]?|售出[了]?|把.+卖[了]|卖得|卖给|售给", "SELL", 0.9),
    # 买
    (r"买[了]?[一]?[匹件斗担]?|购入|买入|置办[米粮]?", "BUY", 0.9),
    # 给/送/赠
    (r"送[了一]?[一]?[封信个匹]?|赠[一]?[一]?[封信个]?|给.+送[钱礼]|打点|行贿", "GIVE", 0.85),
    # 借
    (r"借[了]?[一两钱银]?|借款|贷银|高利", "BORROW", 0.9),
    # 还
    (r"还[了]?[一两钱银]?|归还|还款", "REPAY", 0.9),
    # 去/赴
    (r"去[了]?苏州|赴|到[了]?苏州|入[了]?|回[到家乡]|返|搭船去|坐船去|乘船去|回盛泽|回家", "TRAVEL", 0.85),
    # 见/访/找
    (r"见[到]?了?|访[问了]?|找[到]?了?|遇见|碰见", "MEET", 0.85),
    # 闲聊/观察
    (r"看[一]?[看]?|看窗外|观察|听[一]?[听]?|问[一问]?问|聊[一]?聊|打听|算[一]?[算]?|回忆|想[一]?[想]?|歇[息]?|休息", "IDLE", 0.7),
    # 织/做
    (r"织[了一]?[匹]?|编[了]?|缝[了]?|绣[了]?|做[了]?[一件]?|造[了]?", "CRAFT", 0.85),
    # 缴/交
    (r"缴[纳]?[了]?[税赋差役]?|交[纳]?税", "PAY", 0.9),
]

# 物品正则（中文 + 银两）
OBJECT_PATTERNS = [
    (r"[一二三四五六七八九十]?匹?[湖]?绫[丝]?|绸缎|丝绸|绢", "silk_bolt"),
    (r"[一]?[件]?衣裳|长衫|短褂|衣服", "clothing"),
    (r"玉[佩器镯]?", "jewelry"),
    (r"织机|梭子", "loom"),
    (r"米[粮]?[饭]?|[一]?[担斗]?米", "rice"),
    (r"银[子两]|钱|白银|铜钱", "silver"),
    (r"信|家书|书信", "letter"),
    (r"酒|黄酒|米酒", "alcohol"),
    (r"盐|油|茶|糖", "groceries"),
    (r"肉|鱼|鸡|鸭", "food"),
    (r"桑叶", "mulberry_leaves"),
    (r"经线|纬线|丝", "thread"),
]

# 城市正则
CITY_PATTERNS = [
    (r"苏州|阊门|虎丘", "suzhou"),
    (r"杭州|西湖|清河坊", "hangzhou"),
    (r"松江|枫桥|上海县", "songjiang"),
    (r"南京|应天|京城", "nanjing"),
    (r"盛泽", "shengze"),
]

# 人物正则（家人 + 常见 NPC）
PERSON_PATTERNS = [
    (r"沈氏|妻子|娘子|老婆|内人", "fm_wife"),
    (r"老娘|母亲|娘亲|妈|母", "fm_mother"),
    (r"老父|父亲|爹|父|阿爹", "fm_father"),
    (r"儿子|小儿|犬子|娃", "fm_son"),
    (r"女儿|闺女|小女", "fm_daughter"),
    (r"兄长|大哥|阿哥|哥|弟", "fm_brother"),
    (r"牙行|经纪|掌柜", "npc_broker"),
    (r"里长|甲首|老人", "npc_lijia"),
    (r"县官|知县|县太爷", "npc_county"),
    (r"书吏|皂隶|衙役", "npc_clerk"),
    (r"和尚|尼姑|道士", "npc_religious"),
    (r"邻居|邻家|隔壁", "npc_neighbor"),
]

# 金额正则（阿拉伯 + 中文 + 简单）
AMOUNT_RE = re.compile(
    r"([一二三四五六七八九十百千万半]+|[0-9]+(?:\.[0-9]+)?)\s*(两|钱|分|厘|石|担|斗|匹|件|个)?"
)

CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "半": 0.5, "百": 100, "千": 1000, "万": 10000,
}

UNIT_TO_LIANG = {
    "两": 1.0,
    "钱": 0.1,  # 1 钱 = 0.1 两
    "分": 0.01,
    "厘": 0.001,
}


def _parse_amount(s: str) -> float | None:
    """解析金额字符串"""
    if not s:
        return None
    s = s.strip()
    # 阿拉伯数字
    try:
        return float(s)
    except ValueError:
        pass
    # 中文数字
    if s in CN_DIGITS:
        return float(CN_DIGITS[s])
    # 复合：十五/二十/一百
    total = 0
    last = 0
    for ch in s:
        if ch not in CN_DIGITS:
            continue
        v = CN_DIGITS[ch]
        if v >= 10:
            if last == 0:
                last = 1
            total += last * v
            last = 0
        else:
            last = v
    total += last
    return float(total) if total else None


def _parse_amount_full(text: str) -> tuple[float, str]:
    """从文本提取金额（数字 + 单位）"""
    m = re.search(r"([0-9一二三四五六七八九十百千万半]+(?:\.[0-9]+)?)\s*(两|钱|分|厘|石|担|斗|匹|件|个)?", text)
    if not m:
        return 0.0, ""
    num_str = m.group(1)
    unit = m.group(2) or ""
    amount = _parse_amount(num_str) or 0.0
    # 单位换算（两/钱/分/厘 → 两）
    if unit in UNIT_TO_LIANG:
        amount *= UNIT_TO_LIANG[unit]
    return amount, unit


# ============= 主解析函数 =============

def parse_player_input(text: str) -> PlayerAction:
    """解析玩家输入文本 → PlayerAction 结构化表示

    Examples:
        "我织了一匹湖绫" → SELL? 不, CRAFT, object=silk_bolt, amount=1
        "我卖了湖绫得七钱" → SELL, object=silk_bolt, amount=0.7
        "我搭船去苏州" → TRAVEL, target=suzhou
        "我给沈氏送了一封信" → GIVE, object=letter, target=fm_wife
        "我借邻居老王五两银子" → BORROW, amount=5.0, target=npc_neighbor
        "我回家告诉沈氏这事" → TRAVEL, target=shengze
        "我看窗外" → IDLE
    """
    if not text:
        return PlayerAction(raw_text="", verb="UNKNOWN")
    text = text.strip()

    action = PlayerAction(raw_text=text)

    # 1. 识别 verb（用 "回..." + 家人时优先 MEET）
    for pattern, verb, conf in VERB_PATTERNS:
        if re.search(pattern, text):
            action.verb = verb
            action.confidence = conf
            break

    # 2. 识别 object
    for pattern, obj in OBJECT_PATTERNS:
        m = re.search(pattern, text)
        if m:
            action.object = obj
            break

    # 3. 识别 target（先人物再城市）
    for pattern, person in PERSON_PATTERNS:
        if re.search(pattern, text):
            action.target = person
            break
    if not action.target:
        for pattern, city in CITY_PATTERNS:
            if re.search(pattern, text):
                action.target = city
                if action.verb == "TRAVEL" or "去" in text or "回" in text or "到" in text:
                    action.target = city
                    action.location = city
                break

    # 4. 优先：TRAVEL + 家人 → MEET
    if action.verb == "TRAVEL" and action.target.startswith("fm_"):
        action.verb = "MEET"

    # 4. 识别 amount
    amount, unit = _parse_amount_full(text)
    if amount > 0:
        action.amount = amount
        if unit:
            action.modifiers["unit"] = unit

    # 5. 给 LLM 的提示（叙事素材）
    action.hint = _build_narrative_hint(action)

    return action


def _build_narrative_hint(action: PlayerAction) -> str:
    """根据 PlayerAction 构造给 LLM 的叙事提示"""
    parts = []
    if action.verb != "UNKNOWN":
        verb_desc = {
            "SELL": "把物品卖掉换取银两",
            "BUY": "购买物品或材料",
            "GIVE": "把物品或银两送给别人",
            "BORROW": "向别人借钱",
            "REPAY": "归还借款",
            "TRAVEL": "前往某地或回家",
            "MEET": "拜访或遇见某人",
            "IDLE": "闲聊、观察、问询",
            "CRAFT": "手工制作（织布/缝衣/烹饪）",
            "PAY": "缴纳税款或摊派",
        }.get(action.verb, action.verb)
        parts.append(f"动作：{verb_desc}")
    if action.object:
        parts.append(f"对象：{action.object}")
    if action.amount > 0:
        parts.append(f"数量/银两：{action.amount}")
    if action.target:
        parts.append(f"目标：{action.target}")
    if action.location:
        parts.append(f"地点：{action.location}")
    if not parts:
        return "玩家输入了模糊动作，需要 LLM 自由发挥"
    return "（" + "，".join(parts) + "）"


# ============= ActionResolver：PlayerAction → 状态变化 + 事件 =============

@dataclass
class ActionResult:
    """ActionResolver 输出：状态变化 + 事件列表 + 叙事提示"""
    state_changes: dict  # {cash_delta, debt_delta, rice_delta, current_city, ...}
    events: list  # list[EventId dict]，如 [{"id": "fin.sell_silk", "amount": 0.7, ...}]
    success: bool  # 是否能执行（如没钱买、借太多等）
    error_msg: str = ""  # 失败原因
    narrative_hints: list = field(default_factory=list)  # 给 LLM 的额外提示


# 价格表（基于经济/官僚文档）
PRICES = {
    "silk_bolt": 0.7,  # 一匹湖绫 0.7 两
    "thread": 0.05,  # 一两丝
    "rice_per_dan": 0.1,  # 一担米 0.1 两
    "loom": 4.0,  # 一张织机 4 两
    "mulberry_leaves_per_dan": 0.05,  # 正常 0.05，缺叶 0.3
}


def _get_price(config: dict | None, object_id: str, default: float = 0.5) -> float:
    """🆕 v1.7.33 从 era_config 读价格

    era.json world.economy.price_anchor 节点：
    {
      "silk_bolt": 0.5-0.8,  # 或具体值
      "rice_per_dan": 0.5-0.8,  # 范围
      "thread": ...
    }
    """
    if not config:
        return default
    price_anchor = (
        config.get("world", {}).get("economy", {}).get("price_anchor", {})
    )
    # 优先：完全匹配
    if object_id in price_anchor:
        val = price_anchor[object_id]
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str) and "-" in val:
            # 范围 "0.5-0.8" → 取中位
            try:
                parts = val.split("-")
                return (float(parts[0]) + float(parts[1])) / 2
            except (ValueError, IndexError):
                pass
    # 次选：相同样式
    if "silk_bolt" in price_anchor and "绫" in str(object_id) or "绸" in str(object_id):
        return _get_price(config, "silk_bolt", default=default)
    return default


def resolve_action(state, action: PlayerAction, config: dict = None) -> ActionResult:
    """把 PlayerAction 转成状态变化 + 事件

    Args:
        state: GameState 实例
        action: PlayerAction 实例
        config: era 配置（可选，影响价格/规则）

    Returns:
        ActionResult
    """
    result = ActionResult(
        state_changes={},
        events=[],
        success=True,
    )

    if action.verb == "UNKNOWN":
        result.success = False
        result.error_msg = "无法判定动作，请 LLM 自由发挥"
        return result

    # 优先：MEET 覆盖 TRAVEL（玩家"回家告诉沈氏"应是 MEET fm_wife）
    if action.verb == "TRAVEL" and action.target.startswith("fm_"):
        action.verb = "MEET"

    # 🆕 v1.7.34 LLM Layer 2 fallback（已停用，需 config）
    # 如果 LLM 传入，可在外部解析后调用 resolve_action，再次走总线

    if action.verb == "SELL":
        # 卖：cash + amount（amount 是银两）
        # 🆕 v1.7.33 从 era_config 读价格（缺省用 PRICES）
        price = _get_price(config, action.object, default=PRICES.get(action.object, 0.5))
        amount = action.amount if action.amount > 0 else price
        result.state_changes["cash_delta"] = amount
        result.events.append({
            "id": "fin.sell_silk",
            "amount": amount,
            "note": f"卖{action.object}得银 {amount} 两",
            "location": state.current_city if hasattr(state, "current_city") else "shengze",
        })
        # 同时 discover.item（如卖绸记录）
        if action.object == "silk_bolt":
            result.events.append({
                "id": "discover.item",
                "name": "湖绫",
                "type": "silk_bolt",
                "owner": state.current_city if hasattr(state, "current_city") else "shengze",
                "description": f"卖出的湖绫一匹（{amount} 两）",
            })

    elif action.verb == "BUY":
        # 买：cash - amount
        amount = action.amount if action.amount > 0 else 0.1
        if state.cash < amount:
            result.success = False
            result.error_msg = f"现金不足（需 {amount} 两，现有 {state.cash} 两）"
            return result
        result.state_changes["cash_delta"] = -amount
        result.events.append({
            "id": "fin.buy_thread",
            "amount": amount,
            "note": f"买{action.object}花费 {amount} 两",
        })

    elif action.verb == "GIVE":
        # 给：cash - amount
        amount = action.amount if action.amount > 0 else 0.5
        result.state_changes["cash_delta"] = -amount
        result.events.append({
            "id": "fin.gift_out",
            "amount": amount,
            "note": f"送{action.target}银 {amount} 两",
        })

    elif action.verb == "BORROW":
        # 借：cash + amount, debt + amount
        amount = action.amount if action.amount > 0 else 1.0
        result.state_changes["cash_delta"] = amount
        result.state_changes["debt_delta"] = amount
        result.events.append({
            "id": "fin.borrow",
            "amount": amount,
            "note": f"借{action.target}银 {amount} 两",
        })

    elif action.verb == "REPAY":
        # 还：cash - amount, debt - amount
        amount = action.amount if action.amount > 0 else 1.0
        if state.cash < amount:
            result.success = False
            result.error_msg = f"现金不足还款（需 {amount} 两）"
            return result
        result.state_changes["cash_delta"] = -amount
        result.state_changes["debt_delta"] = -amount
        result.events.append({
            "id": "fin.repay",
            "amount": amount,
            "note": f"还款 {amount} 两",
        })

    elif action.verb == "TRAVEL":
        # 旅行：current_city → target
        if action.target in ("suzhou", "hangzhou", "songjiang", "nanjing", "shengze"):
            result.state_changes["current_city"] = action.target
            result.events.append({
                "id": f"city.arrive.{action.target}",
                "note": f"到达 {action.target}",
            })

    elif action.verb == "MEET":
        # 见人：discover.person
        if action.target.startswith("fm_") or action.target.startswith("npc_"):
            person_name = action.target.replace("fm_", "").replace("npc_", "")
            person_label = {
                "wife": "沈氏", "mother": "母亲", "father": "父亲", "son": "儿子", "daughter": "女儿",
                "broker": "牙行经纪", "lijia": "里长", "county": "县官",
                "clerk": "书吏", "religious": "和尚", "neighbor": "邻居",
            }.get(person_name, person_name)
            result.events.append({
                "id": f"discover.person",
                "name": person_label,
                "role": action.target,
                "city": state.current_city if hasattr(state, "current_city") else "shengze",
                "description": f"玩家主动拜访/遇见",
            })
            if action.target.startswith("fm_"):
                result.events.append({
                    "id": f"fam.meet.{action.target}",
                    "note": f"见到 {person_label}",
                })

    elif action.verb == "CRAFT":
        # 织布：discover.item + 等待卖
        if action.object == "silk_bolt" or "绫" in str(action.object) or "绸" in str(action.object):
            result.events.append({
                "id": "discover.item",
                "name": "湖绫",
                "type": "silk_bolt",
                "owner": state.current_city if hasattr(state, "current_city") else "shengze",
                "qty": 1,
                "description": "刚织成的湖绫一匹（待售）",
            })
            result.narrative_hints.append("织布完成，可卖 0.7 两")

    elif action.verb == "PAY":
        # 缴税：cash - amount
        amount = action.amount if action.amount > 0 else 0.3
        if state.cash < amount:
            result.success = False
            result.error_msg = f"现金不足缴税（需 {amount} 两）"
            return result
        result.state_changes["cash_delta"] = -amount
        result.events.append({
            "id": "fin.pay_tax",
            "amount": amount,
            "note": f"缴税 {amount} 两",
            "location": state.current_city if hasattr(state, "current_city") else "shengze",
        })

    elif action.verb == "IDLE":
        # 闲聊/观察：不改变状态
        result.narrative_hints.append("玩家闲聊/观察，不消耗行动点")

    return result


def apply_action_result(state, result: ActionResult):
    """把 ActionResult 应用到 GameState（应用 state_changes + events）

    🆕 v1.7.33 修复：fin.* 事件通过 apply_event() 内部调 apply_financial_change()
    改 cash——所以我们这里不再单独改 cash_delta（避免双重计算）。
    唯一直接改的 state_changes：current_city（city.* 事件也通过 apply_event 但保险起见）
    """
    if not result.success:
        return
    # 应用 events（fin.* 内部会改 cash/debt/rice）
    for ev in result.events:
        from history_footnote.event_parser import apply_event
        apply_event(state, ev)
    # current_city 是 city.* 事件产物（apply_event 也会改），这里保险起见再 set 一次
    if "current_city" in result.state_changes:
        state.current_city = result.state_changes["current_city"]


# ============= 烟雾测试 =============

if __name__ == "__main__":
    samples = [
        "我织了一匹湖绫，丝光莹润。",
        "我去镇上牙行卖这匹湖绫。",
        "我搭船去苏州。",
        "我给沈氏送了一封信。",
        "我借邻居老王五两银子。",
        "我回家告诉沈氏这事。",
        "我看窗外。",
        "我买三斗米。",
        "我算了算账。",
        "我缴纳了税款三钱。",
        "我算算家里的账，发现这个月支出很大。",
    ]
    for s in samples:
        a = parse_player_input(s)
        print(f"📋 '{s}'")
        print(f"  verb={a.verb} ({a.confidence:.0%}), object={a.object}, amount={a.amount}, target={a.target}, location={a.location}")
        print(f"  hint: {a.hint}")
        print()
