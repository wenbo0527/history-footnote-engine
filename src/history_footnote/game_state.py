"""游戏状态数据模型 + 序列化

设计参考：核心交付物合集v3.0.md 第七章"存档与重开机制设计"
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


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
    # 玩家当前所在城市（"shengze" 表示在盛泽；"suzhou"/"hangzhou"/"nanjing" 表示离乡）
    current_city: str = "shengze"  # 城市 id（对应 era.world.cities 中的 key）

    # 🆕 v2.10.1 W77: 待确认的城市变更
    # LLM 触发 arrive.X 事件时，先写入此字段 → 前端弹窗让用户确认
    # 确认后由 /api/confirm_city_change 清除 + 更新 current_city
    # 拒绝后由 /api/reject_city_change 清除（current_city 不变）
    pending_city_change: Optional[dict] = None

    # === 🆕 v2.4 当前位置（具体地点）===
    # 玩家当前在哪个地点（对应 era.world.locations.list 中的 id）
    # 如 "home"（自家）、"tooth_market"（牙行）
    # 默认与 era.world.locations.default_location 一致
    current_location: str = ""
    # 已去过的地点（用于展示足迹 + 防止 narrative 跑出位置）
    visited_locations: list = field(default_factory=list)
    # 听过但没去过的地点（❓ 状态，用于"未知道点"探索）
    heard_locations: list = field(default_factory=list)

    # === 🆕 v2.5 全局随机种子（replay 机制）===
    # 用途：
    # 1. 所有 Python random.* 调用用此 seed → 可重放
    # 2. QA/debug 可以用同一 seed 重现问题
    # 3. 玩家可以"同 seed 重玩"（分享有趣开局给朋友）
    # 4. 命运卡抽取也用此 seed（v2.5.x 命运卡系统）
    # 默认 0 = 每次随机；> 0 = 固定 seed
    seed: int = 0
    # 玩家自选 seed（如果 None 用系统生成）
    requested_seed: int = 0

    # === 🆕 v2.5 命运卡系统 ===
    # 手牌：开局抽 5 张
    fate_hand: list = field(default_factory=list)
    # 已用过的卡（避免重复触发）
    fate_used: list = field(default_factory=list)
    # 命运卡触发的特殊事件标记（如 "zhou_secret"）
    fate_event_flags: list = field(default_factory=list)
    # NPC 关系（key=npc_name, value=affinity）
    npc_relations: dict = field(default_factory=dict)
    # 路遇概率倍率（命运卡可调）
    encounter_multiplier: float = 1.0
    # 玩家当前生效的 buff 列表
    active_buffs: list = field(default_factory=list)

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

    # === 🆕 v2.7.2 结构化剧情事实 ===
    # 从每回合 narrative 自动提取的 4 类 fact（人物/事实/伏笔/未解）
    # 替代贫瘠的 events_to_save[0] summary → 注入下回合 prompt
    # 容量限制 50 条（防 prompt 爆炸）
    narrative_facts: list[dict] = field(default_factory=list)  # NarrativeFact.to_dict()

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

    # === 🆕 v1.7.30 家人结构化 ===
    # 之前 custom_character.family 是 dict（LLM 写），不可信
    # 4 城市集成后，玩家离乡会触发"家人"互动（盛泽有老宅/祖坟/族谱）
    # family_members: 玩家直接亲属（妻/子/女/父母/兄弟姐妹）
    # [{"id":"fm_wife", "name":"沈氏", "relation":"wife", "age":27, "location":"shengze",
    #   "health":"healthy", "relationship_score":70, "alive":True,
    #   "notes":"操持家务也帮忙缫丝，娘家在隔壁村", "story_hooks_used":[]}]
    family_members: list[dict] = field(default_factory=list)

    # === 🆕 v1.7.30 谱系结构化（扩展家族） ===
    # 区别于 family_members：family 是"自己家"（直系亲属），
    # genealogy 是"大家族"（祖上三代/堂表亲/姻亲/继承关系/族产）
    # 支持"祖宅/家业/族产"继承链；"我是谁家的孩子" 答
    # [{"id":"ge_patriarch", "relation":"patriarch", "name":"施善", "alive":False,
    #   "location":"shengze", "generation":0,
    #   "is_known_to_player":True, "notes":"祖父，购置织机三台，族产奠基人"}]
    genealogy: list[dict] = field(default_factory=list)

    # === 🆕 v1.7.30 城市财产 + 跨城库存 ===
    # 4 城市集成后，玩家在多城市可能拥有财产（铺面/作坊/寄存货物）
    # city_properties: {city_id → list[property]} —— 该城市的玩家财产
    # inventory: {city_id → list[item]} —— 该城市的玩家寄存物
    # 例：
    # city_properties = {
    #   "suzhou": [{"id":"prop_001", "type":"shop", "name":"阊门绸铺",
    #               "value":120, "rent_per_month":0.5, "status":"operating"}],
    #   "shengze": [{"id":"prop_002", "type":"workshop", "name":"自家织房",
    #                "value":15, "status":"own"}]
    # }
    # inventory = {
    #   "shengze": [{"id":"inv_001", "type":"silk_bolt", "name":"湖绫",
    #                "qty":10, "unit_value":0.5, "location_in_city":"自宅"}],
    #   "suzhou": [{"id":"inv_002", "type":"silk_bolt", "name":"湖绫",
    #                "qty":3, "unit_value":0.7, "location_in_city":"阊门牙行寄存"}]
    # }
    city_properties: dict = field(default_factory=dict)  # dict[city_id] -> list[property]
    inventory: dict = field(default_factory=dict)  # dict[city_id] -> list[item]

    # === 🆕 v1.7.30 本次发现层（discoveries）===
    # 与 era-level 知识库分离：玩家和 LLM 在游戏中创建的"地点/人物/物品/信件/事实"
    # source 标签: "era"（标准）/ "save"（LLM 自由生成）/ "player"（玩家主动标注）
    # 用 add_discovery() 添加，可被前端 Wiki 弹层展示
    discoveries: dict = field(default_factory=dict)
    # 结构：
    # {
    #   "places": {place_id: {id, name, city, description, source, created_round, ...}},
    #   "persons": {person_id: {id, name, role, city, description, source, ...}},
    #   "items": {item_id: {id, name, type, owner, qty, source, ...}},
    #   "letters": {letter_id: {id, from, to, date, content, urgency, status, source, ...}},
    #   "events": {event_id: {id, name, date, place, description, source, ...}},
    #   "facts": [{id, text, source, heard_from, reliability, created_round}],
    # }

    # === 🆕 v1.7.1 Per-Save Character Wiki ===
    # 人物知识图谱：仅本存档，删除/重置存档时清空
    # 用于 LLM 上下文 + 侧边栏 UI + 支线一致性
    character_wiki: dict = field(default_factory=dict)  # CharacterWiki.to_dict()

    # === 🆕 v1.7.30 账户隔离 ===
    # 存档绑定的账户 ID（v1.7.30 账户系统）
    # 空字符串 = 旧存档/未登录/访客
    account_id: str = ""

    # === 🆕 v2.8.0 章节制状态（嵌套 dataclass，避免字段超 250） ===
    # L2 章节层的运行时状态
    # 段一：只接入结构 + 硬编码第 1 章蓝图
    # 段二：接入 LLM 自由生成（fill_chapter_blueprint Tool）
    # 段三：接入路径三态（path_state / 4 触发器）
    # 段四：接入 Build × 章节分化
    # 旧存档无此字段 → field(default_factory) 自动建空对象，零回归
    from history_footnote.chapter.types import ChapterState
    chapter_state: ChapterState = field(default_factory=ChapterState)

    # === 🆕 v2.8.0 段三 路径运行时状态（嵌套 dataclass） ===
    # 路径三态：locked / active / dormant
    # 段三 W11：基础数据结构（NarrativePath + PathState + PathRegistry）
    # 段三 W12：4 触发器（选项/NPC/板块/章节转化）
    # 段三 W13：Coordinator 接入路径状态更新
    # 旧存档无此字段 → field(default_factory) 自动建空对象，零回归
    from history_footnote.chapter.paths import PathState
    path_state: PathState = field(default_factory=PathState)

    # === 🆕 v2.8.0 段四 W14 玩家 Build（重玩价值核心） ===
    # 段四：同 seed 不同 Build → 体验不同
    # 合法值："" (未选) / "守乡人" / "外望人" / 其他扩展
    # 旧存档无此字段 → 空字符串向后兼容
    player_build: str = ""

    # === 🆕 v2.8.0 段五 W15 板块运行时状态（嵌套 dataclass） ===
    # 4 状态：stable / tense / shifting / collapsed
    # 段五 W15：基础数据结构（Plate + PlateState + PlateRegistry）
    # 段五 W16：tension_fields + transmission 引擎
    # 段五 W17：PathSwitcher 触发器 3 完整实现
    # 旧存档无此字段 → field(default_factory) 自动建空对象，零回归
    from history_footnote.chapter.plates import PlateState
    plate_state: PlateState = field(default_factory=PlateState)

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

    # 🆕 v1.7.30: 家人 CRUD（结构化操作）
    def add_family_member(self, member: dict) -> dict:
        """添加一位家人（自动校验 id 唯一）

        Args:
            member: 完整 member dict（含 id/name/relation/age/location/...）
        Returns:
            添加后的 member
        Raises:
            ValueError: id 重复 / 必填字段缺失
        """
        required = {"id", "name", "relation"}
        missing = required - set(member.keys())
        if missing:
            raise ValueError(f"家人字段缺失：{missing}")
        if any(m.get("id") == member["id"] for m in self.family_members):
            raise ValueError(f"家人 id 重复：{member['id']}")
        # 默认值填充
        member.setdefault("location", "shengze")
        member.setdefault("health", "healthy")
        member.setdefault("alive", True)
        member.setdefault("relationship_score", 50)
        member.setdefault("notes", "")
        member.setdefault("story_hooks_used", [])
        self.family_members.append(member)
        return member

    def update_family_member(self, member_id: str, **updates) -> dict | None:
        """更新一位家人的字段（按 id 定位）

        Args:
            member_id: 家人 id
            **updates: 要更新的字段（health/location/relationship_score/notes/...）
        Returns:
            更新后的 member；找不到返回 None
        """
        for m in self.family_members:
            if m.get("id") == member_id:
                m.update(updates)
                return m
        return None

    def get_family_member(self, member_id: str) -> dict | None:
        return next((m for m in self.family_members if m.get("id") == member_id), None)

    def get_family_by_location(self, city_id: str) -> list[dict]:
        """获取某城市的所有家人（玩家去某城市时，DM 知道"家人"在不在那）"""
        return [m for m in self.family_members if m.get("location") == city_id]

    # 🆕 v1.7.30: 谱系 CRUD
    def add_genealogy_entry(self, entry: dict) -> dict:
        """添加一位族人

        Args:
            entry: 完整 entry dict（含 id/relation/name/...）
        Returns:
            添加后的 entry
        Raises:
            ValueError: id 重复 / 必填字段缺失
        """
        required = {"id", "relation", "name"}
        missing = required - set(entry.keys())
        if missing:
            raise ValueError(f"谱系字段缺失：{missing}")
        if any(e.get("id") == entry["id"] for e in self.genealogy):
            raise ValueError(f"谱系 id 重复：{entry['id']}")
        entry.setdefault("alive", True)
        entry.setdefault("generation", 0)
        entry.setdefault("is_known_to_player", True)
        entry.setdefault("notes", "")
        self.genealogy.append(entry)
        return entry

    def get_genealogy_by_relation(self, relation: str) -> list[dict]:
        """按关系筛（如 'patriarch'/'grandparent'/'uncle'/'cousin'）"""
        return [e for e in self.genealogy if e.get("relation") == relation]

    def get_known_ancestors(self, max_generation: int = 3) -> list[dict]:
        """获取已知祖先（≤ N 代）—— 用于离乡路线"祖上是谁"叙事"""
        return [e for e in self.genealogy
                if e.get("is_known_to_player")
                and e.get("alive") is False
                and e.get("generation", 0) <= max_generation]

    # 🆕 v1.7.30: 城市财产 CRUD
    def add_property(self, city_id: str, prop: dict) -> dict:
        """在指定城市添加一处财产

        Args:
            city_id: 城市 id（如 "suzhou"）
            prop: 财产 dict（含 id/type/name/value/...）
        """
        required = {"id", "type", "name"}
        missing = required - set(prop.keys())
        if missing:
            raise ValueError(f"财产字段缺失：{missing}")
        prop.setdefault("value", 0)
        prop.setdefault("status", "own")
        self.city_properties.setdefault(city_id, []).append(prop)
        return prop

    def get_properties_in_city(self, city_id: str) -> list[dict]:
        return self.city_properties.get(city_id, [])

    def get_total_property_value(self) -> float:
        """所有城市的财产总值（两）"""
        total = 0.0
        for props in self.city_properties.values():
            total += sum(p.get("value", 0) for p in props)
        return total

    # 🆕 v1.7.30: 跨城库存 CRUD
    def add_inventory_item(self, city_id: str, item: dict) -> dict:
        """在指定城市添加一项库存

        Args:
            city_id: 城市 id
            item: 库存 dict（含 id/type/name/qty/...）
        """
        required = {"id", "type", "name", "qty"}
        missing = required - set(item.keys())
        if missing:
            raise ValueError(f"库存字段缺失：{missing}")
        if item["qty"] < 0:
            raise ValueError(f"库存数量不能为负：{item['qty']}")
        item.setdefault("unit_value", 0)
        item.setdefault("location_in_city", "")
        self.inventory.setdefault(city_id, []).append(item)
        return item

    def transfer_inventory(self, item_id: str, from_city: str, to_city: str) -> dict | None:
        """跨城转移库存（运货）

        Args:
            item_id: 物品 id
            from_city: 出发城市
            to_city: 目标城市
        Returns:
            转移后的 item；找不到返回 None
        """
        items = self.inventory.get(from_city, [])
        idx = next((i for i, it in enumerate(items) if it.get("id") == item_id), None)
        if idx is None:
            return None
        item = items.pop(idx)
        self.inventory.setdefault(to_city, []).append(item)
        return item

    def get_inventory_summary(self) -> dict:
        """库存摘要（DM/UI 可见）"""
        out = {}
        for city, items in self.inventory.items():
            total_qty = sum(it.get("qty", 0) for it in items)
            total_value = sum(it.get("qty", 0) * it.get("unit_value", 0) for it in items)
            out[city] = {"items": len(items), "total_qty": total_qty, "total_value": total_value}
        return out

    # 🆕 v1.7.30：discoveries CRUD（单次游戏中创建"地点/人物/物品/信件/事实"）
    def add_discovery(self, kind: str, data: dict, source: str = "save") -> dict:
        """添加一条发现

        Args:
            kind: 类别（place/person/item/letter/event/fact）
            data: 数据 dict
            source: 来源（era / save / player）

        Returns:
            添加后的对象

        Raises:
            ValueError: kind 非法或缺必填字段
        """
        valid_kinds = {"place", "person", "item", "letter", "event", "fact"}
        if kind not in valid_kinds:
            raise ValueError(f"discovery kind 非法: {kind}，需为 {valid_kinds} 中的一个")
        # 自动填充元数据
        data.setdefault("source", source)
        data.setdefault("created_round", self.round_number)
        data.setdefault("created_at", self.current_date)
        # facts 是 list，其他是 dict
        if kind == "fact":
            self.discoveries.setdefault("facts", []).append(data)
            return data
        # dict[kind + 's']
        bucket = self.discoveries.setdefault(f"{kind}s", {})
        obj_id = data.get("id") or f"{kind[:3]}_{len(bucket) + 1:03d}_{self.round_number}"
        data["id"] = obj_id
        bucket[obj_id] = data
        return data

    def update_discovery(self, kind: str, obj_id: str, **updates) -> dict | None:
        """更新一条发现（按 kind + id 定位）

        Returns:
            更新后的对象；找不到返回 None
        """
        if kind == "fact":
            # facts 是 list，按 id 找
            for f in self.discoveries.get("facts", []):
                if f.get("id") == obj_id:
                    f.update(updates)
                    return f
            return None
        bucket = self.discoveries.get(f"{kind}s", {})
        obj = bucket.get(obj_id)
        if obj is None:
            return None
        obj.update(updates)
        return obj

    def get_discoveries(self, kind: str | None = None, source: str | None = None) -> list[dict]:
        """获取发现列表

        Args:
            kind: 类别过滤（None=全部）
            source: 来源过滤（None=全部）

        Returns:
            发现列表
        """
        results = []
        if kind is None:
            # 返回所有
            for k, v in self.discoveries.items():
                if k == "facts":
                    results.extend(v)
                else:
                    results.extend(v.values())
        else:
            if kind == "fact":
                results = list(self.discoveries.get("facts", []))
            else:
                results = list(self.discoveries.get(f"{kind}s", {}).values())
        if source is not None:
            results = [r for r in results if r.get("source") == source]
        return results

    def get_discoveries_summary(self) -> dict:
        """按 source 标签统计发现数"""
        out = {"era": 0, "save": 0, "player": 0, "total": 0}
        for r in self.get_discoveries():
            src = r.get("source", "save")
            out[src] = out.get(src, 0) + 1
            out["total"] += 1
        out["by_kind"] = {}
        for k in ("place", "person", "item", "letter", "event", "fact"):
            out["by_kind"][k] = len(self.get_discoveries(k))
        return out

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

    def append_facts(self, facts: list[dict]) -> None:
        """🆕 v2.7.2 追加结构化 fact（来自 narrative_facts_extractor）

        Args:
            facts: list[NarrativeFact.to_dict()]

        规则：
        - 按 key 去重（相同 key 的 fact 替换旧的 + round 更新）
        - 容量上限 50 条（防 prompt 爆炸），超出时按 importance 淘汰
        """
        if not facts:
            return
        from history_footnote.narrative_facts_extractor import NarrativeFact
        existing_keys = {f.get("key", "") for f in self.narrative_facts if f.get("key")}
        for f in facts:
            fact = NarrativeFact.from_dict(f) if isinstance(f, dict) else f
            if not isinstance(fact, NarrativeFact):
                continue
            # 按 key 替换
            if fact.key and fact.key in existing_keys:
                for i, old in enumerate(self.narrative_facts):
                    if old.get("key") == fact.key:
                        self.narrative_facts[i] = fact.to_dict()
                        break
            else:
                self.narrative_facts.append(fact.to_dict())
                if fact.key:
                    existing_keys.add(fact.key)

        # 容量限制：按 importance + created_at 淘汰
        MAX_FACTS = 50
        if len(self.narrative_facts) > MAX_FACTS:
            self.narrative_facts.sort(key=lambda x: (-x.get("importance", 5), -x.get("created_at", 0)))
            self.narrative_facts = self.narrative_facts[:MAX_FACTS]

    def get_facts_for_prompt(self) -> list[dict]:
        """🆕 v2.7.2 拿要注入 prompt 的 fact 列表（按 importance 倒序）"""
        return sorted(
            self.narrative_facts,
            key=lambda x: (-x.get("importance", 5), -x.get("created_at", 0)),
        )

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
