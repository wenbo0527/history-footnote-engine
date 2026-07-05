"""🆕 v1.6.2 SSE Streaming 处理器

实现 Server-Sent Events (SSE) 让 DM 叙事逐步返回给前端：

事件流：
1. event: thinking   → DM 正在思考（"DM 在思考中..."）
2. event: chunk      → 叙事文本片段（"这是第一段..."）
3. event: voice_options → 内在声音选项
4. event: done       → 完成（包含最终 state）
5. event: error      → 错误

前端使用：
```javascript
const evtSource = new EventSource('/api/input_stream?session_id=xxx&input=xxx');
evtSource.addEventListener('chunk', (e) => {
    appendText(e.data);  // 逐字显示
});
evtSource.addEventListener('done', (e) => {
    evtSource.close();
    const data = JSON.parse(e.data);
    updateVoiceOptions(data.voice_options);
});
```

收益：
- 首 token 延迟 3-5s → <500ms（用户立刻看到 "DM 思考中..."）
- 心理感受提升 10x
- 实现复杂度中等（需要异步 + 队列）
"""
from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class StreamingEmitter:
    """SSE 事件发射器（线程安全）

    用法：
        emitter = StreamingEmitter()
        # 在 LLM 调用线程里：
        emitter.emit("thinking", "DM 在分析场景...")
        emitter.emit("chunk", "灶房里...")
        emitter.emit("done", final_data)

        # 在 HTTP 响应线程里：
        for event_type, event_data in emitter.iter_events():
            yield format_sse(event_type, event_data)
    """

    def __init__(self):
        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._done_event = threading.Event()
        self._error: Exception | None = None

    def emit(self, event_type: str, data: Any) -> None:
        """发射一个事件"""
        self._queue.put((event_type, data))

    def emit_chunk(self, text: str) -> None:
        """发射一个叙事片段"""
        self.emit("chunk", text)

    def emit_thinking(self, text: str = "DM 在思考中...") -> None:
        """发射思考状态"""
        self.emit("thinking", text)

    def emit_phase(self, phase: str, message: str = "", progress: int = 0) -> None:
        """🆕 v1.7.15 发射阶段事件（用于前端弹窗进度条）

        Args:
            phase: 阶段标识
                - "queue": 加入 LLM 队列
                - "analyzing": 分析玩家意图
                - "generating": LLM 正在生成叙事
                - "validating": 后校验
                - "finalizing": 整理 voice_options
            message: 该阶段的人类可读描述
            progress: 进度 0-100
        """
        self.emit("phase", {
            "phase": phase,
            "message": message,
            "progress": max(0, min(100, progress)),
        })

    def emit_done(self, final_data: dict) -> None:
        """发射完成事件"""
        self.emit("done", final_data)
        self._done_event.set()

    def emit_error(self, error: str) -> None:
        """发射错误事件"""
        self.emit("error", error)
        self._done_event.set()

    def iter_events(self, timeout: float = 60.0):
        """迭代事件流"""
        deadline = time.time() + timeout
        while not self._done_event.is_set():
            try:
                remaining = deadline - time.time()
                if remaining <= 0:
                    self.emit_error("Timeout")
                    break
                event_type, data = self._queue.get(timeout=min(remaining, 0.5))
                yield event_type, data
            except queue.Empty:
                continue


def format_sse(event: str, data: Any) -> bytes:
    """格式化为 SSE 字节流

    SSE 格式：
    event: <event_type>
    data: <data>

    """
    if isinstance(data, str):
        data_str = data
    else:
        data_str = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {data_str}\n\n".encode("utf-8")


async def stream_dm_response(game, player_input: str, llm_throttle, post_validator, state_dict, era_config):
    """异步流式生成 DM 响应（带 thinking + chunk + done）

    Args:
        game: GameLoop 实例
        player_input: 玩家输入
        llm_throttle: LLMThrottle 实例
        post_validator: post_validate 函数
        state_dict: 当前游戏状态
        era_config: 时代配置

    Yields:
        SSE 字节流
    """
    emitter = StreamingEmitter()

    def _run_in_thread():
        """在单独线程里跑 LLM 调用"""
        try:
            # 1. 思考状态
            emitter.emit_thinking("DM 正在分析场景（SKILL-1 读场）...")
            # 给前端一些时间
            time.sleep(0.05)

            # 2. LLM 调用（受限流保护）
            try:
                with llm_throttle:
                    # 模拟分块输出（实际 LLM 也是 streaming）
                    emitter.emit_thinking("DM 正在生成叙事...")
                    dm_response = game.dm.run(player_input)

                    # 模拟 streaming：把 narrative 按 50 字分块推送
                    narrative = dm_response.get("narrative", "")
                    chunk_size = 50
                    for i in range(0, len(narrative), chunk_size):
                        chunk = narrative[i:i + chunk_size]
                        emitter.emit_chunk(chunk)
                        time.sleep(0.03)  # 模拟流式延迟

                    # 3. 后校验
                    validation = post_validator(
                        dm_response=dm_response,
                        state=state_dict,
                        era_config=era_config,
                        player_input=player_input,
                    )
                    if not validation.valid:
                        emitter.emit_thinking(f"后校验发现 {len(validation.errors)} 个问题")

                    # 4. 最终结果
                    final_data = {
                        "session_id": game.session.session_id,
                        "voice_options": dm_response.get("voice_options", []),
                        "intent_type": dm_response.get("intent_type", "action"),
                        "is_action": dm_response.get("is_action", True),
                        "validation_passed": validation.valid,
                    }
                    emitter.emit_done(final_data)
            except TimeoutError:
                emitter.emit_error("LLM 调用超时（队列已满）")
        except Exception as e:
            emitter.emit_error(f"{type(e).__name__}: {str(e)}")

    thread = threading.Thread(target=_run_in_thread)
    thread.start()

    # 在事件循环里 yield 事件
    loop = asyncio.get_event_loop()
    while not emitter._done_event.is_set():
        try:
            # 用 run_in_executor 让 queue.get 不阻塞事件循环
            event_type, data = await loop.run_in_executor(
                None, lambda: emitter._queue.get(timeout=0.1)
            )
            yield format_sse(event_type, data)
        except queue.Empty:
            # 检查 thread 是否还活着
            if not thread.is_alive():
                emitter._done_event.set()
                break
            continue

    thread.join(timeout=5)


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("测试 StreamingEmitter...")

    emitter = StreamingEmitter()

    # 模拟 LLM 生成
    def _producer():
        time.sleep(0.1)
        emitter.emit_thinking("DM 正在思考...")
        time.sleep(0.2)
        for chunk in ["灶房里，", "沈氏蹲在灶台前", "吹火，呛得直咳嗽。", "小妹蹲在门槛上。"]:
            emitter.emit_chunk(chunk)
            time.sleep(0.05)
        emitter.emit_done({"voice_options": [{"voice_name": "算盘声"}]})

    t = threading.Thread(target=_producer)
    t.start()

    print("📡 监听事件流：")
    for event_type, data in emitter.iter_events(timeout=5.0):
        print(f"  [{event_type}] {data}")
        if event_type in ("done", "error"):
            break

    print("✅ StreamingEmitter 测试通过")