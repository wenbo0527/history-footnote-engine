"""
location_service.py - 地点服务（v2.4 文字地图系统）

核心职责：
1. 从 era.json 读取 world.locations（地点库）
2. 计算移动的行动点消耗
3. 判断 heard/visited/unseen 状态
4. 决定时间模式（首次/熟悉/危险）
5. 检查 L2 地点解锁条件
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Location:
    """单个地点的运行时数据"""
    id: str
    name: str
    tier: str                # L1/L2/L3
    type: str                # family/public/work/neighbor/social/authority/service/education
    tone: str                # 文风基调
    description: str
    atmosphere_sound: str
    npcs_default: list
    neighbors: list
    events: list
    unlock_hooks: list = None  # L2/L3 才有


@dataclass
class MoveResult:
    """移动结果"""
    success: bool
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    ap_cost: float = 0
    time_mode: str = "now_time"  # 决定叙事字数
    reason: str = ""              # 失败原因


class LocationService:
    """地点服务：所有"我在哪 / 我去哪"的问题都走这里"""

    def __init__(self, era_config: dict):
        """
        Args:
            era_config: era.json 加载后的 dict
        """
        self.world = era_config.get("world", {})
        self.locations_cfg = self.world.get("locations", {})
        self.city_name = self.locations_cfg.get("city_name", "")
        self.city_intro = self.locations_cfg.get("city_intro", "")
        self.default_location = self.locations_cfg.get("default_location", "home")

        # 解析为 Location 对象（O(1) 查询）
        self._by_id: dict[str, Location] = {}
        for loc in self.locations_cfg.get("list", []):
            self._by_id[loc["id"]] = Location(
                id=loc["id"],
                name=loc["name"],
                tier=loc.get("tier", "L1"),
                type=loc.get("type", "public"),
                tone=loc.get("tone", ""),
                description=loc.get("description", ""),
                atmosphere_sound=loc.get("atmosphere_sound", ""),
                npcs_default=loc.get("npcs_default", []),
                neighbors=loc.get("neighbors", []),
                events=loc.get("events", []),
                unlock_hooks=loc.get("unlock_hooks", []),
            )

        # 🆕 v2.4.1 NPC 当前位置表（默认在 home）
        self.npc_locations: dict[str, dict] = self.locations_cfg.get("npc_locations", {})
        # 🆕 NPC 关系网
        self.npc_relationships: list[dict] = self.locations_cfg.get("npc_relationships", [])
        # 🆕 路遇事件表
        self.encounter_table: list[dict] = self.locations_cfg.get("encounter_table", [])

    # ============ 查询 ============

    def get(self, loc_id: str) -> Optional[Location]:
        return self._by_id.get(loc_id)

    def get_name(self, loc_id: str) -> str:
        loc = self.get(loc_id)
        return loc.name if loc else loc_id

    def all_l1_l2(self) -> list[Location]:
        """所有 L1 锚点 + 已解锁 L2 地点（用于地图展示）"""
        return [loc for loc in self._by_id.values() if loc.tier in ("L1", "L2")]

    def is_known(self, loc_id: str) -> bool:
        """L1 永远 known；L2/L3 需要解锁"""
        loc = self.get(loc_id)
        return loc is not None and loc.tier == "L1"

    def is_neighbor(self, from_id: str, to_id: str) -> bool:
        """to 是否是 from 的邻居（一步可达）"""
        loc = self.get(from_id)
        return loc is not None and to_id in loc.neighbors

    def get_default(self) -> str:
        return self.default_location

    # ============ 移动计算 ============

    def calc_move_ap(
        self,
        from_id: str,
        to_id: str,
        visited: list[str],
        action_type: str = "general",
    ) -> tuple[float, str]:
        """
        计算移动消耗的行动点 + 时间模式

        Returns:
            (ap_cost, time_mode)

        规则：
        - 熟悉地点（visited 包含 to_id）：1.0 AP
        - 陌生地点（首次去）：1.5 AP
        - 邻居加成：to 是 from 的邻居 = -0.2 AP（最多 0.5）
        - 危险动作（去 county_office 求情）：× 1.5
        """
        if from_id == to_id:
            return 0.0, "now_time"  # 原地不动不消耗

        base = 1.0
        # 陌生地点 = 首次去
        if to_id not in visited:
            base = 1.5
        # 邻居打折
        if self.is_neighbor(from_id, to_id):
            base = max(0.5, base - 0.2)
        # 危险动作加成
        if action_type == "danger":
            base *= 1.5

        # 时间模式：L1 锚点 + visited = 熟悉
        to_loc = self.get(to_id)
        is_familiar = to_id in visited or (to_loc and to_loc.tier == "L1")
        if is_familiar:
            time_mode = "now_time"  # 熟悉 = 简写
        else:
            time_mode = "slow_time"  # 首次去 = 详写

        return round(base, 1), time_mode

    def can_move(
        self,
        from_id: str,
        to_id: str,
        visited: list[str],
        heard: list[str],
        action_points: float,
        action_type: str = "general",
    ) -> MoveResult:
        """
        检查玩家能否从 from 移动到 to
        Returns:
            MoveResult
        """
        from_loc = self.get(from_id)
        to_loc = self.get(to_id)

        if not to_loc:
            return MoveResult(success=False, reason=f"地点 {to_id} 不存在")

        # 不可见检查：L1 永远可见，L2 需要 heard 触发，L3 需要剧情触发
        if to_loc.tier == "L1":
            pass  # OK
        elif to_loc.tier == "L2":
            if to_id not in heard and to_id not in visited:
                return MoveResult(
                    success=False,
                    to_location=to_id,
                    reason=f"你还没听说过这个地方（{to_loc.name}）",
                )
        elif to_loc.tier == "L3":
            if to_id not in heard and to_id not in visited:
                return MoveResult(
                    success=False,
                    to_location=to_id,
                    reason=f"这是个秘密地方（{to_loc.name}），没人提起过",
                )

        # 距离检查（可放宽：允许任何已 heard 地点）
        # 之前 v1 用 neighbors 严格限制，v2 放宽为"所有 heard 地点可去"
        # 因为 v1 阶段玩家没主动探索，不严格
        # v2 再收紧

        # AP 检查
        ap_cost, time_mode = self.calc_move_ap(from_id, to_id, visited, action_type)
        if action_points < ap_cost:
            return MoveResult(
                success=False,
                from_location=from_id,
                to_location=to_id,
                ap_cost=ap_cost,
                time_mode=time_mode,
                reason=f"行动点不够（需 {ap_cost}，剩 {action_points}）",
            )

        return MoveResult(
            success=True,
            from_location=from_id,
            to_location=to_id,
            ap_cost=ap_cost,
            time_mode=time_mode,
            reason="",
        )

    # ============ heard 解锁检查 ============

    def check_unlock_hooks(self, game_state) -> list[str]:
        """
        检查 L2/L3 地点的 unlock_hooks 是否满足
        Returns: 本次新解锁的 heard 地点列表
        """
        newly_heard: list[str] = []
        visited = list(game_state.visited_locations or [])
        visited_set = set(visited)
        already_heard = set(game_state.heard_locations or [])

        # 当前状态快照
        state_snapshot = {
            "round": getattr(game_state, "round_number", 0),
            "cash": getattr(game_state, "cash", 0),
            "rice": getattr(game_state, "rice", 0),
            "tooth_market_visit": visited.count("tooth_market"),
        }

        for loc in self._by_id.values():
            if loc.tier == "L1":
                continue
            if loc.id in visited_set or loc.id in already_heard:
                continue
            if not loc.unlock_hooks:
                continue

            for hook in loc.unlock_hooks:
                if self._eval_trigger(hook.get("trigger", ""), state_snapshot):
                    newly_heard.append(loc.id)
                    break

        return newly_heard

    def _eval_trigger(self, trigger: str, state: dict) -> bool:
        """
        简单 trigger 解析（v1 范围）
        支持：cash<1, round>=3, loans_total>=2, rice<3, tooth_market_visit>=2
        """
        if not trigger or trigger == "default":
            return False  # 默认 trigger 不算"自动解锁"

        try:
            # 简单表达式求值
            # 安全：只允许 [变量名] [比较] [数字] 的简单形式
            allowed = set("0123456789.<>=!")
            for c in trigger:
                if c.isalpha() or c == "_":
                    continue
                if c in allowed:
                    continue
                return False  # 包含不允许的字符
            # 用 eval，但 sandbox 通过字符白名单
            # 提取左值（变量名）
            for op in [">=", "<=", "!=", "==", ">", "<"]:
                if op in trigger:
                    left, right = trigger.split(op, 1)
                    left = left.strip()
                    right = right.strip()
                    val = state.get(left, 0)
                    try:
                        threshold = float(right)
                    except ValueError:
                        return False
                    if op == ">=":  return val >= threshold
                    if op == "<=":  return val <= threshold
                    if op == "!=":  return val != threshold
                    if op == "==":  return val == threshold
                    if op == ">":   return val > threshold
                    if op == "<":   return val < threshold
            return False
        except Exception:
            return False

    # ============ 移动提示生成 ============

    def get_move_options(
        self,
        from_id: str,
        visited: list[str],
        heard: list[str],
        action_points: float,
    ) -> list[dict]:
        """
        生成"移动选项"列表（给 voice_options 用）
        策略：当前 location 的 neighbors + heard 地点
        """
        options: list[dict] = []
        from_loc = self.get(from_id)
        if not from_loc:
            return options

        candidates = set(from_loc.neighbors) | set(heard) | set(visited)
        for to_id in candidates:
            if to_id == from_id:
                continue
            result = self.can_move(from_id, to_id, visited, heard, action_points)
            if not result.success:
                continue
            to_loc = self.get(to_id)
            options.append({
                "voice_id": f"move_{to_id}",
                "voice_name": f"去{to_loc.name}",
                "intent_text": to_loc.description,
                "is_move": True,
                "target_location": to_id,
                "ap_cost": result.ap_cost,
                "time_mode": result.time_mode,
                "value_dimension": None,
            })
        return options

    def build_prompt_context(
        self,
        current_loc_id: str,
        visited: list[str],
        heard: list[str],
    ) -> str:
        """
        构建 LLM prompt 注入的世界状态块
        """
        loc = self.get(current_loc_id)
        if not loc:
            return ""

        visited_names = [self.get_name(v) for v in visited if v != current_loc_id]
        heard_names = [self.get_name(h) for h in heard]

        lines = [
            f"# 当前世界：{self.city_name}",
            f"**当前位置**：{loc.name}（{loc.tier}，{loc.type}）",
            f"**地点基调**：{loc.tone}",
            f"**环境**：{loc.description}",
            f"**声响**：{loc.atmosphere_sound}",
            f"**该地熟人**：{'、'.join(loc.npcs_default) if loc.npcs_default else '（无）'}",
            f"**可移动到**：{'、'.join(self.get_name(n) for n in loc.neighbors)}",
        ]
        if visited_names:
            lines.append(f"**已去过**：{'、'.join(visited_names)}")
        if heard_names:
            lines.append(f"**听过没去过（❓）**：{'、'.join(heard_names)}")

        return "\n".join(lines)

    # ============ 🆕 v2.4.1 NPC 当前位置系统 ============

    def get_npc_location(self, npc_name: str) -> str | None:
        """查询 NPC 默认位置（玩家想找某 NPC 时）"""
        info = self.npc_locations.get(npc_name)
        if not info:
            return None
        return info.get("default") or info.get("home")

    def get_npcs_at(self, location_id: str) -> list[str]:
        """查询某地点的所有 NPC（默认 + 在此地 home 的）"""
        npcs = set()
        # 1) 地点本身的 npcs_default
        loc = self.get(location_id)
        if loc:
            for n in loc.npcs_default:
                npcs.add(n)
        # 2) 任何 NPC 的 home = 此地
        for npc_name, info in self.npc_locations.items():
            home = info.get("home")
            if home == location_id:
                npcs.add(npc_name)
        # 3) 任何 NPC 的 default = 此地
        for npc_name, info in self.npc_locations.items():
            if info.get("default") == location_id:
                npcs.add(npc_name)
        return sorted(npcs)

    def get_npc_relationships(self, npc_name: str | None = None) -> list[dict]:
        """查询 NPC 关系网（None=全部, str=涉及某 NPC 的）"""
        if npc_name is None:
            return list(self.npc_relationships)
        return [
            r for r in self.npc_relationships
            if r.get("from") == npc_name or r.get("to") == npc_name
        ]

    def build_npc_prompt_section(
        self,
        current_loc_id: str,
        max_relationships: int = 6,
    ) -> str:
        """
        构建 NPC 上下文段（注入到 LLM prompt）

        包含：
        - 当前位置的所有 NPC
        - 当前 NPC 涉及的关系（前 N 条）
        """
        loc_npcs = self.get_npcs_at(current_loc_id)
        if not loc_npcs:
            return ""

        lines = [f"## 🏠 该地 NPC（{current_loc_id}）"]
        lines.append(f"**当前在 {self.get_name(current_loc_id)} 的人**：{'、'.join(loc_npcs)}")

        # 当前 NPC 涉及的关系
        all_rels: list[dict] = []
        for n in loc_npcs:
            for r in self.get_npc_relationships(n):
                # 只显示"本地点相关的另一方"的关系
                other = r.get("to") if r.get("from") == n else r.get("from")
                all_rels.append({**r, "current": n, "other": other})

        # 去重
        seen = set()
        unique_rels = []
        for r in all_rels:
            key = (r.get("from"), r.get("to"))
            if key not in seen:
                seen.add(key)
                unique_rels.append(r)

        if unique_rels:
            lines.append(f"**涉及关系**（最多 {max_relationships} 条）：")
            for r in unique_rels[:max_relationships]:
                lines.append(
                    f"- {r['from']} ↔ {r['to']}（{r.get('type', '')}）：{r.get('description', '')}"
                )

        return "\n".join(lines)

    # ============ 🆕 v2.4.1 路遇事件系统 ============

    def roll_encounter(self, from_id: str, to_id: str) -> dict | None:
        """
        投掷"路遇"事件：从 from → to 的移动可能触发的 NPC 偶遇

        Returns:
            None 或 {npc, event, probability}
        """
        import random
        candidates = [
            e for e in self.encounter_table
            if e.get("from") == from_id and e.get("to") == to_id
        ]
        if not candidates:
            return None
        # 加权随机（按 probability）
        weights = [e.get("probability", 0.1) for e in candidates]
        chosen = random.choices(candidates, weights=weights, k=1)[0]
        # 再掷一次看是否真的触发（用 probability）
        if random.random() > chosen.get("probability", 0.1):
            return None
        return chosen

    def build_encounter_narrative(self, encounter: dict) -> str:
        """生成"路遇"叙事（30-80 字，节省 token）"""
        npc = encounter.get("npc", "")
        event = encounter.get("event", "")
        return f"路上你碰见了 {npc}。{event}。"


# ============ 工厂函数 ============

def build_location_service(era_config: dict) -> LocationService:
    return LocationService(era_config)
