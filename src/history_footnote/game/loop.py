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
# 🆕 v2.10.1 W52 P1-2: 5 个纯显示函数拆到独立模块
from history_footnote.game_loop_display import (
    print_opening as _print_opening_impl,
    display_narrative as _display_narrative_impl,
    display_state as _display_state_impl,
    display_full_state as _display_full_state_impl,
    help_text as _help_text_impl,
    has_persona_opening as _has_persona_opening_impl,
    get_persona_opening as _get_persona_opening_impl,
)
# 🆕 v2.10.1 W52 P1-2 PR#2: 随机事件逻辑拆到独立模块
from history_footnote.game_loop_events import (
    check_random_events as _check_random_events_impl,
    apply_event_effects as _apply_event_effects_impl,
)
# 🆕 v2.10.1 W52 P1-2 PR#3: 存档/读档拆到独立模块
from history_footnote.game_loop_save import (
    save_to_slot as _save_to_slot_impl,
    load_from_slot as _load_from_slot_impl,
    auto_save as _auto_save_impl,
)
# 🆕 v2.10.1 W52 P1-2 followup: 身份切换逻辑拆到独立模块
from history_footnote.game_loop_identity import (
    inject_identity_switch_offers as _inject_identity_switch_offers_impl,
    handle_identity_decision as _handle_identity_decision_impl,
    apply_identity_switch as _apply_identity_switch_impl,
    show_available_offers as _show_available_offers_impl,
    set_pending_offer as _set_pending_offer_impl,
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
            # 🆕 v2.10.1 W86: 老数据 narrative 字段迁移
            # 走 GameState(**kwargs) 路径不触发 load()，手动迁移
            self.state._migrate_narrative_fields()
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
            # 🆕 v1.9.5：解析 custom_character → 结构化 state 字段（cash/debt/family/...）
            self._apply_character_initial_state()

        # 初始化组件
        self.rule_engine = RuleEngine(era_config)
        self.memory = GameMemory(save_dir=self.session.dir_path)
        # 从存档恢复记忆
        if load_state_data is not None and "event_log" in load_state_data:
            for ev_dict in load_state_data.get("event_log", []):
                self.memory.save_event(GameEvent.from_dict(ev_dict))

        # 🆕 v1.7.35 集成 EventBus / DramaManager / QuestSystem
        from history_footnote.event_bus import get_event_bus
        from history_footnote.drama_manager import DramaManager
        from history_footnote.quest_system import QuestSystem, WANLI_QUESTS
        self.event_bus = get_event_bus()
        self.drama_manager = DramaManager(self.state, era_config)
        self.quest_system = QuestSystem(self.state, self.event_bus, WANLI_QUESTS)
        # 默认接受所有可接任务
        for q in list(self.quest_system.quests.values()):
            if q.status == "available":
                self.quest_system.accept_quest(q.id)
        # 🆕 v1.7.45 结局系统
        from history_footnote.ending_system import EndingSystem
        self.ending_system = EndingSystem()

        # 🆕 v1.7.38 Game Engine Facade（统一接口）
        from history_footnote.game_engine_facade import GameEngineFacade
        self.engine = GameEngineFacade(self.state, era_config)
        # 把 facade 子系统映射到 self（保兼容）
        self._bind_facade()

        # 🆕 v2.8.0 章节层协调器（在 facade 之后初始化，复用 chapter sub-facade）
        from history_footnote.chapter.coordinator import ChapterCoordinator
        self._chapter_coordinator = ChapterCoordinator(
            state=self.state,
            chapter_facade=self.engine.sub_facades["chapter"],
            drama_manager=self.drama_manager,
        )

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
        """把 identity_switch_offers 注入到 DM 的 LLM state_ref——委托给 game_loop_identity"""
        _inject_identity_switch_offers_impl(self)

    def _apply_character_initial_state(self) -> None:
        """🆕 v1.9.5 把 custom_character 解析为结构化 state 字段

        解决问题：LLM 生成的"现银一两二钱 / 欠三两 / 母亲张氏"在 custom_character 里，
        但 state.cash/state.debt/state.family_members 等是 dataclass 默认 0/[]。
        解析层级（按优先级）：
        1. cc.initial_state（LLM 直接返回结构化）
        2. 正则解析 cc.background + cc.starting_situation
        3. identity_config.base_state 兜底
        """
        from history_footnote.initial_state_resolver import (
            extract_initial_state_from_character,
            apply_initial_state,
        )
        cc = getattr(self.state, "custom_character", None)
        if not cc:
            return
        # 优先用 self.identity_config（已在 __init__ 解析好）
        identity_config = getattr(self, "identity_config", {}) or {}
        try:
            initial = extract_initial_state_from_character(cc, identity_config)
            apply_initial_state(self.state, initial)
            logger.info(
                f"[v1.9.5] 初始状态已应用: source={initial.get('source')}, "
                f"cash={self.state.cash:.2f}, debt={self.state.debt:.2f}, "
                f"family={len(self.state.family_members)}, "
                f"tasks={len(self.state.active_tasks)}, "
                f"deadlines={len(self.state.upcoming_deadlines)}"
            )
        except Exception as e:
            logger.exception(f"[v1.9.5] 初始状态解析失败: {e}")

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
                self._chapter_coordinator.pre_step()  # 🆕 v2.8.0 章节层钩子
                self._run_round(player_input)
                self._chapter_coordinator.post_step()  # 🆕 v2.8.0
                self._chapter_coordinator.maybe_settle()  # 🆕 v2.8.0

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

        # 🆕 v1.7.30：检查历法（按时间触发重大历史事件）
        calendar_events = self.rule_engine.check_calendar(view)
        if calendar_events:
            # 写入 state.triggered_events
            for cal_evt in calendar_events:
                # triggered_events 是 list[str]
                if cal_evt["event_id"] not in self.state.triggered_events:
                    self.state.triggered_events.append(cal_evt["event_id"])
                # 如果有 evt_ids，构造 evt.* events 给 DM 用
                if cal_evt.get("evt_ids"):
                    logger.info(
                        f"📅 历法触发：{cal_evt['name']} ({cal_evt['year']}, {cal_evt['rank']})"
                    )
            # 注入到 DM context（让 DM 在 narrative 中体现）
            calendar_text = "\n".join([
                f"- [{e['rank']}] {e['name']}（{e['year']}年）：{e['narrative_hook']}"
                for e in calendar_events
            ])
            self.set_calendar_events_for_dm(calendar_text)

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

        # === 🆕 v1.7.33 步骤4.6：action_resolver 解析 + 应用 ===
        # 游戏引擎确定性处理所有结构化数据
        # LLM 不再需要输出 events 块
        from history_footnote.action_resolver import (
            parse_player_input, resolve_action, apply_action_result
        )
        player_action = parse_player_input(player_input)
        action_result = resolve_action(self.state, player_action, self.era_config)
        if action_result.success:
            apply_action_result(self.state, action_result)
            # 把 PlayerAction + narrative_hints 注入 DM context
            self.set_action_context_for_dm(player_action, action_result)
            # 🆕 v1.7.35 发布事件到 EventBus（QuestSystem/DM/Log 订阅）
            from history_footnote.event_bus import GameEvent
            for ev in action_result.events:
                self.event_bus.publish(GameEvent(
                    id=ev.get("id", ""),
                    type=ev.get("id", "").split(".")[0] if ev.get("id") else "unknown",
                    data=ev,
                    source="action_resolver",
                    priority=50,
                ))
            # DramaManager 记录动作
            self.drama_manager.record_player_action(
                verb=player_action.verb,
                obj=player_action.object,
                is_initiative=player_action.verb not in ("IDLE",),
            )
            # 🆕 v1.7.39 Wiki 检索（通过 facade，cache 生效）
            try:
                wiki_fragments = self.engine.search_wiki(
                    query=player_action.raw_text,
                    action_verb=player_action.verb,
                    target=player_action.target or "",
                    city=self.state.current_city or "",
                    top_k=2,
                )
                if wiki_fragments:
                    self.set_wiki_hint_for_dm(wiki_fragments)
            except Exception as e:
                logger.debug(f"Wiki 检索失败: {e}")
        else:
            # 失败（UNKNOWN / 现金不足等）→ 让 LLM 自由发挥
            self.set_action_context_for_dm(player_action, action_result, failed=True)

        # 🆕 v1.7.35 DramaManager 评估（每回合注入 LLM context）
        interventions = self.drama_manager.evaluate()
        if interventions:
            hint = self.drama_manager.build_llm_intervention_hint(interventions)
            self.set_drama_hint_for_dm(hint)
            # 发布 drama 事件
            from history_footnote.event_bus import GameEvent
            self.event_bus.publish(GameEvent(
                id="drama.intervention",
                type="drama",
                data={"interventions": [{"type": iv.type, "reason": iv.reason, "action": iv.action} for iv in interventions]},
                source="drama_manager",
                priority=70,
            ))

        # === 步骤5：DM Agent生成叙事 ===

        # 🆕 v1.6+ 并发支持：LLM 调用受 LLM_THROTTLE 保护
        from history_footnote.concurrency import LLM_THROTTLE
        import time as _time
        _t0 = _time.time()
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
        # 🆕 v1.7.41 性能监控
        self.engine.record_perf("llm_call", (_time.time() - _t0) * 1000)

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
        # 🐛 fix: 用 game_memory.GameEvent（不是 event_bus.GameEvent — 后者字段为 id/type/data）
        from history_footnote.game_memory import GameEvent as _MemoryEvent
        for summary in dm_response.get("events_to_save", []):
            event = _MemoryEvent(
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
        # 🆕 v2.10.1 W78: 记录玩家选择 + 当前日期（用于 recap 显示）
        # player_input: 自由输入的原文 / voice intent
        # chosen_voice: 选的 voice 名（如果有）
        # 🆕 v2.10.1 W84: 记录章节（按故事弧）
        # 🐛 fix: 初始化 chosen_voice（修复 undefined bug）
        chosen_voice = None
        chosen_voice_name = ""
        if chosen_voice and isinstance(chosen_voice, dict):
            chosen_voice_name = chosen_voice.get("voice_name", "") or ""
        current_chapter_id = getattr(self.state.chapter_state, "current_chapter", 0) or 0
        self.state.append_narrative(
            self.state.round_number,
            narrative,
            event_summary,
            player_input=player_input,
            chosen_voice=chosen_voice_name,
            current_date=self.state.current_date,
            chapter_id=current_chapter_id,  # 🆕 W84
        )

        # 🆕 v2.7.2：从 narrative 提取 4 类结构化 fact（保持上下文连贯性）
        # 同步调用，超时 8s 静默降级到启发式（不影响 narrative 响应）
        try:
            from history_footnote.narrative_facts_extractor import extract_facts_from_narrative
            llm_wrapper = getattr(self.dm, "llm", None)
            # 兼容：llm 可能是被 wrapper 包装过的
            if hasattr(llm_wrapper, "invoke") and not hasattr(llm_wrapper, "_invoke_with_timeout"):
                # 已经被 LLMWrapper 包装
                pass
            elif hasattr(self.dm, "llm_wrapper"):
                llm_wrapper = self.dm.llm_wrapper
            facts = extract_facts_from_narrative(
                narrative=narrative,
                round_num=self.state.round_number,
                llm_wrapper=llm_wrapper,
                timeout=8.0,
            )
            if facts:
                self.state.append_facts([f.to_dict() for f in facts])
                logger.info(
                    f"[v2.7.2] 提取 {len(facts)} 条 fact（回合 {self.state.round_number}）"
                )
        except Exception as e:
            logger.warning(f"[v2.7.2] fact 提取失败（不影响主流程）: {e}")

        # 🆕 v1.7.30：event_parser 解析 LLM 输出中的 <events> 块 → 写入 GameState
        # 替代旧的 LLM 自由写 financial_status 模式
        from history_footnote.event_parser import process_llm_output
        raw_llm_output = (
            dm_response.get("_raw_llm_output")
            or dm_response.get("narrative", "")
        )
        # 🆕 v1.7.30 P4 真实流程验证：如果 raw_output 不含 <events>，尝试从 dm.llm 拿
        if not raw_llm_output or "<events>" not in raw_llm_output:
            llm_obj = getattr(self.dm, "llm", None)
            if llm_obj and hasattr(llm_obj, "get_raw_output"):
                raw_llm_output = llm_obj.get_raw_output() or raw_llm_output
        event_result = process_llm_output(
            self.state, raw_llm_output, logger=logger
        )
        if event_result["events_applied"] > 0:
            logger.info(
                f"event_parser: {event_result['events_applied']} applied "
                f"(fallback={event_result['fallback_used']})"
            )

        # 🆕 v1.7.30：月度结算（每 3 回合触发一次）
        from history_footnote.settlement import (
            should_settle, settle_monthly, mark_settled, format_settlement_narrative,
        )
        if should_settle(self.state):
            settle_log = settle_monthly(self.state)
            if settle_log:
                settlement_text = format_settlement_narrative(settle_log)
                # 把结算 narrative 附加到 state.narrative_history
                self.state.narrative_history.append({
                    "round": self.state.round_number,
                    "narrative": settlement_text,
                    "type": "monthly_settlement",
                    "events": settle_log,
                })
                logger.info(
                    f"月度结算（{len(settle_log)} 条）："
                    f"cash={self.state.cash:.2f}, debt={self.state.debt:.2f}, rice={self.state.rice:.1f}"
                )
            mark_settled(self.state)

        # 🐛 v1.5.1 P1 Issue 5 修复：持久化 voice_options（供存档/前端复用）
        # 🆕 v1.6.9 P0 修复：当 LLM 把选项写进 narrative 而未通过 voice_options 返回时，
        # 自动从 narrative 文本提取"一、二、三"等内嵌选项
        # 🆕 v1.7.28 P0 修复：声明提前到 wiki 提取前，避免 dir() 兜底分支
        structured_voice_options = dm_response.get("voice_options", []) or []
        if not structured_voice_options and narrative:
            from history_footnote.narrative_sanitizer import merge_voice_options
            structured_voice_options = merge_voice_options(None, narrative)
            if structured_voice_options:
                logger.info(
                    f"[v1.6.9] inline options extracted: {len(structured_voice_options)} 个"
                )
        self.state.last_voice_options = structured_voice_options

        # 🆕 v1.7.1 Per-Save Character Wiki 自动提取
        # 从 narrative 自动提取 NPC + 事件 + 承诺，更新 wiki
        from history_footnote.character_wiki import CharacterWiki
        if not self.state.character_wiki:
            self.state.character_wiki = CharacterWiki(save_id=self.state.session_id or "").to_dict()
        wiki = CharacterWiki.from_dict(self.state.character_wiki)
        # 玩家选项（用于决策记录）—— 现在 structured_voice_options 已必有值
        wiki.auto_extract_from_narrative(
            narrative=narrative,
            round=self.state.round_number,
            player_input=player_input,
            player_options=[opt.get("intent_text", "") for opt in structured_voice_options] or None,
        )
        self.state.character_wiki = wiki.to_dict()

        # 🆕 v2.10.12+: cash reconciliation（每回合对账）
        # 目的：cr30 实测发现 cash 9.2 → 0 跳变无法对账。
        # 每个回合结束，从 financial_log 重新算 cash，和当前 state.cash 对比，
        # 如有 mismatch 立即 DEBUG 级别报警（不阻塞流程）。
        try:
            expected_cash = 0.0
            for fl in self.state.financial_log:
                if fl.get("type") == "borrow":
                    continue  # borrow 不动 cash，只动 debt
                # 🆕 还款特殊：repay 用 debt，不直接 -cash
                expected_cash += fl.get("amount", 0)
            if expected_cash > 0:
                diff = round(self.state.cash - expected_cash, 3)
                if abs(diff) > 0.01:
                    logger.warning(
                        f"[cash-reconcile] R{self.state.round_number} "
                        f"state.cash={self.state.cash:.3f} "
                        f"expected_from_log={expected_cash:.3f} "
                        f"diff={diff:+.3f}（mismatch！dev 需查 implicit 资金流出）"
                    )
                else:
                    logger.debug(
                        f"[cash-reconcile] R{self.state.round_number} OK ({self.state.cash:.2f} = {expected_cash:.2f})"
                    )
        except Exception as reconcile_err:
            logger.debug(f"[cash-reconcile] exception: {reconcile_err}")

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
        # 🆕 v1.7.28：复用上方已计算好的 structured_voice_options（已含 fallback）
        voice_options = structured_voice_options

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
        """打印开场白——委托给 game_loop_display.print_opening"""
        _print_opening_impl(
            self.state,
            self.era_config,
            self.identity_config,
            self.era_id,
            self.selected_identity,
        )

    def _has_persona_opening(self) -> bool:
        """检查dm_persona.md是否有开场白——委托给 game_loop_display.has_persona_opening"""
        return _has_persona_opening_impl(self.era_id)

    def _get_persona_opening(self) -> str | None:
        """从dm_persona.md提取开场白——委托给 game_loop_display.get_persona_opening"""
        return _get_persona_opening_impl(self.era_id)

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
        """展示叙事——委托给 game_loop_display.display_narrative"""
        _display_narrative_impl(narrative)

    def _display_state(self) -> None:
        """展示状态——委托给 game_loop_display.display_state"""
        _display_state_impl(self.state)

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
        """保存到指定slot——委托给 game_loop_save.save_to_slot"""
        _save_to_slot_impl(slot, self.session, self.save_manager, self.state, self.memory)

    def _load_from_slot(self, slot: str) -> bool:
        """从指定slot读档——委托给 game_loop_save.load_from_slot"""
        return _load_from_slot_impl(slot, self.session, self.save_manager)

    def _auto_save(self) -> None:
        """每回合自动存档到auto.json——委托给 game_loop_save.auto_save"""
        _auto_save_impl(self.session, self.save_manager, self.state, self.memory)

    # === 随机事件机制（v1.2+ DND化） ===

    def _check_random_events(self, scene: str) -> list[dict]:
        """检查并触发随机事件——委托给 game_loop_events.check_random_events"""
        return _check_random_events_impl(self.random_events, self.state, self.dice, scene)

    def _apply_event_effects(self, triggered_events: list[dict]) -> list[str]:
        """应用随机事件的效果——委托给 game_loop_events.apply_event_effects"""
        return _apply_event_effects_impl(triggered_events, self.state)

    def _bind_facade(self) -> None:
        """🆕 v1.7.38 把 facade 子系统映射到 self（保兼容）

        这样 game_loop 既能用 self.engine.process_player_input() 统一接口，
        也能用 self.event_bus / self.drama_manager / self.quest_system 直接访问。
        """
        self.event_bus = self.engine.event_bus
        self.drama_manager = self.engine.drama_manager
        self.quest_system = self.engine.quest_system

    def set_random_events_for_dm(self, triggered: list[dict]) -> None:
        """把随机事件结果注入到DM Agent的LLM state_ref

        DM在生成叙事时可以读到这些事件，把它们融入故事。
        """
        if not triggered:
            return
        if hasattr(self.dm.llm, "_state_ref_slot_ref"):
            current_ref = self.dm.llm._state_ref_slot_ref[0]
            current_ref["random_events"] = triggered

    def set_calendar_events_for_dm(self, calendar_text: str) -> None:
        """🆕 v1.7.30 把历法触发的大事件注入到 DM LLM state_ref

        calendar_text: 多行字符串，每行一个触发事件
        """
        self.set_state_ref_slot("calendar_events", calendar_text)

    def set_wiki_hint_for_dm(self, fragments: list) -> None:
        """🆕 v1.7.37 把 Wiki 检索片段注入到 DM LLM state_ref

        DM Agent 可根据需要主动调用 wiki_search 工具
        """
        if not fragments:
            return
        content_blocks = []
        for f in fragments[:3]:  # 最多 3 段
            c = f.get("content", "")
            if len(c) > 800:
                c = c[:800] + "..."
            content_blocks.append(f"【{f.get('title', '')}】\n{c}")
        self.set_state_ref_slot("wiki_hint", "\n\n".join(content_blocks))

    def set_state_ref_slot(self, key: str, value) -> None:
        """🆕 v1.7.41 通用 state_ref slot 注入

        替代 5 个 set_*_hint 方法。
        LLM 通过 _state_ref_slot_ref[0] 读取 state_ref 字典。
        """
        if not value:
            return
        if hasattr(self.dm.llm, "_state_ref_slot_ref"):
            current_ref = self.dm.llm._state_ref_slot_ref[0]
            current_ref[key] = value

    def set_drama_hint_for_dm(self, hint: str) -> None:
        """🆕 v1.7.35 把 DramaManager 干预 hint 注入到 DM LLM state_ref"""
        self.set_state_ref_slot("drama_hint", hint)

    def set_action_context_for_dm(self, player_action, action_result, failed: bool = False) -> None:
        """🆕 v1.7.33 把 PlayerAction + ActionResult 注入到 DM LLM state_ref

        LLM 用这些 context 生成 narrative（不再需要输出 events 块）

        Args:
            player_action: parse_player_input 的输出
            action_result: resolve_action 的输出
            failed: 是否失败（现金不足/UNKNOWN）
        """
        if not hasattr(self.dm.llm, "_state_ref_slot_ref"):
            return
        current_ref = self.dm.llm._state_ref_slot_ref[0]
        current_ref["action_context"] = {
            "raw_text": player_action.raw_text,
            "verb": player_action.verb,
            "object": player_action.object,
            "amount": player_action.amount,
            "target": player_action.target,
            "location": player_action.location,
            "hint": player_action.hint,
            "state_changes": action_result.state_changes if action_result else {},
            "events_triggered": [e.get("id", "") for e in (action_result.events if action_result else [])],
            "narrative_hints": action_result.narrative_hints if action_result else [],
            "failed": failed,
            "error_msg": action_result.error_msg if action_result else "",
            "instruction": (
                "游戏引擎已处理以下结构化数据。你只需要把以下状态变化包装成 narrative："
                + "\n".join([f"  - {e.get('id', '')}: {e.get('note', '')}" for e in (action_result.events if action_result else [])])
                + "\n不需要输出 <events> 块。"
            ),
        }

    # === 身份切换机制 ===

    def _handle_identity_decision(self, accept: bool) -> bool:
        """处理 /accept 或 /decline——委托给 game_loop_identity"""
        return _handle_identity_decision_impl(self, accept)

    def _apply_identity_switch(self, offer: dict) -> None:
        """应用身份切换——委托给 game_loop_identity"""
        _apply_identity_switch_impl(self, offer)

    def _show_available_offers(self) -> None:
        """显示可用 offer——委托给 game_loop_identity"""
        _show_available_offers_impl(self)

    def set_pending_offer(self, offer: dict) -> None:
        """设置待处理 offer——委托给 game_loop_identity"""
        _set_pending_offer_impl(self, offer)

    def _display_full_state(self) -> None:
        """展示完整状态——委托给 game_loop_display.display_full_state"""
        _display_full_state_impl(self.session, self.state, self.memory)

    @staticmethod
    def _help_text() -> str:
        """帮助文本——委托给 game_loop_display.help_text"""
        return _help_text_impl()
