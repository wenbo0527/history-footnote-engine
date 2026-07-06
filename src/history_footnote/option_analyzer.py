"""🆕 v1.7.30 选项智能分析（option_analyzer）

分析玩家选项文本，预测会触发的 EventId 列表。
用于：
- UI 预览：玩家点击选项前显示"会触发什么事件"
- 决策辅助：DM 看到选项和可能事件，更准确生成 narrative
- 自动化：玩家自由输入时给出建议的选项
"""
from __future__ import annotations

import re
from typing import Optional


# 关键词 → EventId 映射（按优先级）
KEYWORD_TO_EVENTS = [
    # === 财务（fin.*）===
    (r"卖[了]?一?匹?|售出?|出售?", "fin.sell_silk", 0.8),
    (r"买[了]?一?匹?|买入|购入", "fin.buy_thread", 0.7),
    (r"缴[纳]?[了]?[税赋差役]+|交[纳]?税", "fin.pay_tax", 0.9),
    (r"借[了]?[了]?[一二三四五六七八九十两钱]+|借款|借贷", "fin.borrow", 0.7),
    (r"还[了]?[了]?[一二三四五六七八九十两钱]+|还款|归还", "fin.repay", 0.7),
    (r"送礼|赠予?|给.+送[钱礼银]+|给.+送[一二三四五六七八九十]+[两钱银]|打点|行贿|给[县官书吏里长]+送[钱礼]+|送[钱礼]+给[县官书吏里长]+", "fin.gift_out", 0.6),
    (r"收到[礼钱]?+|收了[一两钱]+", "fin.gift_in", 0.6),

    # === 城市（city.*）===
    (r"去?([一-龥]{2,3})[的]?码头|乘船|搭船|坐船", "city.arrive", 0.6),  # 城市名提取
    (r"回到盛泽|回乡|回家|返[回]?[盛泽]", "city.arrive.shengze", 0.8),
    (r"去苏州|赴苏州|入苏州|到苏州", "city.arrive.suzhou", 0.9),
    (r"去杭州|赴杭州|入杭州|到杭州", "city.arrive.hangzhou", 0.9),
    (r"去松江|赴松江|入松江|到松江", "city.arrive.songjiang", 0.9),
    (r"去南京|赴南京|入南京|到南京|进京", "city.arrive.nanjing", 0.9),

    # === 家人（fam.*）===
    (r"沈氏|妻子|娘子|老婆|内人", "fam.meet.fm_wife", 0.7),
    (r"老娘|母亲|娘亲|妈|母", "fam.meet.fm_mother", 0.7),
    (r"老父|父亲|爹|父", "fam.meet.fm_father", 0.7),
    (r"儿子|娃|孩子", "fam.meet.fm_son", 0.6),
    (r"女儿|闺女", "fam.meet.fm_daughter", 0.6),
    (r"兄弟|弟弟|哥哥", "fam.meet.fm_brother", 0.6),

    # === 物象（obj.*）===
    (r"珍珠|金镯|玉佩|传家宝", "obj.token_exposed", 0.7),
    (r"织机|梭子|经线|纬线", "obj.daily_grudge", 0.4),

    # === 商业陷阱（comm.*）===
    (r"牙行|经纪|卖[到]?牙行|给牙行", "comm.broker_lowball", 0.6),
    (r"合伙|合股|一起做", "comm.partnership_trap", 0.5),
    (r"借钱|借银|贷银|高利", "comm.usury", 0.6),

    # === 官府（gov.*）===
    (r"打官司|见官|起诉|告[状]?[到]?", "gov.false_case", 0.7),
    (r"行贿|送[钱礼]?给[县官书吏里长]+|打点", "gov.bribe_official", 0.7),
    (r"钞关|关卡|过关", "gov.customs", 0.7),

    # === 旅途（trv.*）===
    (r"拾[到]?[银钱]+|捡[到]?[银钱]+", "trv.find_money", 0.8),
    (r"遇到[盗贼土匪强盗]+|被劫|被抢", "trv.robbed", 0.9),

    # === 宗教（relig.*） ===
    (r"拜佛|上香|去寺庙|进香", "relig.temple_fair", 0.6),
    (r"算命|测字|占卜|解梦", "relig.omen", 0.6),

    # === 人际（reln.*） ===
    (r"茶馆[里]?坐[坐]?|找[个]?人[聊天]+|闲话", "reln.hanger_on", 0.4),
    (r"请客|设宴|饭局|喝酒", "reln.kindness_repaid", 0.5),

    # === 灾祸（dis.*） ===
    (r"发水|洪水|大水|暴雨|发大水", "dis.flood", 0.9),
    (r"起火|走水|失火|着火了", "dis.fire", 0.9),
    (r"瘟疫|时疫|传染|病死", "dis.plague", 0.7),

    # === 发现（discover.*） ===
    # 注意：discover.* 是不确定事件，关键词不直接映射但可提示
]


def analyze_option(option_text: str) -> list[dict]:
    """分析单个选项文本，返回预测事件列表

    Returns:
        [{"event_id": str, "confidence": float, "keyword": str, "extracted": dict}, ...]
        按 confidence 倒序
    """
    if not option_text:
        return []
    results = []
    seen = set()  # 去重
    for pattern, event_id, confidence in KEYWORD_TO_EVENTS:
        m = re.search(pattern, option_text)
        if not m:
            continue
        # 提取 city
        extracted = {}
        if event_id == "city.arrive" and m.group(1):
            # 尝试从提取的中文解析 city
            city = _cn_to_city(m.group(1))
            if city:
                event_id = f"city.arrive.{city}"
                extracted["city"] = city
            else:
                continue  # 解析不出 city 跳过
        if event_id in seen:
            continue
        seen.add(event_id)
        results.append({
            "event_id": event_id,
            "confidence": confidence,
            "keyword": m.group(0),
            "extracted": extracted,
        })
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def _cn_to_city(text: str) -> str | None:
    """中文地名 → city_id"""
    mapping = {
        "苏州": "suzhou",
        "杭州": "hangzhou",
        "松江": "songjiang",
        "南京": "nanjing",
        "应天": "nanjing",
        "盛泽": "shengze",
    }
    return mapping.get(text)


def analyze_options_batch(options: list[str]) -> list[list[dict]]:
    """批量分析多个选项"""
    return [analyze_option(opt) for opt in options]


def get_event_summary_text(event_id: str) -> str:
    """事件 ID → 玩家易读描述（用于 UI 预览）"""
    mapping = {
        "fin.sell_silk": "💰 卖绸得银",
        "fin.buy_thread": "🛒 买丝",
        "fin.pay_tax": "💸 缴税",
        "fin.borrow": "🏦 借钱",
        "fin.repay": "🏦 还钱",
        "fin.gift_in": "🎁 收到礼金",
        "fin.gift_out": "🎁 送礼",
        "city.arrive.shengze": "📍 回到盛泽",
        "city.arrive.suzhou": "📍 到达苏州",
        "city.arrive.hangzhou": "📍 到达杭州",
        "city.arrive.songjiang": "📍 到达松江",
        "city.arrive.nanjing": "📍 到达南京",
        "fam.meet.fm_wife": "👩 见到妻子",
        "fam.meet.fm_mother": "👩 见到母亲",
        "fam.meet.fm_father": "👨 见到父亲",
        "obj.token_exposed": "💎 物象触发",
        "comm.broker_lowball": "🤝 牙行压价",
        "comm.partnership_trap": "🤝 合伙生意",
        "comm.usury": "💳 高利贷",
        "gov.false_case": "⚖️ 官司缠身",
        "gov.bribe_official": "🎁 行贿",
        "gov.customs": "🛃 钞关抽税",
        "trv.find_money": "🍀 拾遗",
        "trv.robbed": "⚠️ 遇盗贼",
        "relig.temple_fair": "🏯 庙会",
        "relig.omen": "🔮 占卜",
        "reln.hanger_on": "💬 帮闲",
        "reln.kindness_repaid": "🍚 施恩",
        "dis.flood": "🌊 水灾",
        "dis.fire": "🔥 火灾",
        "dis.plague": "🦠 瘟疫",
    }
    return mapping.get(event_id, f"❓ {event_id}")


if __name__ == "__main__":
    # 烟雾测试
    samples = [
        "我去镇上牙行卖这匹湖绫",
        "我搭船去苏州",
        "我给县官送三两银子",
        "我借邻居老王五两银子",
        "我回家告诉沈氏这事",
        "我算算账",
    ]
    for s in samples:
        results = analyze_option(s)
        print(f"📋 '{s}'")
        for r in results[:3]:
            text = get_event_summary_text(r["event_id"])
            print(f"  {r['confidence']:.0%} {text} ({r['event_id']}) [{r['keyword']}]")
        print()
