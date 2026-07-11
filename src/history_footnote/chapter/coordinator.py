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
                self._initialized = True
                _LOG.info(
                    "[v2.8.0] 第 %d 章初始化: %s, round_start=%d, via=hardcoded",
                    target_chapter,
                    self.state.chapter_state.blueprint.get("chapter_title", "?"),
                    self.state.chapter_state.chapter_start_round,
                )
            except FileNotFoundError as e2:
                # 🆕 W32: 硬编码也不存在时，明确错误但**不 raise**（保持向后兼容）
                # 因为这之前的代码是 silent log 走完，smoke 测试依赖此行为
                _LOG.error("第 %d 章硬编码蓝图也不存在: %s，章节化就此退出（无法继续）", target_chapter, e2)
                # 不 raise，避免破坏 smoke / 上层 caller 假设

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

    def _maybe_advance_node(self) -> None:
        """检查是否推进节点（段一硬编码：每 4 回合推进一个）"""
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

    # ============= 钩子 2：每回合结束 =============

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
