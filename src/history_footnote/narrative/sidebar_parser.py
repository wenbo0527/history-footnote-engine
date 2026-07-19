"""🆕 v1.7.26 侧边栏数据解析

从 narrative 提取结构化数据，固化到右侧栏。
LLM 输出 `<aside>` 块时优先解析；否则基于 narrative 文本智能推断。

aside 块格式（LLM 输出）:
<aside>
家庭：丁口X口（关系X岁）
待办：春税预单、束脩2两、米粮、桑叶定钱
外部动态：赵里长午后到访收税预单
财务：现金X两、米X日、其他支出
还债：春税（约Y天后）、夏税（约Z天后）
</aside>
"""
import re
from typing import Any


def parse_aside_block(narrative: str) -> dict[str, Any]:
    """🆕 v1.7.26: 解析 narrative 中的 <aside> 块

    Returns:
        {
            "active_tasks": [...],         # 待办任务
            "upcoming_deadlines": [...],   # 还债日
            "financial_status": {...},     # 财务状态
        }
    """
    result = {
        "active_tasks": [],
        "upcoming_deadlines": [],
        "financial_status": {},
    }

    if not narrative:
        return result

    # 提取 <aside>...</aside> 块
    aside_match = re.search(r"<aside[^>]*>(.+?)</aside>", narrative, re.DOTALL)
    if not aside_match:
        return result

    aside_text = aside_match.group(1).strip()

    # 解析每一行
    for line in aside_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 待办：xxx
        if line.startswith("待办") or line.startswith("待办："):
            tasks_str = line.split("：", 1)[1] if "：" in line else line[2:]
            for task in re.split(r"[、，,；;]", tasks_str):
                task = task.strip()
                if not task:
                    continue
                # 估算 urgency：含"预单/税/欠/急" → high
                urgency = "high" if any(kw in task for kw in ["预单", "税", "欠", "急", "束脩"]) else "normal"
                result["active_tasks"].append({
                    "title": task,
                    "urgency": urgency,
                })
        # 还债：xxx
        elif line.startswith("还债") or line.startswith("还债："):
            debts_str = line.split("：", 1)[1] if "：" in line else line[2:]
            for debt in re.split(r"[、，,；;]", debts_str):
                debt = debt.strip()
                if not debt:
                    continue
                # 提取天数
                days_match = re.search(r"(\d+)\s*天", debt)
                days_estimate = int(days_match.group(1)) if days_match else None
                # 提取金额
                amount_match = re.search(r"(\d+(?:\.\d+)?)\s*两", debt)
                amount = f"约{amount_match.group(1)}两" if amount_match else None
                result["upcoming_deadlines"].append({
                    "name": debt,
                    "days_estimate": days_estimate,
                    "amount": amount,
                })
        # 财务：xxx
        elif line.startswith("财务") or line.startswith("财务："):
            fin_str = line.split("：", 1)[1] if "：" in line else line[2:]
            # 提取数字
            cash_match = re.search(r"(\d+(?:\.\d+)?)\s*两", fin_str)
            if cash_match:
                result["financial_status"]["cash"] = float(cash_match.group(1))
            rice_match = re.search(r"米(\d+)\s*日", fin_str)
            if rice_match:
                result["financial_status"]["rice_days"] = int(rice_match.group(1))
            # 兜底：存原始文本
            result["financial_status"]["raw"] = fin_str[:100]
        # 家庭：xxx
        elif line.startswith("家庭"):
            result["financial_status"]["family"] = line.split("：", 1)[1] if "：" in line else line[2:]
        # 外部动态：xxx
        elif line.startswith("外部动态") or line.startswith("动态"):
            result["financial_status"]["external"] = line.split("：", 1)[1] if "：" in line else line[2:]

    return result


def infer_from_narrative(narrative: str, variables: dict) -> dict[str, Any]:
    """🆕 v1.7.26: LLM 没输出 <aside> 时，从 narrative 推断

    提取策略:
    - 数字 + 两 → 财务金额
    - "X天" / "约X日" → 还债日
    - "税/束脩/欠" → 任务
    """
    result = {
        "active_tasks": [],
        "upcoming_deadlines": [],
        "financial_status": {},
    }

    if not narrative:
        return result

    # 财务：找"X两"数字
    amounts = re.findall(r"(\d+(?:\.\d+)?)\s*两", narrative)
    if amounts:
        result["financial_status"]["cash"] = float(amounts[0])
        if len(amounts) > 1:
            result["financial_status"]["monthly_burn"] = float(amounts[1])

    # 还债日：找"X天/日"
    days = re.findall(r"(\d+)\s*[天日](?![前之])", narrative)
    if days:
        for d in days[:3]:
            result["upcoming_deadlines"].append({
                "name": "未知债务",
                "days_estimate": int(d),
                "amount": None,
            })

    # 任务：找关键词
    task_keywords = {
        "春税": "春税预单",
        "夏税": "夏税",
        "束脩": "阿宝束脩",
        "桑叶": "桑叶定钱",
        "米粮": "米粮",
        "赋": "赋税",
    }
    for kw, title in task_keywords.items():
        if kw in narrative:
            result["active_tasks"].append({
                "title": title,
                "urgency": "high" if "税" in title or "束脩" in title else "normal",
            })

    # 兜底：从 variables 拿
    for k, v in variables.items():
        if "cash" in k.lower() or "银" in k or "钱" in k:
            result["financial_status"]["cash"] = float(v)
        elif "rice" in k.lower() or "米" in k:
            result["financial_status"]["rice_days"] = int(float(v))

    return result


def build_sidebar_data(narrative: str, variables: dict, existing_tasks: list = None) -> dict[str, Any]:
    """🆕 v1.7.26: 主入口 — 解析 + 推断 + 合并
    🆕 v1.7.27: 任务合并（持久化防丢）

    合并策略:
    - 现有任务（existing_tasks）保留 pending 状态
    - 新解析的任务如果 title 匹配现有，则更新（不覆盖 status）
    - 新任务追加为 pending
    - 现有 completed 任务从 active 移到 completed_tasks
    """
    # 1. 尝试解析 <aside> 块
    parsed = parse_aside_block(narrative)
    # 2. 推断（补充 parsed 空缺的部分）
    inferred = infer_from_narrative(narrative, variables)
    # 3. 合并（parsed 优先）
    for k in parsed:
        if not parsed[k]:
            parsed[k] = inferred[k]
    # 🆕 v1.7.27: 任务合并（防丢）
    if existing_tasks:
        parsed["active_tasks"] = _merge_tasks(
            existing_tasks, parsed["active_tasks"]
        )
    return parsed


def _merge_tasks(existing: list, new: list) -> list:
    """🆕 v1.7.27: 合并任务列表（保留状态 + 防丢）

    Args:
        existing: state.active_tasks（已有任务，含 status/created_round）
        new: 从 narrative 解析的新任务
    Returns:
        合并后的任务列表
    """
    # 用 title 作为 key
    existing_map = {t.get("title"): t for t in existing if t.get("title")}
    new_map = {t.get("title"): t for t in new if t.get("title")}
    merged = []
    # 1. 现有任务保留
    for title, t in existing_map.items():
        if t.get("status") == "completed":
            continue  # 已完成的移到 completed_tasks
        if title in new_map:
            # 新数据补充（保留 status）
            new_data = new_map[title]
            merged.append({
                **new_data,  # 新解析的 urgency 等
                "status": t.get("status", "pending"),  # 保留状态
                "created_round": t.get("created_round"),
                "completed_round": t.get("completed_round"),
            })
        else:
            # 现有任务不在新数据中 → 保留
            merged.append(t)
    # 2. 新任务追加为 pending
    for title, t in new_map.items():
        if title not in existing_map:
            merged.append({
                **t,
                "status": "pending",
                "created_round": None,
                "completed_round": None,
            })
    return merged


def mark_task_completed(tasks: list, title: str, current_round: int) -> tuple[list, list, bool]:
    """🆕 v1.7.27: 标记任务完成

    Returns:
        (active_tasks, completed_tasks, found) — 新 active 列表 + 新 completed 列表 + 是否找到
    """
    new_active = []
    completed = []
    found = False
    for t in tasks:
        if t.get("title") == title and t.get("status") != "completed":
            completed.append({
                **t,
                "status": "completed",
                "completed_round": current_round,
            })
            found = True
        else:
            new_active.append(t)
    return new_active, completed, found