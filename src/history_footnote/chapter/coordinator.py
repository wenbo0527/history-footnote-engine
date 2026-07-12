"""v2.8.0 ChapterCoordinator（章节协调器）

设计目标：
- 给 game_loop 提供 3 个钩子（pre_step / post_step / maybe_settle）
- 不动 _run_round 内部 9 步逻辑
- 协调 ChapterFacade 蓝图加载 + 收束判定 + 节点推进

3 钩子的语义：
1. pre_step：每回合开始时
   - 首次进入：初始化第 1 章
   - 节点推进：检查并推进
2. post_step：每回合结束时
   - 收束检查
   - 写回 last_closure_status
3. maybe_settle：每回合结束后
   - 满足 SOFT_READY / HARD_FORCED → 结算 + 推进下一章

段一节点推进规则（硬编码，段二可配置）：
- 固定每 4 回合推进一个节点（节点 1→2→3→4）
- 段一不查 LLM、不查 value_dimensions、不查 NPC 关系

段一不实现：
- 章节结算内容（只追加 chapter_history 骨架）
- 下一章初始化（maybe_settle 只追加 history，不调 init_chapter）
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from history_footnote.chapter.closure import (
    ChapterClosure,
    DEFAULT_NODES_PER_CHAPTER,
    DEFAULT_ROUNDS_PER_NODE,
)

if TYPE_CHECKING:
    from history_footnote.game_state import GameState
    from history_footnote.sub_facades import ChapterFacade


_LOG = logging.getLogger("history_footnote.chapter.coordinator")


# 节点推进规则（段一硬编码）
NODES_ADVANCE_ROUNDS = 4  # 每 4 回合推进一个节点


class ChapterCoordinator:
    """章节协调器——game_loop 的 3 个钩子

    用法（在 game_loop.run 中）：
        while not self._is_game_over():
            player_input = self._get_player_input()
            self._chapter_coordinator.pre_step()  # 新增
            self._run_round(player_input)
            self._chapter_coordinator.post_step()  # 新增
            self._chapter_coordinator.maybe_settle()  # 新增

    段二 W9 升级：
    - 支持 LLM 注入（llm_callable）
    - init_chapter 走 LLM 路径（mock LLM 模式）
    - 段一硬编码仍可用（不传 llm_callable）
    """

    def __init__(
        self,
        state: "GameState",
        chapter_facade: "ChapterFacade",
        drama_manager=None,
        llm_callable=None,
    ):
        self.state = state
        self.facade = chapter_facade
        self._drama = drama_manager
        self._llm = llm_callable  # None=段一硬编码模式
        self._closure: Optional[ChapterClosure] = None
        # 首次 init 标记
        self._initialized = False

    @property
    def closure(self) -> ChapterClosure:
        if self._closure is None:
            self._closure = ChapterClosure(self.state, self._drama)
        return self._closure

    # ============= 钩子 1：每回合开始 =============

    def pre_step(self) -> None:
        """每回合开始时调用

        行为：
        - 首次进入游戏 → 初始化第 1 章
        - 检查节点推进条件
        """
        cs = self.state.chapter_state

        # 首次初始化
        if not self._initialized and cs.current_chapter == 0:
            self._init_first_chapter()
            return

        # 已初始化但 current_chapter=0（如结算后）→ 不重复 init
        if cs.current_chapter == 0:
            return

        # 节点推进检查
        self._maybe_advance_node()

    def _init_first_chapter(self) -> None:
        """初始化第 1 章

        段二 W9 升级：
        - 有 llm_callable → 调 facade.convert_llm_to_blueprint（走 LLM 路径）
        - 无 llm_callable → facade.init_chapter（段一硬编码路径）
        - 段三：支持 chapter 1 之后的 init（不再只 first）
        """
        # 段二 W9：先确定要 init 哪一章
        target_chapter = self._next_chapter_to_init() or 1

        try:
            if self._llm is not None:
                # 走 LLM 路径
                self._init_chapter_via_llm(target_chapter)
            else:
                # 段一硬编码路径
                self.facade.init_chapter(target_chapter)

            # 🆕 v2.10.1 W85: 蓝图加载后注入 5 字段默认值
            self._inject_w85_blueprint_defaults()

            self._initialized = True
            _LOG.info(
                "[v2.8.0] 第 %d 章初始化: %s, round_start=%d, via=%s",
                target_chapter,
                self.state.chapter_state.blueprint.get("chapter_title", "?"),
                self.state.chapter_state.chapter_start_round,
                "llm" if self._llm else "hardcoded",
            )
        except FileNotFoundError as e:
            _LOG.error("第 %d 章蓝图加载失败: %s，回退到硬编码", target_chapter, e)
            try:
                self.facade.init_chapter(target_chapter)
                # 🆕 W32: 硬编码成功，标 initialized
                self._inject_w85_blueprint_defaults()
                self._initialized = True
                _LOG.info(
                    "[v2.8.0] 第 %d 章初始化: %s, round_start=%d, via=hardcoded",
                    target_chapter,
                    self.state.chapter_state.blueprint.get("chapter_title", "?"),
                    self.state.chapter_state.chapter_start_round,
                )
            except FileNotFoundError as e2:
                # 🆕 W32 + W85-P0-1: 硬编码蓝图缺失时的 3 层 fallback
                # 1) LLM 实时生成
                # 2) 静态最小可用 blueprint（不依赖任何外部文件）
                # 3) 放弃（保持原 silent log，不 raise）
                _LOG.warning(
                    "[W85-P0-1] 第 %d 章硬编码蓝图缺失，尝试 LLM fallback: %s",
                    target_chapter, e2,
                )
                if self._llm is not None:
                    try:
                        self._init_chapter_via_llm(target_chapter)
                        self._inject_w85_blueprint_defaults()
                        self._initialized = True
                        _LOG.info(
                            "[W85-P0-1] 第 %d 章 LLM fallback 成功",
                            target_chapter,
                        )
                        return
                    except Exception as e3:
                        _LOG.error(
                            "[W85-P0-1] LLM fallback 也失败: %s",
                            e3,
                        )
                # 2) 静态 fallback（不依赖文件）
                if self._static_fallback_init(target_chapter):
                    return
                # 3) 彻底放弃（不 raise，保留向后兼容）
                _LOG.error(
                    "[W85-P0-1] 所有 fallback 都失败，章节化就此退出（无法继续）",
                )

    def _inject_w85_blueprint_defaults(self) -> None:
        """🆕 v2.10.1 W85: 为已加载蓝图注入 W85 5 字段默认值

        行为：
        - 不覆盖已有值（LLM 生成的蓝图如果带 W85 字段，保留之）
        - 缺哪个字段补哪个（向后兼容旧蓝图文件）
        - must_resolve 缺则补空 list（避免 KeyError）
        """
        cs = self.state.chapter_state
        bp = cs.blueprint
        if not bp:
            return
        bp.setdefault("narrative_position", "opening")
        bp.setdefault("pace", "slow")
        bp.setdefault("hook_type", "none")
        bp.setdefault("must_resolve", [])
        bp.setdefault("dm_instruction", "铺陈日常，暗示即将到来的变故")

    def _static_fallback_init(self, chapter_id: int) -> bool:
        """🆕 W85-P0-1: 静态 fallback blueprint

        当 LLM 和硬编码蓝图都不可用时,直接构造最小可用 blueprint dict
        让章节化叙事能继续,玩家不至于卡死。

        Returns:
            bool: True=成功初始化, False=彻底失败
        """
        try:
            cs = self.state.chapter_state
            cs.current_chapter = chapter_id
            cs.current_node = 1
            cs.chapter_start_round = self.state.round_number
            cs.blueprint = {
                "chapter_id": chapter_id,
                "chapter_title": f"第 {chapter_id} 章",
                "chapter_subtitle": "章节蓝图缺失,启用应急模式",
                "nodes": [
                    {
                        "index": 1,
                        "role": "introduction",
                        "scene": "应急场景：DM 实时叙事",
                        "npc_ids": [],
                        "option_directions": [],
                        "knowledge_ids": [],
                        "completion_condition": "round_4_reached",
                    }
                ],
                "transition_hint": "season",
                "meta": None,
                # 🆕 W85 5 字段(直接填,免得后面再注入一次)
                "narrative_position": "opening",
                "pace": "slow",
                "hook_type": "none",
                "must_resolve": [],
                "dm_instruction": "应急模式：铺陈日常，等待玩家后续行为",
            }
            cs.last_closure_status = "INIT"
            cs.just_initialized = True
            # 🆕 W85: 路线也重置为 opening
            from history_footnote.chapter.types import DEFAULT_CURRENT_ROUTE
            cs.current_route = dict(DEFAULT_CURRENT_ROUTE)
            cs.current_route["entered_at_round"] = self.state.round_number
            cs.route_history.append({
                "round": self.state.round_number,
                "from_template": "none",
                "to_template": "opening",
                "trigger": "static_fallback",
            })
            self._initialized = True
            _LOG.info(
                "[W85-P0-1] 静态 fallback 初始化成功: chapter=%d",
                chapter_id,
            )
            return True
        except Exception as e:
            _LOG.error("[W85-P0-1] 静态 fallback 失败: %s", e)
            return False

    def _init_chapter_via_llm(self, chapter_id: int) -> None:
        """段二 W9：通过 LLM 生成章节蓝图

        流程：
        1. facade.build_prompt_context(chapter_id) → 喂 LLM 的完整上下文
        2. self._invoke_llm(prompt_dict) → LLM 返回章节蓝图 dict
        3. facade.convert_llm_to_blueprint(llm_output, chapter_id) → 校验+兑底
        4. 写入 state.chapter_state（继承 facade.init_chapter 的逻辑）
        5. 🆕 v2.8.0 段三 W13：设置 just_initialized=True 触发 PathSwitcher
        """
        # 1. 构建 prompt
        prompt_ctx = self.facade.build_prompt_context(chapter_id)

        # 2. 调 LLM（兼容 LangChain BaseChatModel 类 LLM 和 callable 函数）
        try:
            llm_output = self._invoke_llm(prompt_ctx)
        except Exception as e:
            _LOG.error("LLM 调用失败: %s，回退硬编码", e)
            self.facade.init_chapter(chapter_id)
            # 段三 W13：硬编码路径也要设标记
            self.state.chapter_state.just_initialized = True
            return

        # 3. 转换+校验+兑底
        blueprint = self.facade.convert_llm_to_blueprint(llm_output, chapter_id=chapter_id)

        # 4. 写入 state（复用 facade.init_chapter 的写入逻辑）
        cs = self.state.chapter_state
        cs.current_chapter = chapter_id
        cs.current_node = 1
        cs.chapter_start_round = self.state.round_number
        cs.blueprint = blueprint.to_dict()
        cs.last_closure_status = "INIT"
        # 段三 W13：标记章节刚初始化（PathSwitcher 触发器 4 用）
        cs.just_initialized = True

    def _next_chapter_to_init(self) -> Optional[int]:
        """段二 W9：决定下一章序号

        - 第 1 次 init → 1
        - 段三扩展：基于已结算章节数 + 1
        """
        history = self.state.chapter_state.chapter_history
        if not history:
            return 1
        last = history[-1]
        return last.get("chapter", 0) + 1

    def _invoke_llm(self, prompt_ctx: dict) -> dict:
        """🆕 v2.8.0 段六 W19 兼容 LangChain LLM

        兼容 2 种 LLM 类型：
        1. callable 函数（mock 模式 / 测试）：self._llm(prompt_ctx) → dict
        2. LangChain BaseChatModel 类（真 LLM）：需 .invoke() + AIMessage.content
           还要先调 facade.build_chapter_tool_prompt 转为字符串

        Returns:
            dict: LLM 生成的章节蓝图 dict

        Raises:
            Exception: LLM 调用失败时（让外层 fallback）
        """
        if self._llm is None:
            raise ValueError("_llm is None")

        # 判 callable
        if callable(self._llm) and not hasattr(self._llm, "invoke"):
            # mock 函数模式：直接调，返回 dict
            return self._llm(prompt_ctx)

        # LangChain 类模式：调 facade.build_chapter_tool_prompt → HumanMessage → .invoke
        from history_footnote.chapter.dm_tool import fill_chapter_blueprint_via_llm
        # 用 dm_tool 的完整路径（已实现 invoke + JSON 提取）
        blueprint = fill_chapter_blueprint_via_llm(
            state=self.state,
            chapter_id=prompt_ctx["chapter_meta"]["chapter_id"],
            era_config=prompt_ctx.get("chapter_meta", {}).get("era_config", {}),
            llm_callable=self._llm,
            chapter_facade=self.facade,
        )
        if blueprint is None:
            raise RuntimeError("fill_chapter_blueprint_via_llm 返回 None")
        return blueprint.to_dict()

    def detect_route_change(
        self,
        player_input: str,
        value_shifts: dict,
        historical_anchors_triggered: Optional[list] = None,
    ) -> dict:
        """🆕 v2.10.1 W85: 调 RouteDetector 检测路线变化

        Returns:
            RouteDetector.detect() 的原始结果 dict（含 route_change/suggested_template/trigger/confidence/dm_instruction）

        Phase 2: 把 coordinator 的 _llm 注入 RouteDetector,实现未预设路线的 LLM 识别
        """
        from history_footnote.chapter.route_detector import RouteDetector
        # 🆕 W85-Phase 2: 把 self._llm 传给 RouteDetector
        detector = RouteDetector(llm_callable=self._llm)
        cs = self.state.chapter_state
        # current_chapter 可以是 dict（blueprint 存储形式）
        current = cs.blueprint or {}
        return detector.detect(
            player_input=player_input,
            value_shifts=value_shifts,
            current_chapter=current,
            historical_anchors_triggered=historical_anchors_triggered,
        )

    def apply_route_change(self, detection: dict) -> None:
        """🆕 v2.10.1 W85: 应用路线变更到 state

        行为：
        1. 写 current_route（template / trigger / entered_at_round / dm_instruction）
        2. 追加 route_history
        3. 不立即改章节（让 DM 先按新路线创作，下一节点再结算）

        Args:
            detection: RouteDetector.detect() 返回的 dict
        """
        if not detection.get("route_change"):
            return
        cs = self.state.chapter_state
        new_template = detection["suggested_template"]
        from_template = (cs.current_route or {}).get("template", "opening")
        # 写 current_route
        cs.current_route = {
            "template": new_template,
            "trigger": detection["trigger"],
            "entered_at_round": self.state.round_number,
            "dm_instruction": detection.get("dm_instruction", ""),
        }
        # 追加 route_history
        cs.route_history.append({
            "round": self.state.round_number,
            "from_template": from_template,
            "to_template": new_template,
            "trigger": detection["trigger"],
        })
        _LOG.info(
            "[W85] 路线变更: round=%d, %s → %s, trigger=%s",
            self.state.round_number,
            from_template,
            new_template,
            detection["trigger"],
        )

    def _maybe_advance_node(self) -> None:
        """检查并推进节点

        规则：每 NODES_ADVANCE_ROUNDS 回合推进一个节点
        """
        cs = self.state.chapter_state
        if cs.current_chapter == 0 or cs.current_node >= DEFAULT_NODES_PER_CHAPTER:
            return  # 已到末节点

        rounds_in_chapter = max(0, self.state.round_number - cs.chapter_start_round + 1)
        expected_node = min(
            DEFAULT_NODES_PER_CHAPTER,
            (rounds_in_chapter - 1) // NODES_ADVANCE_ROUNDS + 1,
        )

        if expected_node > cs.current_node:
            old_node = cs.current_node
            cs.current_node = expected_node
            _LOG.info(
                "[v2.8.0] 节点推进: chapter=%d, node %d → %d (round=%d)",
                cs.current_chapter, old_node, expected_node, self.state.round_number,
            )

        # 🆕 v2.10.1 W85: 推进节点时,如果 current_route 有新模板,
        # 同步更新 blueprint 的 narrative_position
        if cs.current_route and cs.blueprint:
            new_template = cs.current_route.get("template")
            old_template = cs.blueprint.get("narrative_position")
            if new_template and new_template != old_template:
                cs.blueprint["narrative_position"] = new_template
                _LOG.info(
                    "[W85] narrative_position 同步: %s → %s (round=%d)",
                    old_template, new_template, self.state.round_number,
                )

    def post_step(self) -> None:
        """每回合结束时调用

        行为：
        - 调用 facade.check_closure() 写回 last_closure_status
        - 🆕 v2.8.0 段三 W13：跑 PathSwitcher 4 触发器 + apply events
        - 🆕 v2.8.0 段三 W13：清空 just_initialized 标记
        """
        if self.state.chapter_state.current_chapter == 0:
            return
        self.facade.check_closure()

        # 段三 W13：跑 PathSwitcher
        try:
            events = self.facade.check_path_events()
            if events:
                self.facade.apply_path_events(events)
                _LOG.info("应用 %d 个路径事件", len(events))
        except Exception as e:
            _LOG.warning("PathSwitcher 跑失败: %s", e)

        # 段三 W13：清空 just_initialized（只触发一次）
        if self.state.chapter_state.just_initialized:
            self.state.chapter_state.just_initialized = False

        # 🆕 v2.10.1 W85: 路线检测（关键词 / 价值偏移 / 历史铁轨）
        try:
            last_input = getattr(self.state, "last_player_input", "") or ""
            last_value_shifts = getattr(self.state, "value_shifts", {}) or {}
            detection = self.detect_route_change(
                player_input=last_input,
                value_shifts=last_value_shifts,
                historical_anchors_triggered=None,  # Phase 1 默认 None
            )
            self.apply_route_change(detection)
        except Exception as e:
            _LOG.warning("[W85] 路线检测跑失败: %s", e)

    # ============= 钩子 3：条件触发结算 =============

    def maybe_settle(self) -> None:
        """条件触发章节结算

        行为：
        - SOFT_READY / HARD_FORCED → 调 Settlement 生成完整记录（含 4 必填项 + 摘要）
        - 追加到 chapter_history
        - 重置 current_chapter=0（不自动 init 下一章）

        段二 W8 升级：用 ChapterSettlement 替代硬编码 summary
        """
        cs = self.state.chapter_state
        if cs.current_chapter == 0:
            return

        status = cs.last_closure_status
        if status not in ("SOFT_READY", "HARD_FORCED"):
            return

        # 段二 W8：调 Settlement 生成完整记录
        from history_footnote.chapter.settlement import ChapterSettlement
        # 段六+ W20：Settlement 也接 LLM（与 Coordinator 共用同一个 _llm）
        settlement = ChapterSettlement(
            self.state,
            era_config=None,
            llm_callable=self._llm,  # 🆕 段六+ W20：Settlement 共享 LLM
        )
        chapter_record = settlement.settle(closure_status=status)
        if chapter_record:
            cs.chapter_history.append(chapter_record)

        _LOG.info(
            "[v2.8.0] 章节结算: chapter=%d, status=%s, rounds=%d, summary_len=%d",
            cs.current_chapter, status, chapter_record.get("rounds_in_chapter", 0),
            len(chapter_record.get("summary", "")),
        )

        # 段一：不初始化下一章（保留 current_chapter=0 表示已结束）
        # 段二/段三可以在这里调 facade.init_chapter(current+1)
        cs.current_chapter = 0
        cs.current_node = 1
        cs.blueprint = None
        cs.last_closure_status = "INIT"
        self._initialized = False
