"""🆕 v1.7.34 EventBus（事件总线）

依据"高自由度RPG引擎"调研报告：
> 事件总线贯穿所有层，是跨层通信的唯一通道。

设计：
- 单一入口 publish(event) → 所有订阅者收到
- 中间件链（filter/transform/log）
- 异步/同步两种模式
- 错误隔离（一个 handler 失败不影响其他）

事件类型（与现有 EventId 一致）：
- fin.* / city.* / fam.* / gen.* / prop.* / inv.*
- trv.* / comm.* / gov.* / obj.* / relig.* / reln.* / dis.*
- discover.* / evt.*
- meta.* （元事件：log/save/feedback 等）

事件结构：
{
  "id": "fin.sell_silk",  # 事件 ID
  "type": "fin",  # 命名空间
  "data": {amount: 0.7, note: "卖湖绫一匹"},
  "source": "action_resolver",  # 触发源
  "priority": 0,  # 优先级
  "ts": "2026-07-06T19:00:00",  # 时间戳
  "trace_id": "uuid-..."  # 追踪 ID
}
"""
from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


_LOG = logging.getLogger("history_footnote.event_bus")


class EventPriority(Enum):
    """事件优先级（高→低）"""
    CRITICAL = 100  # 系统错误 / 关键状态变化
    HIGH = 75  # 财务变化 / 历史事件
    NORMAL = 50  # 通用事件
    LOW = 25  # 日志 / 提示
    DEBUG = 0  # 调试


@dataclass
class GameEvent:
    """游戏事件（结构化）"""
    id: str  # "fin.sell_silk"
    type: str  # "fin"（命名空间）
    data: dict = field(default_factory=dict)
    source: str = "unknown"
    priority: int = 50
    ts: str = ""
    trace_id: str = ""

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.now().isoformat(timespec="seconds")
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex[:12]
        if not self.type and self.id:
            self.type = self.id.split(".")[0]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GameEvent":
        return cls(**{k: v for k, v in d.items() if k in cls.__annotations__})


# 事件处理器签名：Callable[[GameEvent], None]
EventHandler = Callable[[GameEvent], None]


class EventBus:
    """事件总线（线程安全）"""

    def __init__(self, name: str = "default"):
        self.name = name
        self._lock = __import__("threading").RLock()
        # 订阅者：{event_type: [handler, ...]}
        # 通配符订阅：{namespace: handlers}
        self._subscribers: dict[str, list[tuple[EventHandler, dict]]] = defaultdict(list)
        # 事件历史（环形缓冲）
        self._history: list[GameEvent] = []
        self._max_history = 1000
        # 中间件
        self._middleware: list[Callable[[GameEvent], Optional[GameEvent]]] = []
        # 死信队列（处理失败的）
        self._dead_letter: list[tuple[GameEvent, str, str]] = []
        # 事件持久化（可选）
        self._persist_path: Optional[Path] = None
        # 统计
        self._stats = {
            "total_published": 0,
            "total_handled": 0,
            "total_failed": 0,
            "by_type": defaultdict(int),
        }

    # === 订阅管理 ===

    def subscribe(self, event_pattern: str, handler: EventHandler, **meta) -> None:
        """订阅事件

        Args:
            event_pattern: 事件 ID 或通配符
                - "fin.sell_silk" 精确匹配
                - "fin.*" 通配符（所有 fin 事件）
                - "*" 所有事件
            handler: 处理函数
            **meta: 元数据（priority/source/...）
        """
        with self._lock:
            self._subscribers[event_pattern].append((handler, meta))
            _LOG.debug(f"[{self.name}] 订阅 {event_pattern} → {handler.__name__}")

    def unsubscribe(self, event_pattern: str, handler: EventHandler) -> bool:
        """取消订阅"""
        with self._lock:
            handlers = self._subscribers.get(event_pattern, [])
            for i, (h, _) in enumerate(handlers):
                if h is handler:
                    handlers.pop(i)
                    return True
            return False

    # === 中间件 ===

    def use(self, middleware: Callable[[GameEvent], Optional[GameEvent]]) -> None:
        """添加中间件（链式处理）

        middleware(GameEvent) -> GameEvent | None
        返回 None 表示过滤掉该事件
        """
        with self._lock:
            self._middleware.append(middleware)

    # === 事件发布 ===

    def publish(self, event: GameEvent) -> int:
        """发布事件（同步）

        Returns: 处理的 handler 数量
        """
        if not isinstance(event, GameEvent):
            if isinstance(event, dict):
                event = GameEvent.from_dict(event)
            else:
                raise TypeError(f"event must be GameEvent or dict, got {type(event)}")

        with self._lock:
            self._stats["total_published"] += 1
            self._stats["by_type"][event.type] += 1
            # 应用中间件
            for mw in self._middleware:
                try:
                    result = mw(event)
                    if result is None:
                        # 过滤掉
                        return 0
                    event = result
                except Exception as e:
                    _LOG.error(f"[{self.name}] 中间件 {mw.__name__} 失败: {e}")
            # 持久化（可选）
            if self._persist_path:
                self._persist_event(event)
            # 历史
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            # 找到订阅者
            handlers_to_call = self._get_handlers(event)
            # 调用
            handled = 0
            for handler, meta in handlers_to_call:
                try:
                    handler(event)
                    self._stats["total_handled"] += 1
                    handled += 1
                except Exception as e:
                    self._stats["total_failed"] += 1
                    tb = traceback.format_exc()
                    self._dead_letter.append((event, str(e), tb))
                    _LOG.error(f"[{self.name}] handler {handler.__name__} 失败: {e}")
            return handled

    def publish_dict(self, event_dict: dict) -> int:
        """发布 dict 格式事件"""
        return self.publish(GameEvent.from_dict(event_dict))

    def _get_handlers(self, event: GameEvent) -> list[tuple[EventHandler, dict]]:
        """获取所有匹配的 handlers

        匹配规则：
        1. 精确 ID 匹配
        2. 通配符 * 匹配
        3. 命名空间通配符 (e.g. "fin.*") 匹配
        """
        handlers = []
        # 精确
        handlers.extend(self._subscribers.get(event.id, []))
        # * 命名空间
        handlers.extend(self._subscribers.get(f"{event.type}.*", []))
        # 全通配
        handlers.extend(self._subscribers.get("*", []))
        return handlers

    # === 持久化 ===

    def enable_persistence(self, path: Path) -> None:
        """启用事件持久化（追加到 JSONL 文件）"""
        self._persist_path = Path(path)
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)

    def _persist_event(self, event: GameEvent) -> None:
        if not self._persist_path:
            return
        try:
            with self._persist_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            _LOG.error(f"事件持久化失败: {e}")

    # === 死信 / 失败回放 ===

    def replay_dead_letters(self) -> int:
        """重新发布死信队列（用于失败重试）"""
        replayed = 0
        with self._lock:
            dl = self._dead_letter[:]
            self._dead_letter.clear()
        for event, err, tb in dl:
            try:
                self.publish(event)
                replayed += 1
            except Exception as e:
                _LOG.error(f"重放死信失败: {e}")
        return replayed

    # === 查询 ===

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> list[GameEvent]:
        """获取事件历史

        Args:
            event_type: 过滤类型（"fin" / "fin.sell_silk"）
            limit: 最多返回多少条
        """
        with self._lock:
            history = self._history[:]
        if event_type:
            if "." in event_type:
                # 精确 ID
                history = [e for e in history if e.id == event_type]
            else:
                # 命名空间
                history = [e for e in history if e.type == event_type]
        return history[-limit:]

    def get_stats(self) -> dict:
        """获取总线统计"""
        with self._lock:
            stats = dict(self._stats)
            stats["by_type"] = dict(self._stats["by_type"])
            stats["dead_letter_count"] = len(self._dead_letter)
            stats["subscribers_count"] = sum(len(handlers) for handlers in self._subscribers.values())
            return stats


# ============= 全局单例 =============

_GLOBAL_BUS: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线（单例）"""
    global _GLOBAL_BUS
    if _GLOBAL_BUS is None:
        _GLOBAL_BUS = EventBus(name="global")
        # 注册默认 handler
        _register_default_handlers(_GLOBAL_BUS)
    return _GLOBAL_BUS


def reset_event_bus() -> None:
    """重置全局事件总线（测试用）"""
    global _GLOBAL_BUS
    _GLOBAL_BUS = None


def _register_default_handlers(bus: EventBus) -> None:
    """注册默认 handlers

    默认行为：
    1. 所有事件：log
    2. fin.* 事件：写入 financial_log
    3. evt.* 事件：写入 triggered_events
    4. city.* 事件：current_city
    5. discover.* 事件：discoveries bucket
    6. fam.* 事件：family_members + fam_log
    """
    # 注：handler 实际在 game_loop 调 process_event 时执行
    # 这里只放 log handler
    def log_handler(event: GameEvent) -> None:
        if event.priority >= EventPriority.LOW.value:
            _LOG.info(f"[bus/{event.type}] {event.id} {event.data}")

    bus.subscribe("*", log_handler, priority=EventPriority.DEBUG.value)


# ============= 烟雾测试 =============

if __name__ == "__main__":
    # 1. 基本发布订阅
    bus = EventBus("test")
    received = []

    def h1(event):
        received.append(("h1", event.id))

    def h2(event):
        received.append(("h2", event.id))

    bus.subscribe("fin.sell_silk", h1)
    bus.subscribe("fin.*", h2)
    bus.subscribe("*", h1)  # 也订阅全部

    # 发布
    n = bus.publish(GameEvent(id="fin.sell_silk", type="fin", data={"amount": 0.7}))
    print(f"fin.sell_silk: {n} handlers")
    print(f"  received: {received}")

    n = bus.publish(GameEvent(id="city.arrive.suzhou", type="city"))
    print(f"city.arrive.suzhou: {n} handlers")

    # 2. 中间件
    bus.use(lambda e: e if e.priority >= 25 else None)  # 过滤 DEBUG
    n = bus.publish(GameEvent(id="fin.buy_thread", type="fin", priority=10))
    print(f"fin.buy_thread (priority=10): {n} handlers (应=0)")

    n = bus.publish(GameEvent(id="fin.buy_thread", type="fin", priority=50))
    print(f"fin.buy_thread (priority=50): {n} handlers (应≥1)")

    # 3. 失败处理
    def bad_handler(event):
        raise ValueError("intentional")

    bus.subscribe("dis.*", bad_handler)
    bus.subscribe("dis.*", h1)
    n = bus.publish(GameEvent(id="dis.flood", type="dis"))
    print(f"dis.flood: {n} handlers (应=2)")
    print(f"dead_letter: {len(bus._dead_letter)}")

    # 4. 统计
    print(f"\nstats: {bus.get_stats()}")
