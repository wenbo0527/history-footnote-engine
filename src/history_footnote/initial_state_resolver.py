"""🆕 v1.9.5 初始状态解析器

解决问题：
- LLM 在 custom_character 里生成了"手头现银一两二钱 / 欠牙行三两 / 母亲张氏"等信息
- 但 state.cash / state.debt / state.family_members 等是 dataclass 默认 0/[]
- 结果：右侧 sidebar 全部显示 0，玩家看 narrative 文本看到"我有一两二钱"但 sidebar 显示 0

本模块提供：
- extract_initial_state_from_character(cc, identity_config) -> dict
  把 LLM 生成的 custom_character 解析为结构化 initial_state
  解析失败时用 identity_config.base_state 兜底
- apply_initial_state(state, initial_state)
  把解析结果写入 GameState
- parse_chinese_number(s) -> float
  中文数字 → float（"一两二钱" → 1.2, "三两" → 3.0, "八钱" → 0.8）
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# 中文数字映射（简化版，覆盖 0-99）
_CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
    "七": 7, "八": 8, "九": 9, "十": 10, "百": 100, "千": 1000, "两": 2,
}


def parse_chinese_number(s: str) -> float | None:
    """中文数字 → float

    支持的格式：
    - "1.2" / "3" / "0.42"      → 直接返回
    - "一两二钱"                  → 1.2  (1两 + 2钱 = 1.2两)
    - "三两"                      → 3.0
    - "四钱二分"                  → 0.42 (4钱 + 2分 = 0.42两)
    - "八钱"                      → 0.8
    - "半两"                      → 0.5
    """
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    # 1) 纯阿拉伯数字
    try:
        return float(s)
    except ValueError:
        pass
    # 2) 用一个"按单位出现一次"的稳健方式：
    #    每个单位只解析**一次**——从原字符串里 find 第一次出现的位置
    total = 0.0
    matched = False
    s_remaining = s
    # 两（整数）
    m = re.search(r"([零一二三四五六七八九十百千半\d]+)两", s_remaining)
    if m:
        v = _parse_cn_int(m.group(1))
        if v is not None:
            total += v
            matched = True
            s_remaining = s_remaining.replace(m.group(0), "", 1)
    # 钱
    m = re.search(r"([零一二三四五六七八九十百千半\d]+)钱", s_remaining)
    if m:
        v = _parse_cn_int(m.group(1))
        if v is not None:
            total += v / 10.0
            matched = True
            s_remaining = s_remaining.replace(m.group(0), "", 1)
    # 分
    m = re.search(r"([零一二三四五六七八九十百千半\d]+)分", s_remaining)
    if m:
        v = _parse_cn_int(m.group(1))
        if v is not None:
            total += v / 100.0
            matched = True
            s_remaining = s_remaining.replace(m.group(0), "", 1)
    return total if matched else None


def _parse_cn_int(s: str) -> float | None:
    """解析中文整数（含'十/百/千'位）"""
    if not s:
        return None
    # 阿拉伯数字
    try:
        return float(s)
    except ValueError:
        pass
    if s == "半":
        return 0.5
    if s in _CN_DIGITS:
        return float(_CN_DIGITS[s])
    # 简单合成：例如"十二"="十"+"二"=10+2
    if "十" in s:
        parts = s.split("十")
        left, right = parts[0], parts[1] if len(parts) > 1 else ""
        tens = _CN_DIGITS.get(left, 1) if left else 1  # "十"=10, "二十"=20
        ones = _CN_DIGITS.get(right, 0) if right else 0
        return float(tens * 10 + ones)
    if "百" in s:
        parts = s.split("百")
        left, right = parts[0], parts[1] if len(parts) > 1 else ""
        hundreds = _CN_DIGITS.get(left, 1) if left else 1
        rest = _parse_cn_int(right) if right else 0
        return float(hundreds * 100 + (rest or 0))
    return None


def _try_float(v: Any) -> float | None:
    """统一 float 转换：优先数字，其次中文"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return parse_chinese_number(s)
    return None


def _extract_cash_from_text(text: str) -> float | None:
    """从 narrative 文本里正则提取现金数额

    模式：手头现银 X / 现有现银 X / 身上有 X 两 / 现银 X 两
    """
    if not text:
        return None
    # 模式 1: "现银 X" / "手头现银 X"
    for pat in [
        r"手头现银\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
        r"现有?\s*现银\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
        r"现银\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
        r"手头\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
        r"身上有?\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
        r"现金\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
    ]:
        m = re.search(pat, text)
        if m:
            v = parse_chinese_number(m.group(1))
            if v is not None and 0 < v < 10000:  # 合理范围
                return v
    return None


def _extract_debt_from_text(text: str) -> float | None:
    """从 narrative 文本里正则提取欠债数额

    模式：欠 X 两 / 欠牙行 X 两 / 还欠 X 两 / 旧账 X 两
    """
    if not text:
        return None
    for pat in [
        r"欠[^，。\n]{0,12}?([零一二三四五六七八九十百千半\d.]+)\s*两",
        r"旧账\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
        r"借了\s*([零一二三四五六七八九十百千半\d.]+)\s*两",
    ]:
        m = re.search(pat, text)
        if m:
            v = parse_chinese_number(m.group(1))
            if v is not None and 0 < v < 10000:
                return v
    return None


def _extract_rice_from_text(text: str) -> float | None:
    """从 narrative 文本里正则提取存粮（米几日 / X 石 / X 斗）"""
    if not text:
        return None
    # "米缸还够 X 日"
    m = re.search(r"米[缸粮]?[够剩有]?\s*([零一二三四五六七八九十百千半\d.]+)\s*日", text)
    if m:
        v = _try_float(m.group(1))
        if v is not None:
            return v / 30.0  # 转成石
    # "存粮 X 石"
    m = re.search(r"存粮\s*([零一二三四五六七八九十百千半\d.]+)\s*石", text)
    if m:
        v = _try_float(m.group(1))
        if v is not None:
            return v
    return None


def _extract_monthly_burn_from_text(text: str) -> float | None:
    """从 narrative 文本里正则提取月耗"""
    if not text:
        return None
    # "春税折银（合 X 钱 X 分）"
    m = re.search(r"(?:春税|夏税|秋税|冬税|税银|折银|税)[^，。\n]{0,8}?合?\s*([零一二三四五六七八九十百千半\d.]+)\s*钱\s*([零一二三四五六七八九十百千半\d.]*)\s*分?", text)
    if m:
        q = _try_float(m.group(1)) or 0
        f = _try_float(m.group(2)) or 0
        total = q / 10.0 + f / 100.0
        if total > 0:
            return total
    return None


def _extract_family_from_cc(cc: dict) -> list[dict]:
    """从 cc.family 解析出 family_members 列表

    cc.family 形态多样：
    - {"mother": "张氏（58岁）", "wife": "张氏（26岁）", "son": "大毛（5岁）"}
    - {"spouse": "沈氏", "children": ["阿宝（8岁）", "小妹（4岁）"]}
    """
    raw = cc.get("family")
    if not raw or not isinstance(raw, dict):
        return []
    members: list[dict] = []
    # 常见 key 映射
    relation_map = {
        "spouse": ("妻子", "wife"),
        "husband": ("丈夫", "husband"),
        "wife": ("妻子", "wife"),
        "mother": ("母亲", "mother"),
        "father": ("父亲", "father"),
        "mother_in_law": ("婆婆", "mother_in_law"),
        "father_in_law": ("公公", "father_in_law"),
        "son": ("儿子", "son"),
        "daughter": ("女儿", "daughter"),
        "children": ("子女", "child"),
        "elderly": ("老人", "elder"),
        "parents": ("父母", "parent"),
        "siblings": ("兄弟姐妹", "sibling"),
    }
    for k, v in raw.items():
        if v is None:
            continue
        rel_label, rel_id = relation_map.get(k, (k, k))
        # 数组（children 多个）
        if isinstance(v, list):
            for idx, item in enumerate(v):
                name, age = _parse_name_age(str(item))
                members.append({
                    "id": f"fm_{rel_id}_{idx+1}",
                    "name": name,
                    "relation": rel_id,
                    "age": age,
                    "location": "shengze",
                    "alive": True,
                    "notes": f"由custom_character解析: {item}",
                })
        elif isinstance(v, str):
            name, age = _parse_name_age(v)
            members.append({
                "id": f"fm_{rel_id}",
                "name": name,
                "relation": rel_id,
                "age": age,
                "location": "shengze",
                "alive": True,
                "notes": f"由custom_character解析",
            })
    return members


def _parse_name_age(s: str) -> tuple[str, int | None]:
    """从 '张氏（58岁）' / '阿宝（8岁）' 提取姓名和年龄"""
    if not s:
        return ("?", None)
    m = re.search(r"^(.+?)[（(](\d+)\s*岁[）)]", s)
    if m:
        return (m.group(1).strip(), int(m.group(2)))
    m = re.search(r"^(.+?)\s*(\d+)\s*岁", s)
    if m:
        return (m.group(1).strip(), int(m.group(2)))
    return (s.strip(), None)


def _extract_genealogy_from_cc(cc: dict) -> list[dict]:
    """从 cc 中尝试提取谱系信息（祖上三代）

    cc 字段没有显式 genealogy，从 background 文本里尝试解析
    """
    bg = cc.get("background", "")
    if not bg:
        return []
    genealogy: list[dict] = []
    # "祖父" / "祖母"
    m = re.search(r"祖[父母]", bg)
    if m:
        genealogy.append({
            "id": "ge_grandparent",
            "name": "沈老太爷",
            "relation": "grandfather",
            "alive": False,
            "location": "shengze",
            "generation": -2,
            "is_known_to_player": True,
            "notes": "由 custom_character.background 推断",
        })
    return genealogy


def _extract_active_tasks_from_text(text: str) -> list[dict]:
    """从 starting_situation 文本里提取主动任务（"必须" / "马上要" / "下月也该"）"""
    if not text:
        return []
    tasks: list[dict] = []
    # 找"马上要 / 必须 / 下月也该 / 该续"等关键短语
    sentences = re.split(r"[。\n；]", text)
    for idx, s in enumerate(sentences):
        s = s.strip()
        if not s:
            continue
        if any(kw in s for kw in ["马上要交", "必须", "下月也该续", "该续", "月底要", "得还", "得交"]):
            title = s[:30] + ("…" if len(s) > 30 else "")
            urgency = "high" if "马上" in s or "必须" in s else "normal"
            tasks.append({
                "title": title,
                "urgency": urgency,
                "status": "pending",
                "created_round": 0,
                "completed_round": None,
                "source": "initial_extracted",
            })
    return tasks[:5]  # 最多 5 个


def _extract_deadlines_from_text(text: str) -> list[dict]:
    """从文本里提取还债日（"春税 / 夏税 / 月息"）"""
    if not text:
        return []
    deadlines: list[dict] = []
    # "利息每月三分" → 30 天后还 X 利息
    m = re.search(r"欠[^，。\n]{0,12}?([零一二三四五六七八九十百千半\d.]+)\s*两[（(]?[^，。\n]{0,12}?利息每月\s*([零一二三四五六七八九十百千半\d.]+)\s*分", text)
    if m:
        amount = _try_float(m.group(1)) or 0
        monthly_interest_rate = (_try_float(m.group(2)) or 0) / 100.0  # 几分 → 比例
        # 下次还息：30 天
        deadlines.append({
            "name": f"牙行欠债利息（月利{monthly_interest_rate*100:.0f}分）",
            "date": "30天后",
            "days_estimate": 30,
            "amount": f"{amount * monthly_interest_rate:.2f}两",
            "status": "pending",
            "source": "initial_extracted",
        })
    # "春税折银" → 6 月交
    m = re.search(r"(春税|夏税|秋税|冬税)", text)
    if m:
        season = m.group(1)
        deadline_month = {"春税": "5月", "夏税": "8月", "秋税": "11月", "冬税": "2月"}[season]
        deadlines.append({
            "name": f"{season}折银",
            "date": deadline_month,
            "days_estimate": 60,
            "amount": "约0.4-0.5两",
            "status": "pending",
            "source": "initial_extracted",
        })
    return deadlines


def extract_initial_state_from_character(
    cc: dict | None,
    identity_config: dict | None = None,
) -> dict:
    """从 custom_character dict 解析出结构化 initial_state

    解析层级（按优先级）：
    1. cc.initial_state 字段（如果 LLM 直接返回结构化）
    2. 正则解析 cc.background + cc.starting_situation 文本
    3. identity_config.base_state 兜底

    Returns:
        {
            "cash": float,
            "debt": float,
            "rice": float,
            "monthly_burn": float,
            "family_members": list[dict],
            "genealogy": list[dict],
            "active_tasks": list[dict],
            "upcoming_deadlines": list[dict],
            "source": "llm_struct" | "llm_text_parsed" | "identity_base" | "default",
        }
    """
    identity_config = identity_config or {}
    base = identity_config.get("base_state", {})

    # 兜底
    result = {
        "cash": _try_float(base.get("cash", 0.0)) or 0.0,
        "debt": _try_float(base.get("debt", 0.0)) or 0.0,
        "rice": _try_float(base.get("rice", 0.0)) or 0.0,
        "monthly_burn": _try_float(base.get("monthly_burn", 0.0)) or 0.0,
        "family_members": list(base.get("family_members", [])),
        "genealogy": list(base.get("genealogy", [])),
        "active_tasks": list(base.get("active_tasks", [])),
        "upcoming_deadlines": list(base.get("upcoming_deadlines", [])),
        "source": "identity_base" if base else "default",
    }

    if not cc:
        return result

    # 1️⃣ 优先用 LLM 直接返回的 initial_state 字段
    if isinstance(cc.get("initial_state"), dict):
        ist = cc["initial_state"]
        if "cash" in ist:
            v = _try_float(ist["cash"])
            if v is not None:
                result["cash"] = v
                result["source"] = "llm_struct"
        if "debt" in ist:
            v = _try_float(ist["debt"])
            if v is not None:
                result["debt"] = v
                result["source"] = "llm_struct"
        if "rice" in ist:
            v = _try_float(ist["rice"])
            if v is not None:
                result["rice"] = v
                result["source"] = "llm_struct"
        if "monthly_burn" in ist:
            v = _try_float(ist["monthly_burn"])
            if v is not None:
                result["monthly_burn"] = v
                result["source"] = "llm_struct"
        if isinstance(ist.get("family_members"), list) and ist["family_members"]:
            result["family_members"] = ist["family_members"]
            result["source"] = "llm_struct"
        if isinstance(ist.get("active_tasks"), list) and ist["active_tasks"]:
            result["active_tasks"] = ist["active_tasks"]
            result["source"] = "llm_struct"
        if isinstance(ist.get("upcoming_deadlines"), list) and ist["upcoming_deadlines"]:
            result["upcoming_deadlines"] = ist["upcoming_deadlines"]
            result["source"] = "llm_struct"
        if isinstance(ist.get("genealogy"), list) and ist["genealogy"]:
            result["genealogy"] = ist["genealogy"]
            result["source"] = "llm_struct"

    # 2️⃣ 文本正则解析（补足缺失字段）
    bg = cc.get("background", "") or ""
    ss = cc.get("starting_situation", "") or ""
    combined = f"{bg}\n{ss}"

    if result["source"] != "llm_struct" or True:  # 永远尝试补足
        v = _extract_cash_from_text(combined)
        if v is not None and (result["source"] == "identity_base" or result["source"] == "default"):
            result["cash"] = v
            result["source"] = "llm_text_parsed" if result["source"] != "llm_struct" else result["source"]
        elif v is not None and result["cash"] == 0.0:
            result["cash"] = v
            result["source"] = "llm_text_parsed" if result["source"] != "llm_struct" else result["source"]

        v = _extract_debt_from_text(combined)
        if v is not None and result["debt"] == 0.0:
            result["debt"] = v
            result["source"] = "llm_text_parsed" if result["source"] != "llm_struct" else result["source"]

        v = _extract_rice_from_text(combined)
        if v is not None and result["rice"] == 0.0:
            result["rice"] = v
            result["source"] = "llm_text_parsed" if result["source"] != "llm_struct" else result["source"]

        v = _extract_monthly_burn_from_text(combined)
        if v is not None and result["monthly_burn"] == 0.0:
            result["monthly_burn"] = v
            result["source"] = "llm_text_parsed" if result["source"] != "llm_struct" else result["source"]

    # 3️⃣ 家庭成员（从 cc.family 解析 — 文本里的更具体，优先覆盖 base）
    members = _extract_family_from_cc(cc)
    if members:
        result["family_members"] = members
        if result["source"] == "default":
            result["source"] = "llm_text_parsed"
        elif result["source"] == "identity_base":
            # 文本里的 family 比 base 更具体（用户实际 LLM 生成的角色家人）
            result["source"] = "llm_text_parsed"

    # 4️⃣ 谱系
    if not result["genealogy"]:
        genealogy = _extract_genealogy_from_cc(cc)
        if genealogy:
            result["genealogy"] = genealogy
            if result["source"] == "default":
                result["source"] = "llm_text_parsed"

    # 5️⃣ 任务和还债日（永远从文本提取，叠加到 base 之上）
    if not result["active_tasks"]:
        tasks = _extract_active_tasks_from_text(ss)
        if tasks:
            result["active_tasks"] = tasks
            if result["source"] == "default":
                result["source"] = "llm_text_parsed"
    if not result["upcoming_deadlines"]:
        deadlines = _extract_deadlines_from_text(ss)
        if deadlines:
            result["upcoming_deadlines"] = deadlines
            if result["source"] == "default":
                result["source"] = "llm_text_parsed"

    return result


def apply_initial_state(state, initial: dict) -> None:
    """把解析结果写入 GameState（in-place）"""
    if "cash" in initial:
        state.cash = float(initial["cash"])
    if "debt" in initial:
        state.debt = float(initial["debt"])
    if "rice" in initial:
        state.rice = float(initial["rice"])
    if "monthly_burn" in initial:
        state.monthly_burn = float(initial["monthly_burn"])
    if initial.get("family_members"):
        state.family_members = list(initial["family_members"])
    if initial.get("genealogy"):
        state.genealogy = list(initial["genealogy"])
    if initial.get("active_tasks"):
        # 合并到现有（避免覆盖）
        existing_titles = {t.get("title") for t in state.active_tasks}
        for t in initial["active_tasks"]:
            if t.get("title") not in existing_titles:
                state.active_tasks.append(t)
    if initial.get("upcoming_deadlines"):
        existing_names = {d.get("name") for d in state.upcoming_deadlines}
        for d in initial["upcoming_deadlines"]:
            if d.get("name") not in existing_names:
                state.upcoming_deadlines.append(d)
    # 把 source 写到 financial_status 便于排查
    state.financial_status["initial_state_source"] = initial.get("source", "default")
