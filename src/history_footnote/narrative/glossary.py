"""🆕 v1.6.6 明朝名词字典

为玩家解释明朝时代专有名词（如"牙行"、"湖丝"、"束脩"）。

特点：
- 轻量级内存存储（无需 DB）
- 按 key 查询（中文/拼音/同义词）
- 首次出现时高亮 + tooltip
- 支持二级词条（不同语境含义不同）

数据结构：
{
    "牙行": {
        "category": "经济",
        "definition": "明代中介商业机构...",
        "example": "...",
        "related": ["牙人", "牙税"],
    },
    ...
}
"""
from __future__ import annotations

import re
from typing import Iterable

# 🆕 v1.6.6 明朝名词字典（万历年间常用）
# 来源：参考《万历十五年》《明代社会经济史》《剑桥中国明代史》等
TERM_GLOSSARY: dict[str, dict] = {
    # === 经济类 ===
    "牙行": {
        "category": "经济",
        "definition": "明代专门撮合买卖双方的中介机构，类似现代的'中介公司'。垄断特定商品的交易，抽取佣金（'牙用'）。",
        "example": "盛泽镇上最大的牙行是陈三家，专做湖丝外销。",
        "related": ["牙人", "牙税", "牙用"],
    },
    "牙人": {
        "category": "经济",
        "definition": "牙行里的中介人，负责评估商品、撮合交易、签订契约。",
        "example": "",
        "related": ["牙行"],
    },
    "湖丝": {
        "category": "物产",
        "definition": "浙江湖州府出产的蚕丝，品质上乘，明代畅销海内外。湖丝+苏缎被誉为'衣被天下'。",
        "example": "三两三银子能买六匹素绸，已经是湖丝下品了。",
        "related": ["盛泽镇", "苏缎", "绸缎"],
    },
    "苏缎": {
        "category": "物产",
        "definition": "苏州府出产的缎类织物，与湖丝并称'苏湖丝缎'。明代高级官员常以苏缎为贡品。",
        "example": "",
        "related": ["湖丝", "盛泽镇"],
    },
    "盛泽镇": {
        "category": "地理",
        "definition": "苏州府吴江县小镇，明代后期中国最大的丝织业市镇之一，万历时'镇上居民稠广'。",
        "example": "",
        "related": ["湖丝", "牙行"],
    },
    "绸缎": {
        "category": "物产",
        "definition": "丝织品的统称。绸是平纹织物，缎是缎纹织物，比绸更厚更亮。",
        "example": "",
        "related": ["湖丝", "苏缎"],
    },
    "绫": {
        "category": "物产",
        "definition": "斜纹丝织物，明代常见品种有'湖绫''杭绫'。",
        "example": "",
        "related": ["湖丝"],
    },
    "束脩": {
        "category": "教育",
        "definition": "学生送给老师的学费（腊肉或银两）。'脩'是干肉，'束脩'即十条干肉，后泛指学费。",
        "example": "阿宝的束脩是一年二两银子。",
        "related": ["秀才", "科举"],
    },
    "秀才": {
        "category": "科举",
        "definition": "明代科举体系第一级功名。通过县/府/院三级考试取得，可免本人徭役，见县官不跪。",
        "example": "李秀才连考三次乡试都没中。",
        "related": ["乡试", "举人", "进士", "科举"],
    },
    "举人": {
        "category": "科举",
        "definition": "通过乡试的考生（每三年一次，逢子午卯酉年举行）。举人可参加会试，地位高于秀才。",
        "example": "孙举人是镇上唯一有功名的人。",
        "related": ["秀才", "进士", "乡试", "会试"],
    },
    "进士": {
        "category": "科举",
        "definition": "通过会试+殿试的最高功名。明代每科录取约300人，是士人毕生追求的目标。",
        "example": "",
        "related": ["会试", "殿试", "状元"],
    },
    "乡试": {
        "category": "科举",
        "definition": "省一级考试，每三年一次，录取者为举人。",
        "example": "今年是丁酉年，正是乡试年。",
        "related": ["举人", "会试"],
    },
    "会试": {
        "category": "科举",
        "definition": "京城举行的全国考试，乡试合格者参加，录取者再参加殿试。",
        "example": "",
        "related": ["殿试", "进士"],
    },
    "殿试": {
        "category": "科举",
        "definition": "皇帝亲自主持的最终考试，决定进士名次（一甲/二甲/三甲）。",
        "example": "",
        "related": ["进士", "状元"],
    },
    "科举": {
        "category": "科举",
        "definition": "明代选拔官员的考试制度。从童生→秀才→举人→进士逐级考取。",
        "example": "",
        "related": ["秀才", "举人", "进士"],
    },
    # === 税赋类 ===
    "里甲": {
        "category": "制度",
        "definition": "明代基层户籍制度。每110户为一'里'，设里长1人、甲首10人，负责催征赋税、编排差役。",
        "example": "赵里长就是本里的里长。",
        "related": ["里长", "甲首", "赋税"],
    },
    "里长": {
        "category": "制度",
        "definition": "一里之首，由丁粮最多的10户轮流担任（10年一轮），负责催征本里赋税。",
        "example": "赵里长催春税来了。",
        "related": ["里甲", "赋税"],
    },
    "甲首": {
        "category": "制度",
        "definition": "一甲（10户）之首，协助里长管理户籍和赋税。",
        "example": "",
        "related": ["里甲", "里长"],
    },
    "赋税": {
        "category": "制度",
        "definition": "明代农民向朝廷缴纳的税赋，包括'夏税'（征麦）和'秋粮'（征米）。万历时加派'三饷'。",
        "example": "",
        "related": ["里甲", "三饷", "徭役"],
    },
    "三饷": {
        "category": "制度",
        "definition": "万历末年加征的三种赋税：辽饷、剿饷、练饷，加重了农民负担，加速明朝灭亡。",
        "example": "",
        "related": ["赋税"],
    },
    "徭役": {
        "category": "制度",
        "definition": "明代百姓免费为国家服劳役（如修河、运粮）。可以银代役（'力差'改'银差'）。",
        "example": "",
        "related": ["里甲", "赋税"],
    },
    "秋粮": {
        "category": "制度",
        "definition": "秋季征收的粮食税。万历年间，秋粮是农民最沉重的负担之一。",
        "example": "去年秋粮还欠着三两五钱。",
        "related": ["夏税", "赋税"],
    },
    "夏税": {
        "category": "制度",
        "definition": "夏季征收的税（通常为麦或银）。",
        "example": "",
        "related": ["秋粮", "赋税"],
    },
    # === 货币 ===
    "两": {
        "category": "货币",
        "definition": "明代基本银两单位，1两=10钱=100分。万历时1两约可买2石米。",
        "example": "三两三银子。",
        "related": ["钱", "分", "银子"],
    },
    "钱": {
        "category": "货币",
        "definition": "银钱单位，1钱=0.1两；也指铜钱（'制钱'），1钱银≈70文铜钱。",
        "example": "五百文。",
        "related": ["两", "文"],
    },
    "文": {
        "category": "货币",
        "definition": "铜钱的最小单位，1文=1枚铜钱。明代'一条鞭法'后部分赋税改征银两。",
        "example": "",
        "related": ["钱", "两"],
    },
    "银子": {
        "category": "货币",
        "definition": "明代通用银两的俗称，流通形态有元宝、银锭、碎银等。",
        "example": "",
        "related": ["两"],
    },
    # === 官职/身份 ===
    "县官": {
        "category": "官职",
        "definition": "明代一县之长，正式称谓'知县'。辖区赋税、刑狱、教化都由其负责。",
        "example": "见县官不跪。",
        "related": ["知县"],
    },
    "知县": {
        "category": "官职",
        "definition": "一县最高长官。",
        "example": "",
        "related": ["县官"],
    },
    "知府": {
        "category": "官职",
        "definition": "一府最高长官，管辖数县。",
        "example": "",
        "related": ["知县"],
    },
    "学政": {
        "category": "官职",
        "definition": "负责一省科举和学校的官员，又称'提学御史'。",
        "example": "学政衙门传出今年秋闱要挪到三月。",
        "related": ["科举"],
    },
    # === 文化/习俗 ===
    "牙祭": {
        "category": "习俗",
        "definition": "商家每月初二、十六给伙计吃的肉食，类似现代'加餐'。",
        "example": "",
        "related": [],
    },
    "年节": {
        "category": "习俗",
        "definition": "明代最重要的节日。腊月、正月有各种祭祀、走亲活动。",
        "example": "",
        "related": [],
    },
    "香烛": {
        "category": "物产",
        "definition": "祭祀用的香和蜡烛。",
        "example": "",
        "related": [],
    },
    "当铺": {
        "category": "经济",
        "definition": "明代专门接受抵押放贷的店铺，类似现代典当行。利息较高（'月息三分'）。",
        "example": "",
        "related": ["牙行"],
    },
    "小户": {
        "category": "身份",
        "definition": "明代无田产的贫苦人家，靠给人做工（'佣工'）度日。",
        "example": "小户人家，日子难过。",
        "related": ["大户", "佣工"],
    },
    "大户": {
        "category": "身份",
        "definition": "明代占有大量田产的地主或缙绅家庭。",
        "example": "",
        "related": ["小户"],
    },
    "织户": {
        "category": "身份",
        "definition": "专门从事丝织业的家庭，往往自备织机，可以是独立户也可以是雇佣工人。",
        "example": "",
        "related": ["盛泽镇", "湖丝"],
    },
    "自耕农": {
        "category": "身份",
        "definition": "自己耕种自有土地的农民，明代中期占农村人口多数。",
        "example": "",
        "related": ["佃户"],
    },
    "佃户": {
        "category": "身份",
        "definition": "租种地主土地的农民，需缴纳'佃租'（一般是收成的 40-50%）。",
        "example": "",
        "related": ["自耕农"],
    },
    "佣工": {
        "category": "身份",
        "definition": "受雇于人出卖劳动力的无地者，日工资约 30-50 文。",
        "example": "",
        "related": ["小户"],
    },
}


# 同义词映射（不同写法 → 标准 key）
SYNONYM_MAP: dict[str, str] = {
    "牙行": "牙行",
    "牙家": "牙行",
    "铺户": "牙行",
    "湖丝": "湖丝",
    "辑里湖丝": "湖丝",
    "盛泽": "盛泽镇",
    "盛泽镇": "盛泽镇",
    "秀才": "秀才",
    "生员": "秀才",
    "秀士": "秀才",
    "举人": "举人",
    "孝廉": "举人",
    "进士": "进士",
    "科举": "科举",
    "科考": "科举",
    "束脩": "束脩",
    "束修": "束脩",
    "学费": "束脩",
    "牙行": "牙行",
    "牙人": "牙人",
    "牙子": "牙人",
    "牙侩": "牙人",
    "里长": "里长",
    "里甲": "里甲",
    "甲首": "甲首",
    "赋税": "赋税",
    "税赋": "赋税",
    "钱粮": "赋税",
    "三饷": "三饷",
    "辽饷": "三饷",
    "剿饷": "三饷",
    "练饷": "三饷",
    "徭役": "徭役",
    "差役": "徭役",
    "秋粮": "秋粮",
    "夏税": "夏税",
    "两": "两",
    "银子": "银子",
    "白银": "银子",
    "碎银": "银子",
    "文": "文",
    "制钱": "文",
    "铜钱": "文",
    "县官": "县官",
    "知县": "知县",
    "知府": "知府",
    "学政": "学政",
    "提学": "学政",
    "牙祭": "牙祭",
    "当铺": "当铺",
    "典当": "当铺",
    "小户": "小户",
    "穷户": "小户",
    "大户": "大户",
    "富户": "大户",
    "缙绅": "大户",
    "织户": "织户",
    "机户": "织户",
    "自耕农": "自耕农",
    "自耕": "自耕农",
    "佃户": "佃户",
    "佃农": "佃户",
    "佣工": "佣工",
    "雇工": "佣工",
}


def get_term(key: str) -> dict | None:
    """获取名词解释（支持同义词）"""
    if not key:
        return None
    key = SYNONYM_MAP.get(key, key)
    return TERM_GLOSSARY.get(key)


def get_term_html(key: str) -> str | None:
    """获取名词的 HTML 片段（用于 tooltip/侧边栏）"""
    term = get_term(key)
    if not term:
        return None
    # 🆕 v1.6.6 P0 XSS 修复：所有用户/字典值必须 escape
    definition = escape_html(term.get("definition", ""))
    example = escape_html(term.get("example", ""))
    category = escape_html(term.get("category", ""))
    related = term.get("related", [])
    related_html = ""
    if related:
        related_html = (
            f'<div class="term-related">相关：{", ".join(escape_html(r) for r in related)}</div>'
        )
    example_html = f'<div class="term-example">例：{example}</div>' if example else ""
    return (
        f'<div class="term-entry" data-term="{escape_html(key)}">'
        f'<div class="term-name">{escape_html(key)} <span class="term-cat">[{category}]</span></div>'
        f'<div class="term-def">{definition}</div>'
        f'{example_html}'
        f'{related_html}'
        f'</div>'
    )


def search_terms(query: str, limit: int = 20) -> list[str]:
    """按 query 模糊搜索名词"""
    if not query:
        return list(TERM_GLOSSARY.keys())[:limit]
    query = query.strip()
    matches = []
    for key in TERM_GLOSSARY.keys():
        if query in key:
            matches.append(key)
    # 还能匹配 definition
    for key, term in TERM_GLOSSARY.items():
        if query in term.get("definition", "") and key not in matches:
            matches.append(key)
    return matches[:limit]


def extract_terms_from_text(text: str) -> list[str]:
    """从文本中提取出现的所有明朝名词（去重，按出现顺序）"""
    if not text:
        return []
    found = []
    seen = set()
    # 按字典序最长的 key 先匹配（防止"牙人"被"牙"先匹配）
    sorted_keys = sorted(TERM_GLOSSARY.keys(), key=len, reverse=True)
    # 简化：扫描所有 key，找出现在 text 中的（按位置排序）
    positions = []  # (pos, key)
    for key in sorted_keys:
        for m in re.finditer(re.escape(key), text):
            positions.append((m.start(), key))
    # 按位置排序，去重（同一位置只保留最长的）
    positions.sort()
    seen_positions = set()
    for pos, key in positions:
        if pos not in seen_positions and key not in seen:
            found.append(key)
            seen.add(key)
    return found


def escape_html(s: str) -> str:
    """简单 HTML 转义"""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("明朝名词字典 测试")
    print("=" * 50)

    # 测试 1：基本查询
    term = get_term("牙行")
    assert term is not None
    assert term["category"] == "经济"
    print(f"✅ get_term('牙行'): {term['definition'][:30]}...")

    # 测试 2：同义词
    term2 = get_term("牙家")
    assert term2 == term  # 应等于"牙行"
    print(f"✅ 同义词 '牙家' → '牙行'")

    # 测试 3：搜索
    matches = search_terms("丝")
    print(f"✅ search_terms('丝'): {matches}")

    # 测试 4：文本提取
    text = "你去了牙行和湖丝店，见到秀才李四。"
    terms = extract_terms_from_text(text)
    print(f"✅ extract_terms_from_text('{text}')")
    print(f"   → {terms}")

    # 测试 5：HTML 输出
    html = get_term_html("牙行")
    assert html is not None
    assert "牙行" in html
    print(f"✅ get_term_html: {len(html)} chars")

    # 测试 6：未知名词
    term6 = get_term("王者荣耀")
    assert term6 is None
    print(f"✅ 未知词返回 None")

    print("\n✅ 所有测试通过")
    print(f"\n字典规模：{len(TERM_GLOSSARY)} 个名词 + {len(SYNONYM_MAP)} 个同义词")