"""游戏状态数据模型 + 序列化

设计参考：核心交付物合集v3.0.md 第七章"存档与重开机制设计"
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class GameState:
    """游戏状态数据模型"""

    # 🆕 v1.6.3 双层叙事保留配置
    NARRATIVE_RECENT_SIZE: int = 20   # 最近保留完整叙事的回合数
    NARRATIVE_ARCHIVE_SIZE: int = 100 # 早期摘要最大保留数
    """游戏状态——一局游戏的完整快照

    这是存档/读档/checkpoint的最小数据单位。
    """

    # === 身份信息 ===
    era_id: str = ""
    session_id: str = ""
    created_at: str = ""
    saved_at: str = ""
    # 角色身份（v1.1+：多身份支持）
    selected_identity: str = ""  # 选中的identity id（如"weaving_male"）
    player_gender: str = ""  # male/female（冗余字段便于快速访问）

    # === 🆕 v1.7.30 当前位置 ===
    # 玩家当前所在城市（"shengze" 表示在盛泽；"suzhou"/"hangzhou"/"songjiang"/"nanjing" 表示离乡）
    current_city: str = "shengze"  # 城市 id（对应 era.world.cities 中的 key）

    # === 时间进度 ===
    round_number: int = 1
    current_date: str = ""   # 月级时间（如"1587年1月"）
    day_of_month: int = 1    # 月内第几天（1-30），用于行动点推进

    # === 行动点（v1.3+：行动点耗尽才跳月） ===
    action_points_current: int = 3  # 当前月剩余行动点
    action_points_max: int = 3     # 每月基础行动点（按身份调整）

    # === 变量状态（key=variable_id, value=numeric） ===
    variables: dict[str, float] = field(default_factory=dict)

    # === 事件记录 ===
    triggered_events: list[str] = field(default_factory=list)  # historical_events的event_id
    triggered_triggers: list[str] = field(default_factory=list)  # triggers的id（once=true的）

    # === 成长状态 ===
    unlocked_insights: list[str] = field(default_factory=list)  # insight_tree节点id
    npc_levels: dict[str, str] = field(default_factory=dict)  # npc_id -> 当前关系等级
    value_shifts: dict[str, int] = field(default_factory=dict)  # value_dimension_id -> 累计偏移

    # === 记忆 ===
    event_log: list[dict] = field(default_factory=list)  # 每回合的事件摘要

    # === 🆕 v1.6.3 叙事历史：双层结构 ===
    # narrative_history: 兼容旧字段（= recent，但保留 20 回合而非 10）
    # narrative_recent: 最近 20 回合完整叙事（用于 LLM 上下文）
    # narrative_archive: 早期最多 100 回合的纯摘要（用于剧情回顾）
    narrative_history: list[dict] = field(default_factory=list)
    narrative_recent: list[dict] = field(default_factory=list)
    narrative_archive: list[dict] = field(default_factory=list)

    # === 🆕 v1.6.6 明朝名词首次出现跟踪（用于 tooltip 高亮未读词） ===
    # seen_terms: 玩家已经见过并解释过的名词（已读）
    # 新词首次出现时高亮 + tooltip
    seen_terms: list[str] = field(default_factory=list)

    # === 🆕 v1.7.26 侧边栏固化面板数据 ===
    # 从 LLM 输出（narrative 的 <aside> 块）解析，或后端兜底生成
    # 玩家右侧栏常驻：任务 / 还债日 / 财务
    # 🆕 v1.7.27 状态：active_tasks 加 status + created_at + completed_at（持久化防丢）
    # 玩家可标记完成；旧任务只删不丢（completed_tasks 保留）
    active_tasks: list[dict] = field(default_factory=list)        # [{"title":"春税预单","urgency":"high","status":"pending","created_round":1,"completed_round":null}, ...]
    upcoming_deadlines: list[dict] = field(default_factory=list)  # [{"name":"夏税","date":"1587年6月","days_estimate":90,"amount":"约1.5两","status":"pending"}, ...]
    financial_status: dict = field(default_factory=dict)          # {"cash":3.7,"rice_days":7,"monthly_burn":1.2,...}
    completed_tasks: list[dict] = field(default_factory=list)     # 🆕 v1.7.27 已完成任务历史（玩家可查看）

    # === 🆕 v1.7.30 钱结构化（替代 financial_status 部分字段） ===
    # 之前 financial_status 是 dict（LLM 自由写），现在 cash/rice/debt 严格类型
    # 后端校验：财务字段变更必须通过 state.apply_financial_change()（拒绝 LLM 自由改）
    cash: float = 0.0           # 现金（两，1 两 = 1000 文）
    rice: float = 0.0           # 存粮（石）
    debt: float = 0.0           # 欠债（两）
    monthly_burn: float = 0.0   # 每月基础开销（两，自动计算）
    # financial_log: 财务变动日志（每笔交易 1 条）
    # [{"date":"1587年1月","round":1,"type":"sell_silk","amount":+0.5,"note":"卖湖绫一匹","location":"盛泽"}]
    financial_log: list[dict] = field(default_factory=list)

    # === 🆕 v1.7.1 Per-Save Character Wiki ===
    # 人物知识图谱：仅本存档，删除/重置存档时清空
    # 用于 LLM 上下文 + 侧边栏 UI + 支线一致性
    character_wiki: dict = field(default_factory=dict)  # CharacterWiki.to_dict()

    # === 节奏追踪（规则引擎的元数据） ===
    player_idle_rounds: int = 0
    rounds_since_last_insight: int = 0

    # === 全局轻回合计数（用于重/轻回合节奏控制） ===
    consecutive_light_rounds: int = 0

    # === 🐛 Bug #4 修复：v1.4.0+ 8 SKILL 字段 ===
    route_tendency: str = ""           # 当前路线倾向：weaving/imperial_exam/leave/monk/tax_resist/business
    recent_scenes: list[str] = field(default_factory=list)  # 最近 10 个场景（用于 SKILL-1 读场）
    recent_inputs: list[str] = field(default_factory=list)  # 最近 5 个玩家输入
    failure_type: str = ""             # 当前回合失败类型（persuasion/action/...）

    # === 🐛 v1.5.1 P0 Bug #1 修复：玩家 LLM 生成的人设 ===
    custom_character: dict = field(default_factory=dict)  # {name, hometown, family, background, voices, skills, opening_paragraph, ...}

    # === 🐛 v1.5.1 P1 Issue 5 修复：voice_options 持久化（用于加载存档后恢复） ===
    last_voice_options: list[dict] = field(default_factory=list)  # 最后一次 DM 返回的 voice_options

    def to_dict(self) -> dict:
        return asdict(self)

    # 🆕 v1.7.30: 财务变更（带日志 + 校验）
    def apply_financial_change(
        self,
        amount: float,
        type_: str,
        note: str,
        location: str = "",
        round_number: int | None = None,
    ) -> dict:
        """应用一笔财务变更（核心入口，替代 LLM 自由改 cash/rice/debt）

        Args:
            amount: 金额（两），正为入账，负为支出
            type_: 交易类型（"sell_silk" / "buy_thread" / "pay_tax" / "borrow" / "repay" / "rent" / "gift" ...）
            note: 备注
            location: 交易地点
            round_number: 回合数（默认 self.round_number）

        Returns:
            交易记录 dict（已追加到 financial_log）

        校验规则：
        - 单笔交易上限 100 两（防 LLM 编造"天降 500 两"）
        - 单笔下限 -50 两（防 LLM 把玩家钱扣到负数过多）
        """
        MAX_TRANSACTION = 100.0
        MIN_TRANSACTION = -50.0
        if amount > MAX_TRANSACTION:
            raise ValueError(f"单笔入账 {amount} 两超过上限 {MAX_TRANSACTION}（疑似 LLM 编造）")
        if amount < MIN_TRANSACTION:
            raise ValueError(f"单笔支出 {amount} 两低于下限 {MIN_TRANSACTION}（疑似 LLM 编造）")
        # 应用变更
        if type_ == "borrow":
            self.debt += abs(amount)  # 借钱 → 欠债增加（绝对值）
        elif type_ == "repay":
            self.debt = max(0.0, self.debt - abs(amount))  # 还钱 → 欠债减少
        else:
            # 现金变化（正入负出）
            self.cash += amount
            # 防止现金扣到 -0.1
            if self.cash < 0:
                self.cash = 0.0
        entry = {
            "date": self.current_date,
            "round": round_number if round_number is not None else self.round_number,
            "type": type_,
            "amount": amount,
            "note": note,
            "location": location or self.current_city,
        }
        self.financial_log.append(entry)
        return entry

    def snapshot_financial(self) -> dict:
        """返回当前财务快照（DM 可见 / UI 渲染用）"""
        return {
            "cash": self.cash,
            "rice": self.rice,
            "debt": self.debt,
            "monthly_burn": self.monthly_burn,
            "net_worth": self.cash - self.debt,
            "rice_days_estimate": (self.rice / max(self.monthly_burn, 0.1)) * 30 if self.monthly_burn > 0 else None,
            "log_count": len(self.financial_log),
        }

    def save(self, path: Path) -> None:
        """保存到JSON文件"""
        self.saved_at = datetime.now().isoformat(timespec="seconds")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "GameState":
        """从JSON文件加载"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def append_narrative(self, round_number: int, narrative: str, summary: str) -> None:
        """追加一回合的叙事到历史

        🆕 v1.6.3 双层保留：
        1. 先入 narrative_recent + narrative_history（最近 N 回合完整叙事）
        2. 超 N 回合 → 弹出最旧的，提取摘要到 narrative_archive
        3. archive 最多保留 N 条
        """
        entry = {
            "round": round_number,
            "narrative": narrative,
            "summary": summary,
        }
        self.narrative_recent.append(entry)
        self.narrative_history.append(entry)  # 兼容旧字段

        # 超 N 回合：从 recent 弹到 archive
        while len(self.narrative_recent) > self.NARRATIVE_RECENT_SIZE:
            old = self.narrative_recent.pop(0)
            # 生成归档版本（保留前 200 字 + 关键元数据）
            archived = {
                "round": old["round"],
                "summary": old.get("summary", "") or old.get("narrative", "")[:200],
                "narrative_preview": old.get("narrative", "")[:200],
            }
            self.narrative_archive.append(archived)
            # 同步更新 narrative_history（旧字段不弹，保持兼容）
            # 因为 narrative_history 现在只是 narrative_recent 的镜像

        # archive 上限
        if len(self.narrative_archive) > self.NARRATIVE_ARCHIVE_SIZE:
            self.narrative_archive = self.narrative_archive[-self.NARRATIVE_ARCHIVE_SIZE:]

    def get_recap(self, recent_count: int = 5, archive_count: int = 30) -> dict:
        """🆕 v1.6.3 剧情回顾

        Args:
            recent_count: 返回最近多少回合完整叙事（默认 5）
            archive_count: 返回归档摘要多少条（默认 30）

        Returns:
            {
                "round_number": 当前回合数,
                "current_date": 当前日期,
                "total_narratives": 记录总数,
                "recent": [最近 N 回合完整...],
                "archive": [早期 M 条摘要],
                "month_markers": [月份变更节点...]
            }
        """
        # 找到叙事中的月份标记（用 current_date 字段变化的回合）
        recent = self.narrative_recent[-recent_count:] if recent_count > 0 else []
        archive = self.narrative_archive[-archive_count:] if archive_count > 0 else []
        return {
            "round_number": self.round_number,
            "current_date": self.current_date,
            "total_narratives": len(self.narrative_recent) + len(self.narrative_archive),
            "recent": recent,
            "archive": archive,
        }

    def get_visible_state(self) -> dict:
        """返回给玩家可见的状态（过滤敏感信息）"""
        return {
            "round": self.round_number,
            "date": self.current_date,
            "day_of_month": self.day_of_month,
            "action_points_current": self.action_points_current,
            "action_points_max": self.action_points_max,
            "variables": {k: round(v, 1) for k, v in self.variables.items()},
            "unlocked_insights_count": len(self.unlocked_insights),
            "npc_levels": dict(self.npc_levels),
        }

    def consume_action_points(self, cost: int) -> dict:
        """消耗行动点；如果耗尽则推进到下月

        Returns:
            {
                "consumed": cost,
                "remaining": 剩余行动点,
                "month_advanced": 是否跳月,
                "new_date": 新日期,
            }
        """
        # cost 至少为 0（问询/观察不消耗）
        cost = max(0, cost)
        # 实际消耗不能超过剩余
        actual_cost = min(cost, self.action_points_current)
        self.action_points_current -= actual_cost

        month_advanced = False
        new_date = self.current_date
        if self.action_points_current <= 0:
            # 跳到下月
            month_advanced = True
            self.round_number += 1
            # 解析当前年月
            import re
            m = re.match(r"(\d+)年(\d+)月", self.current_date)
            if m:
                year, month = int(m.group(1)), int(m.group(2))
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                self.current_date = f"{year}年{month}月"
            else:
                # fallback：保留旧日期
                self.current_date = self.current_date
            self.day_of_month = 1
            # 恢复行动点
            self.action_points_current = self.action_points_max
            new_date = self.current_date

        return {
            "consumed": actual_cost,
            "remaining": self.action_points_current,
            "month_advanced": month_advanced,
            "new_date": new_date,
        }


def make_initial_state(era_id: str, config: dict[str, Any], selected_identity: str = "") -> GameState:
    """根据时代包配置创建初始游戏状态

    Args:
        era_id: 时代包ID
        config: 时代包配置
        selected_identity: 选中的身份id（v1.1+多身份支持）
    """
    variables = {}
    for v in config.get("mechanics", {}).get("variables", []):
        variables[v["id"]] = v.get("initial", 0)

    # 初始日期
    timeline = config.get("world", {}).get("timeline", {})
    start = timeline.get("start", {})
    initial_date = f"{start.get('year', '?')}年{start.get('month', '?')}月"

    # 解析selected_identity的gender和action_points_max
    player_gender = ""
    action_points_max = 3  # 默认
    if selected_identity:
        identities = config.get("world", {}).get("player_identities", {})
        if selected_identity in identities:
            ident = identities[selected_identity]
            player_gender = ident.get("gender", "")
            # 🐛 Issue #5 修复：从 identity 配置读取 action_points_max
            action_points_max = ident.get("action_points_max", 3)
    elif "player_identity" in config.get("world", {}):
        # 兼容旧格式
        player_gender = config["world"]["player_identity"].get("gender", "")

    return GameState(
        era_id=era_id,
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
        created_at=datetime.now().isoformat(timespec="seconds"),
        saved_at="",
        selected_identity=selected_identity,
        player_gender=player_gender,
        round_number=1,
        current_date=initial_date,
        action_points_max=action_points_max,  # 🐛 Issue #5 修复
        action_points_current=action_points_max,  # 初始等于 max
        variables=variables,
        triggered_events=[],
        triggered_triggers=[],
        unlocked_insights=[],
        npc_levels={},
        value_shifts={},
        event_log=[],
        narrative_history=[],
        player_idle_rounds=0,
        rounds_since_last_insight=0,
        consecutive_light_rounds=0,
        # 🐛 Bug #4 修复：v1.4.0+ 8 SKILL 字段
        route_tendency="",
        recent_scenes=[],
        recent_inputs=[],
        failure_type="",
        # 🐛 v1.5.1 P0 Bug #1 修复：玩家 LLM 生成的人设
        custom_character={},
    )
