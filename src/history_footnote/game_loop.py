"""游戏主循环——9步执行流程

设计参考：设计文档v1.0.md 第7.2节"游戏主循环" + 第七章"存档与重开机制设计"

主循环步骤：
1. 获取玩家输入
2. 输入预处理（截断过长输入、识别元指令）
3. 规则引擎：确定性预计算（行动边界、强制事件、触发、节奏、insight候选、settle）
4. 多路召回（最近3回合+关键词+关联+因果）
5. DM Agent：一次API调用 + 多轮Tool Calling
6. 后校验（叙事兜底）
7. 应用变量变更（含合理性校验）
8. 保存事件到记忆
9. 呈现给玩家

存档集成：
- 每回合结束自动存档到 auto.json
- /save [slot] 手动存档
- /load <slot> 读档
- /state 查看状态
- /quit 退出
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from history_footnote.dm_agent import DMAgent
from history_footnote.game_memory import GameEvent, GameMemory
from history_footnote.game_state import GameState, make_initial_state
from history_footnote.knowledge_base import KnowledgeBase
from history_footnote.rule_engine import RuleEngine
from history_footnote.storage.save_manager import (
    SaveManager,
    SaveSession,
    DEFAULT_SAVE_ROOT,
)

logger = logging.getLogger(__name__)


# 元指令
META_COMMANDS = {"/save", "/load", "/state", "/help", "/quit", "/exit", "/restart"}


class GameLoop:
    """游戏主循环"""

    def __init__(
        self,
        era_id: str,
        era_config: dict,
        llm_model: Any,
        save_manager: SaveManager | None = None,
        session: SaveSession | None = None,
        load_state_data: dict | None = None,
        selected_identity: str = "",
        custom_character: dict | None = None,  # 🐛 v1.5.1 P0 Bug #1 修复
    ):
        """初始化游戏循环

        Args:
            era_id: 时代包ID
            era_config: 时代包配置
            llm_model: LLM模型
            save_manager: 存档管理器（默认创建）
            session: 已存在的session（继续游戏时）
            load_state_data: 要加载的存档数据（dict）
            selected_identity: 选中的身份id（v1.1+多身份支持）
            custom_character: 🆕 玩家在 8 步向导中由 LLM 生成的人设
        """
        self.era_id = era_id
        self.era_config = era_config
        self.llm = llm_model

        # 解析身份（如果没传，从era_config取默认）
        if not selected_identity:
            selected_identity = era_config.get("world", {}).get("default_identity", "")
        self.selected_identity = selected_identity

        # 🐛 v1.5.1 P0 Bug #1 修复：把 custom_character 存到 state
        if custom_character:
            # 在 make_initial_state 之后会赋值给 self.state.custom_character
            self._pending_custom_character = custom_character
        else:
            self._pending_custom_character = None

        # 解析对应的identity配置
        identities = era_config.get("world", {}).get("player_identities", {})
        self.identity_config = identities.get(selected_identity, {})

        # 初始化SaveManager
        self.save_manager = save_manager or SaveManager(DEFAULT_SAVE_ROOT)

        # 决定使用哪个session
        if session is None:
            # 创建新session
            self.session = self.save_manager.create_session(era_id)
        else:
            self.session = session

        # 初始化state
        if load_state_data is not None:
            # 从存档恢复
            state_kwargs = self.save_manager.make_initial_state_from_load(
                era_config, load_state_data
            )
            self.state = GameState(**state_kwargs)
            # selected_identity从存档恢复
            self.selected_identity = self.state.selected_identity or selected_identity
            self.identity_config = identities.get(self.selected_identity, {})
        else:
            # 新建state
            self.state = make_initial_state(era_id, era_config, selected_identity=selected_identity)
            # 如果有session，绑定session_id
            self.state.session_id = self.session.session_id
            # 🐛 v1.5.1 P0 Bug #1 修复：注入 custom_character
            if hasattr(self, '_pending_custom_character') and self._pending_custom_character:
                self.state.custom_character = self._pending_custom_character

        # 初始化组件
        self.rule_engine = RuleEngine(era_config)
        self.memory = GameMemory(save_dir=self.session.dir_path)
        # 从存档恢复记忆
        if load_state_data is not None and "event_log" in load_state_data:
            for ev_dict in load_state_data.get("event_log", []):
                self.memory.save_event(GameEvent.from_dict(ev_dict))

        self.knowledge_base = KnowledgeBase(
            entries=era_config.get("knowledge", {}).get("entries", []),
            snippets=era_config.get("knowledge", {}).get("narrative_snippets", []),
            story_segments=era_config.get("knowledge", {}).get("story_segments", {}),
        )

        # 初始化DM Agent
        self.dm = DMAgent(
            era_config=era_config,
            state=self.state,
            rule_engine=self.rule_engine,
            memory=self.memory,
            knowledge_base=self.knowledge_base,
            llm_model=llm_model,
        )

        # 初始化DiceEngine（v1.2+：DND式随机判定）
        from history_footnote.dice_engine import DiceEngine
        self.dice = DiceEngine()

        # 初始化随机事件表（v1.2+）
        self.random_events = era_config.get("world", {}).get("random_events", [])

        # 当前待处理的身份切换offer（None=无offer）
        self.pending_identity_offer: dict | None = None

        # 注入identity_switch_offers到DM系统prompt
        self._inject_identity_switch_offers()

    def _inject_identity_switch_offers(self) -> None:
        """把identity_switch_offers注入到DM的LLM state_ref中

        这样DM在每次Tool调用时都能感知到当前可用的offer选项。
        """
        offers = self.era_config.get("world", {}).get("identity_switch_offers", [])
        if not offers:
            return

        # 找到当前身份可用的offers
        available = [o for o in offers if o.get("from_identity") == self.selected_identity]
        if not available:
            return

        # 注入到 llm state_ref（通过 DM Agent）
        if hasattr(self.dm, "llm") and hasattr(self.dm.llm, "_state_ref_slot_ref"):
            current_ref = self.dm.llm._state_ref_slot_ref[0]
            current_ref["identity_switch_offers"] = available

    def run(self) -> None:
        """启动游戏主循环"""
        # 注入background知识（游戏开始时）
        self._inject_background_knowledge()

        # 打印开场白
        self._print_opening()

        # 主循环
        while not self._is_game_over():
            try:
                player_input = self._get_player_input()
                if not player_input:
                    continue

                # 处理元指令
                if player_input.startswith("/"):
                    if self._handle_meta_command(player_input):
                        continue
                    else:
                        print("[ERROR] 未知元指令，输入 /help 查看")
                        continue

                # 执行一回合
                self._run_round(player_input)

            except KeyboardInterrupt:
                print("\n[INFO] 游戏已暂停。输入 /quit 退出，/save 保存。")
                continue
            except SystemExit:
                # /quit 触发 SystemExit，向上抛出
                raise
            except Exception as e:
                logger.exception("回合执行异常")
                print(f"[ERROR] 系统异常: {e}。继续下一回合。")

    def _run_round(self, player_input: str) -> None:
        """执行一回合游戏"""
        # === 步骤2：输入预处理 ===
        player_input = self._preprocess_input(player_input)

        # === 步骤3：规则引擎预计算 ===
        view = self.rule_engine.make_view(self.state)
        action_check = self.rule_engine.check_action(view, player_input)
        forced_events = self.rule_engine.check_forced_events(view)
        triggered_rules = self.rule_engine.check_triggers(view)
        pacing_directives = self.rule_engine.check_pacing(view)

        # 玩家输入的insight候选
        self.state._last_player_input = player_input
        insight_candidates = self.rule_engine.check_insights(view, player_input)

        # 每回合自动结算
        settlements = self.rule_engine.settle_round(view)

        # === 步骤4：多路召回 ===
        recent_events = self.memory.get_recent(rounds=3, current_round=self.state.round_number)

        # === 步骤4.5：v1.2+ 随机事件触发（DND式随机判定）===
        current_scene = self.knowledge_base.detect_scene(player_input)
        triggered_events = self._check_random_events(current_scene)
        if triggered_events:
            # 应用事件效果（更新state.variables）
            effect_messages = self._apply_event_effects(triggered_events)
            # 注入到DM的LLM state_ref
            self.set_random_events_for_dm(triggered_events)
            # 显示给玩家
            print(f"\n[随机事件]")
            for ev in triggered_events:
                print(f"  🎲 {ev['outcome'].get('description', '')}")
                if ev['outcome'].get('hint'):
                    print(f"     （{ev['outcome']['hint']}）")
            for msg in effect_messages:
                print(msg)

        # === 步骤5：DM Agent生成叙事 ===
        # 处理行动边界：如果是越界行动，先告知DM
        if not action_check.get("allowed", True):
            print(f"\n[系统] {action_check.get('reason', '行动被拒绝')}")

        # 🆕 v1.6+ 并发支持：LLM 调用受 LLM_THROTTLE 保护
        from history_footnote.concurrency import LLM_THROTTLE
        try:
            with LLM_THROTTLE:
                dm_response = self.dm.run(player_input)
        except TimeoutError:
            print("[⚠️ LLM 限流] 等待 LLM 许可超时，使用兜底叙事")
            dm_response = generate_safe_narrative(
                state={
                    "triggered_events": sorted(self.state.triggered_events),
                    "current_date": self.state.current_date,
                    "round_number": self.state.round_number,
                },
                era_config=self.era_config,
            )

        # v1.2+：处理DM发起的身份切换offer
        identity_offer = dm_response.get("identity_offer")
        if identity_offer:
            self.set_pending_offer(identity_offer)

        # === 步骤5.5：🆕 v1.6+ P0 后校验 + 重试 ===
        MAX_RETRY = 2
        from history_footnote.post_validator import post_validate, generate_safe_narrative
        state_dict = {
            "triggered_events": sorted(self.state.triggered_events),
            "current_date": self.state.current_date,
            "round_number": self.state.round_number,
            "selected_identity": self.state.selected_identity,
        }
        validation = post_validate(
            dm_response=dm_response,
            state=state_dict,
            era_config=self.era_config,
            player_input=player_input,
        )
        retry_count = 0
        while not validation.valid and retry_count < MAX_RETRY:
            print(f"\n[⚠️ 后校验] 发现 {len(validation.errors)} 个 error 级别问题，重试中（第 {retry_count + 1}/{MAX_RETRY} 次）...")
            for issue in validation.errors[:3]:  # 打印前 3 个
                print(f"  - [{issue.layer}/{issue.severity}] {issue.message}")
            retry_count += 1
            try:
                # 🆕 v1.6+ 并发：重试也受 LLM_THROTTLE 保护
                with LLM_THROTTLE:
                    dm_response = self.dm.regenerate(
                        player_input=player_input,
                        validation_issues=[asdict(i) for i in validation.issues],
                        prev_narrative=dm_response.get("narrative", ""),
                    )
                # 重新校验
                validation = post_validate(
                    dm_response=dm_response,
                    state=state_dict,
                    era_config=self.era_config,
                    player_input=player_input,
                )
            except (TimeoutError, Exception) as e:
                print(f"[⚠️ 重试异常] {e}，切换到安全兜底")
                break

        if not validation.valid:
            # 2 次重试仍失败 → 安全兜底
            print(f"[⚠️ 后校验] 重试 {MAX_RETRY} 次仍失败，使用安全兜底叙事")
            dm_response = generate_safe_narrative(
                state=state_dict,
                era_config=self.era_config,
                failed_response=dm_response,
            )

        # === 步骤6：后校验（Phase 1简化版） ===
        narrative = self._validate_narrative(dm_response.get("narrative", ""))

        # === 步骤7：应用变量变更 ===
        applied = self.rule_engine.apply_changes(view, dm_response.get("state_changes", {}))

        # 应用updates
        self.rule_engine.apply_updates(view, dm_response.get("updates"))

        # 记录已触发的强制事件
        for fe in forced_events:
            if fe.event_id not in self.state.triggered_events:
                self.state.triggered_events.append(fe.event_id)

        # === 步骤8：保存事件到记忆 ===
        for summary in dm_response.get("events_to_save", []):
            event = GameEvent(
                round=self.state.round_number,
                type="dm_narrative",
                summary=summary,
                player_action=player_input,
                affected_variables=dm_response.get("state_changes", {}),
            )
            self.memory.save_event(event)

        # 同步event_log到state（用于存档）
        self.state.event_log = [
            e.to_dict() for e in self.memory.events
        ]

        # 记录到state的narrative_history
        event_summary = dm_response.get("events_to_save", ["日常"])[0] if dm_response.get("events_to_save") else "日常"
        self.state.append_narrative(
            self.state.round_number,
            narrative,
            event_summary,
        )

        # 🐛 v1.5.1 P1 Issue 5 修复：持久化 voice_options（供存档/前端复用）
        # 🆕 v1.6.9 P0 修复：当 LLM 把选项写进 narrative 而未通过 voice_options 返回时，
        # 自动从 narrative 文本提取"一、二、三"等内嵌选项
        structured_voice_options = dm_response.get("voice_options", [])
        if not structured_voice_options and narrative:
            from history_footnote.narrative_sanitizer import merge_voice_options
            structured_voice_options = merge_voice_options(None, narrative)
            if structured_voice_options:
                logger.info(
                    f"[v1.6.9] inline options extracted: {len(structured_voice_options)} 个"
                )
        self.state.last_voice_options = structured_voice_options

        # === 步骤9：呈现给玩家 ===
        # 先回显玩家输入（明确告知"这是你做的事"）
        print(f"\n> {player_input}")
        self._display_narrative(narrative)
        self._display_state()

        # 调整后的变量变更提示
        if applied.get("adjusted"):
            print("\n[系统] 部分变量变化被自动调整（超过单回合上限）：")
            for var_id, info in applied["adjusted"].items():
                print(f"  - {var_id}: 请求{info['requested']:+.0f} → 实际{info['actual']:+.0f} ({info['reason']})")

        # === v1.3+ 行动点系统：行动点耗尽才跳月 ===
        is_action = dm_response.get("is_action", True)
        time_cost = int(dm_response.get("time_cost", 1))
        intent_type = dm_response.get("intent_type", "action")  # 🆕 v1.5+
        voice_options = dm_response.get("voice_options", [])  # 🆕 v1.5+

        # 🆕 v1.5+：打印 voice_options（DE 风格）
        if voice_options:
            print(f"\n[🎭 你脑海中的声音]")
            for i, opt in enumerate(voice_options, 1):
                vname = opt.get("voice_name", "?")
                itext = opt.get("intent_text", "?")
                print(f"  {i}. 【{vname}】{itext}")
            print(f"  {len(voice_options)+1}. 自由输入（输入任何行动）")

        # 🆕 v1.5+：根据 intent_type 区分展示
        if is_action and time_cost > 0:
            # 真行动：消耗行动点
            ap_result = self.state.consume_action_points(time_cost)
            print(f"\n[⚡ 行动] 消耗 {ap_result['consumed']} 点 | 剩余 {ap_result['remaining']}/{self.state.action_points_max}")
            if ap_result["month_advanced"]:
                print(f"  ━━━ 行动点耗尽，进入 {ap_result['new_date']} ━━━")
                # 月推进
                self._update_idle_counter(player_input)
                self.rule_engine.advance_round(view)
        elif intent_type == "describe":
            # 🆕 v1.5+：玩家描述身份/环境/性格 → 不消耗行动点
            print(f"\n[🪞 描述] 你在描述自己的身份/处境 → 不消耗行动点 | 剩余 {self.state.action_points_current}/{self.state.action_points_max}")
        elif not is_action:
            # 问询/观察：不消耗行动点
            print(f"\n[💬 问询] 本次不消耗行动点 | 剩余 {self.state.action_points_current}/{self.state.action_points_max}")
        else:
            # is_action=true 但 time_cost=0：边界情况
            print(f"\n[⏱️ 行动点] 本次行动未消耗时间 | 剩余 {self.state.action_points_current}/{self.state.action_points_max}")

        # === 自动存档 ===
        # 🐛 Issue #9 修复：把 dm_agent state_ref 的 8 SKILL 字段同步到 GameState
        # 这样存档能持久化 recent_scenes/recent_inputs/route_tendency
        if hasattr(self.dm, 'graph') and hasattr(self.dm, '_last_state_ref'):
            last_state_ref = getattr(self.dm, '_last_state_ref', None) or {}
            self.state.recent_scenes = list(last_state_ref.get("recent_scenes", self.state.recent_scenes))
            self.state.recent_inputs = list(last_state_ref.get("recent_inputs", self.state.recent_inputs))
            self.state.route_tendency = last_state_ref.get("route_tendency", self.state.route_tendency)
            self.state.failure_type = last_state_ref.get("failure_type", self.state.failure_type)

        self._auto_save()

    # === 辅助方法 ===

    def _preprocess_input(self, text: str) -> str:
        """输入预处理：截断过长输入"""
        max_len = 200
        if len(text) > max_len:
            return text[:max_len] + "…"
        return text.strip()

    def _validate_narrative(self, narrative: str) -> str:
        """后校验：Phase 1简化版——确保叙事非空

        🆕 v1.6.7 架构重构：清洗逻辑在 dm_agent.extract_narrative_node 已完成
        这里只做兜底空值检查。
        """
        if not narrative or not narrative.strip():
            return "时间流逝。一切如常。"
        return narrative

    def _update_idle_counter(self, player_input: str) -> None:
        """更新玩家空闲轮数"""
        # 简化：任何非元输入都算"有行动"
        if player_input and not player_input.startswith("/"):
            self.state.player_idle_rounds = 0
        else:
            self.state.player_idle_rounds += 1

    def _is_game_over(self) -> bool:
        """判断游戏是否结束"""
        timeline = self.era_config.get("world", {}).get("timeline", {})
        total = timeline.get("total_rounds", 50)
        return self.state.round_number > total

    def _inject_background_knowledge(self) -> None:
        """注入background知识（Phase 1只打印提示）"""
        bg = self.knowledge_base.get_background()
        logger.info(f"已加载{len(bg)}条background知识")

    def _print_opening(self) -> None:
        """打印开场白——根据身份动态变化

        v1.5.1+：如果 state.custom_character 存在（玩家在 8 步向导中由 LLM 生成的人设），
        优先使用人设的开场白。
        """
        era_name = self.era_config.get("era_name", "")
        gender_label = "♂" if self.state.player_gender == "male" else "♀" if self.state.player_gender == "female" else ""
        label = self.identity_config.get("label", "小人物")
        role = self.identity_config.get("role", "小人物")
        description = self.identity_config.get("description", "你是这个时代的一个小人物。")

        # 🐛 v1.5.1 P0 Bug #1 修复：优先用 custom_character
        cc = getattr(self.state, "custom_character", None)
        if cc and (cc.get("opening_paragraph") or cc.get("background") or cc.get("name")):
            print(f"\n{'=' * 60}")
            print(f"欢迎来到【{era_name}】 {gender_label}")
            print(f"\n你是 {cc.get('name', '?')} — {cc.get('hometown', '盛泽镇')}")
            if cc.get('family'):
                family_str = ' / '.join([f"{k}: {v}" for k, v in list(cc.get('family', {}).items())[:3]])
                if family_str:
                    print(f"家庭：{family_str}")
            if cc.get('background'):
                print(f"\n【来历】{cc['background']}")
            if cc.get('starting_situation'):
                print(f"\n【开局处境】{cc['starting_situation']}")
            if cc.get('opening_paragraph'):
                print(f"\n{cc['opening_paragraph']}")
            print(f"\n日期：{self.state.current_date}")
            print(f"{'=' * 60}\n")
            return

        # 优先从dm_persona.md的开场白部分读（但只在身份为默认男性时使用）
        from pathlib import Path
        is_default_identity = self.selected_identity == self.era_config.get("world", {}).get("default_identity", "")

        # 动态identity开场白（当不是默认男性身份时）
        if not is_default_identity or not self._has_persona_opening():
            print(f"\n{'=' * 60}")
            print(f"欢迎来到【{era_name}】 {gender_label}")
            print(f"\n你选择成为：{label}")
            print(f"你的身份：{role}")
            print(f"\n{description}")
            print(f"\n日期：{self.state.current_date}")
            print(f"{'=' * 60}\n")
        else:
            # 默认男性身份 + 有persona.md → 用persona的开场白
            opening = self._get_persona_opening()
            print(f"\n{'=' * 60}")
            print(opening)
            print(f"{'=' * 60}\n")

    def _has_persona_opening(self) -> bool:
        """检查dm_persona.md是否有开场白"""
        from pathlib import Path
        persona_path = Path("eras") / self.era_id / "dm_persona.md"
        if not persona_path.exists():
            return False
        text = persona_path.read_text(encoding="utf-8")
        return "# 开场白" in text

    def _get_persona_opening(self) -> str | None:
        """从dm_persona.md提取开场白"""
        from pathlib import Path
        persona_path = Path("eras") / self.era_id / "dm_persona.md"
        if not persona_path.exists():
            return None
        text = persona_path.read_text(encoding="utf-8")
        if "# 开场白" in text:
            start = text.find("# 开场白") + len("# 开场白")
            end = text.find("\n# ", start)
            if end == -1:
                end = len(text)
            return text[start:end].strip()
        return None

    def _get_player_input(self) -> str:
        """获取玩家输入"""
        try:
            ap_cur = self.state.action_points_current
            ap_max = self.state.action_points_max
            ap_bar = "●" * ap_cur + "○" * (ap_max - ap_cur)
            return input(f"\n[第{self.state.round_number}回合 {self.state.current_date}] 行动点 {ap_bar} {ap_cur}/{ap_max} > ")
        except EOFError:
            return "/quit"

    def _display_narrative(self, narrative: str) -> None:
        """展示叙事"""
        print(f"\n【DM叙事】\n{narrative}")

    def _display_state(self) -> None:
        """展示状态"""
        visible = self.state.get_visible_state()
        ap_cur = visible.get('action_points_current', 0)
        ap_max = visible.get('action_points_max', 3)
        ap_bar = "●" * ap_cur + "○" * (ap_max - ap_cur)
        print(f"\n[状态] 回合{visible['round']} | {visible['date']} | 行动点 {ap_bar} {ap_cur}/{ap_max} | 已解锁认知{visible['unlocked_insights_count']}个")

    def _handle_meta_command(self, cmd: str) -> bool:
        """处理元指令"""
        parts = cmd.strip().split()
        cmd_name = parts[0].lower()
        args = parts[1:]

        if cmd_name in ("/quit", "/exit"):
            print("[INFO] 游戏结束。")
            raise SystemExit(0)
        elif cmd_name == "/help":
            print(self._help_text())
            return True
        elif cmd_name == "/state":
            self._display_full_state()
            return True
        elif cmd_name == "/save":
            slot = args[0] if args else "default"
            self._save_to_slot(slot)
            return True
        elif cmd_name == "/load":
            slot = args[0] if args else "auto"
            return self._load_from_slot(slot)
        elif cmd_name == "/accept":
            return self._handle_identity_decision(accept=True)
        elif cmd_name == "/decline":
            return self._handle_identity_decision(accept=False)
        elif cmd_name == "/offers":
            self._show_available_offers()
            return True
        else:
            return False

    def _save_to_slot(self, slot: str) -> None:
        """保存到指定slot

        slot支持：
        - "default" / 不传 → 存到 slot1（首次手动存档）
        - "1" / "2" / "3" → 存到 slot1/slot2/slot3
        - "auto" → 存到 auto（一般不手动）
        """
        if slot == "default":
            # 找第一个空的slot，否则覆盖slot1
            target = "slot1"
            if self.session.slots.get("slot1") is None:
                target = "slot1"
            else:
                target = "slot1"  # 默认覆盖slot1
        elif slot in ("1", "slot1"):
            target = "slot1"
        elif slot in ("2", "slot2"):
            target = "slot2"
        elif slot in ("3", "slot3"):
            target = "slot3"
        elif slot == "auto":
            target = "auto"
        else:
            print(f"[ERROR] 非法slot名: {slot}（支持 1/2/3/auto）")
            return

        # 构造state_data
        state_data = self.state.to_dict()
        # 同步event_log
        state_data["event_log"] = [e.to_dict() for e in self.memory.events]
        # 摘要
        summary = f"第{self.state.round_number}回合 {self.state.current_date}"
        if self.state.event_log:
            summary += f" - {self.state.event_log[-1].get('summary', '')[:30]}"

        slot_info = self.save_manager.save_state(self.session, target, state_data, summary)
        print(f"[INFO] 已存档到 {target}（回合{slot_info.round_number} {slot_info.current_date}）")

    def _load_from_slot(self, slot: str) -> bool:
        """从指定slot读档

        Returns:
            True=成功读档（需要重启游戏循环）
            False=失败
        """
        if slot in ("1", "slot1"):
            target = "slot1"
        elif slot in ("2", "slot2"):
            target = "slot2"
        elif slot in ("3", "slot3"):
            target = "slot3"
        elif slot in ("auto", "default"):
            target = "auto"
        else:
            print(f"[ERROR] 非法slot名: {slot}")
            return False

        if target not in self.session.slots:
            print(f"[ERROR] {target} 没有存档")
            return False

        loaded = self.save_manager.load_state(self.session, target)
        if not loaded:
            print(f"[ERROR] 读取{target}失败")
            return False

        print(f"[INFO] 从 {target} 读档成功（回合{loaded.get('round_number')} {loaded.get('current_date')}）")
        print("[INFO] 读档需要重启游戏，请在外部重新运行：")
        print(f"       python -m history_footnote load {self.session.session_id} --slot {target}")
        return True

    def _auto_save(self) -> None:
        """每回合自动存档到auto.json"""
        state_data = self.state.to_dict()
        state_data["event_log"] = [e.to_dict() for e in self.memory.events]
        self.save_manager.save_state(
            self.session,
            "auto",
            state_data,
            summary=f"自动存档 - 回合{self.state.round_number}",
        )

    # === 随机事件机制（v1.2+ DND化） ===

    def _check_random_events(self, scene: str) -> list[dict]:
        """检查并触发随机事件

        Args:
            scene: 当前场景名

        Returns:
            触发的随机事件列表（包含dice结果、效果等）
        """
        triggered = []
        for event in self.random_events:
            cond = event.get("trigger_condition", {})

            # 场景匹配
            if cond.get("scene") and cond.get("scene") != scene:
                continue

            # 回合数
            if self.state.round_number < cond.get("min_round", 1):
                continue

            # 概率判定
            if not self.dice.chance(event.get("probability", 0)):
                continue

            # 触发：加权选一个outcome
            outcomes = event.get("outcomes", [])
            if not outcomes:
                continue

            chosen = self.dice.weighted_choice(outcomes)

            # 如果outcome需要dice判定
            if chosen.get("requires_dice"):
                dice_expr = chosen.get("dice", "d20")
                dc = chosen.get("dc", 10)
                check_result = self.dice.check(dc, dice_expr, purpose=chosen.get("description", ""))
                chosen["dice_result"] = check_result

            triggered.append({
                "event_id": event["id"],
                "outcome": chosen,
            })

        return triggered

    def _apply_event_effects(self, triggered_events: list[dict]) -> list[str]:
        """应用随机事件的效果（更新state.variables）

        Returns:
            事件效果描述列表（用于打印给玩家）
        """
        messages = []
        for ev in triggered_events:
            outcome = ev["outcome"]
            effect = outcome.get("effect", {})
            for var_key, delta in effect.items():
                # 解析"+0.5" "-0.3"
                if isinstance(delta, str):
                    if delta.startswith("+"):
                        delta = float(delta[1:])
                    elif delta.startswith("-"):
                        delta = -float(delta[1:])
                if var_key in self.state.variables:
                    self.state.variables[var_key] += delta
                    messages.append(f"  [随机事件效果] {var_key} {delta:+.1f}")

            # 如果是dice判定
            if "dice_result" in outcome:
                dice_res = outcome["dice_result"]
                roll = dice_res["result"]
                crit = " 💥大成功" if roll.is_critical_success else (" 💀大失败" if roll.is_critical_fail else "")
                if dice_res["success"]:
                    messages.append(f"  [判定] {roll}{crit} vs DC{dice_res['dc']} → 成功！{outcome.get('success', '')}")
                else:
                    messages.append(f"  [判定] {roll}{crit} vs DC{dice_res['dc']} → 失败。{outcome.get('fail', '')}")

        return messages

    def set_random_events_for_dm(self, triggered: list[dict]) -> None:
        """把随机事件结果注入到DM Agent的LLM state_ref

        DM在生成叙事时可以读到这些事件，把它们融入故事。
        """
        if not triggered:
            return
        if hasattr(self.dm.llm, "_state_ref_slot_ref"):
            current_ref = self.dm.llm._state_ref_slot_ref[0]
            current_ref["random_events"] = triggered

    # === 身份切换机制 ===

    def _handle_identity_decision(self, accept: bool) -> bool:
        """处理/accept或/decline

        DM通过Tool发起的offer存在self.pending_identity_offer
        """
        if self.pending_identity_offer is None:
            print("[INFO] 当前没有待处理的身份切换offer")
            return True

        if accept:
            self._apply_identity_switch(self.pending_identity_offer)
        else:
            print(f"[INFO] 你拒绝了身份切换offer：{self.pending_identity_offer.get('to_label', '新身份')}")
            print("  继续当前身份的游戏。")
            self.pending_identity_offer = None
        return True

    def _apply_identity_switch(self, offer: dict) -> None:
        """应用身份切换——更新state、identity_config、DM Agent

        Args:
            offer: offer_identity_switch的返回值
        """
        to_identity = offer.get("to_identity")
        if not to_identity:
            print("[ERROR] offer缺少to_identity")
            return

        # 1. 更新state
        old_identity = self.selected_identity
        self.state.selected_identity = to_identity
        # player_gender不变（性别锁定）
        # self.state.player_gender保持

        # 2. 更新GameLoop的identity_config
        identities = self.era_config.get("world", {}).get("player_identities", {})
        self.selected_identity = to_identity
        self.identity_config = identities.get(to_identity, {})

        # 3. 重新注入offers（新身份可能有新offer）
        self._inject_identity_switch_offers()

        # 4. 记录到事件日志
        summary = f"身份切换：{old_identity} → {to_identity}（{offer.get('reason', '')}）"
        event = GameEvent(
            round=self.state.round_number,
            type="identity_switch",
            summary=summary,
            metadata={
                "from": old_identity,
                "to": to_identity,
                "cost": offer.get("cost", ""),
                "benefit": offer.get("benefit", ""),
            },
        )
        self.memory.save_event(event)

        # 5. 显示反馈
        to_label = self.identity_config.get("label", to_identity)
        print(f"\n{'=' * 60}")
        print(f"🎭 身份已切换：{identities.get(old_identity, {}).get('label', old_identity)} → {to_label}")
        print(f"{'=' * 60}")
        new_role = self.identity_config.get("role", "")
        new_desc = self.identity_config.get("description", "")
        print(f"\n新身份：{new_role}")
        print(f"\n{new_desc[:200]}...")

        # 6. 清除pending offer
        self.pending_identity_offer = None

    def _show_available_offers(self) -> None:
        """显示所有可用的身份切换offer（不依赖DM）"""
        offers = self.era_config.get("world", {}).get("identity_switch_offers", [])
        available = [o for o in offers if o.get("from_identity") == self.selected_identity]
        if not available:
            print("[INFO] 当前身份暂无可用的身份切换选项")
            return

        print(f"\n=== 当前身份可用的切换选项 ===\n")
        for i, o in enumerate(available, 1):
            print(f"  {i}. {o.get('id')}")
            print(f"     目标身份: {o.get('to_identity')}")
            cond = o.get("trigger_condition", {})
            cond_str = ", ".join(f"{k}={v}" for k, v in cond.items())
            print(f"     触发条件: {cond_str}")
            print(f"     代价: {o.get('cost_description', '')}")
            print(f"     收益: {o.get('benefit_description', '')}")
            print()

    def set_pending_offer(self, offer: dict) -> None:
        """设置待处理的offer（DM Agent通过Tool调用）"""
        if offer.get("offered"):
            self.pending_identity_offer = offer
            print(f"\n{'─' * 60}")
            print(f"[OFFER] {offer.get('message', '身份切换')}")
            print(f"  目标: {offer.get('to_label', offer.get('to_identity'))}")
            print(f"  原因: {offer.get('reason', '')}")
            print(f"  代价: {offer.get('cost', '')}")
            print(f"  收益: {offer.get('benefit', '')}")
            print(f"\n  接受请输入 /accept")
            print(f"  拒绝请输入 /decline")
            print(f"{'─' * 60}\n")

    def _display_full_state(self) -> None:
        """展示完整状态"""
        print(f"\n{'=' * 40}")
        print(f"会话: {self.session.session_id}")
        print(f"回合: {self.state.round_number} | 日期: {self.state.current_date}")
        print(f"{'=' * 40}")
        print("\n变量:")
        for k, v in self.state.variables.items():
            print(f"  {k}: {v:.1f}")
        print(f"\n已触发事件: {len(self.state.triggered_events)}")
        print(f"已解锁认知: {self.state.unlocked_insights}")
        print(f"NPC关系: {self.state.npc_levels}")
        print(f"价值观: {self.state.value_shifts}")
        print(f"事件日志: {self.memory.count()}条")
        print(f"\n存档:")
        for name, slot in self.session.slots.items():
            print(f"  {name}: 回合{slot.round_number} {slot.current_date}")
        print(f"{'=' * 40}\n")

    @staticmethod
    def _help_text() -> str:
        return """
可用元指令：
  /state         - 查看完整游戏状态
  /save [1|2|3]  - 保存到slot1/2/3（不传则存slot1）
  /load [1|2|3|auto] - 从指定slot读档
  /quit          - 退出游戏
  /help          - 显示帮助

游戏玩法：
  直接输入你想做的任何事（去牙行、问税收、织丝绸等）
  DM会根据时代背景和你的行动生成叙事

存档机制：
  - 每回合结束自动存档（auto.json）
  - 手动存档有3个slot（slot1/2/3.json）
  - 重新游戏用：python -m history_footnote continue
  - 列出存档：python -m history_footnote list-saves
"""
