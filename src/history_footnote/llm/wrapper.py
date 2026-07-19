"""🆕 v1.7.16 LLM 包装器：超时 + Fallback + Token 日志

核心功能：
1. 统一的 .invoke() / .stream() 接口
2. 超时检测（默认 30 秒）
3. 多 Provider Fallback（minimax → deepseek）
4. Token 消耗统计（JSONL 文件 + 内存）

设计：
- 不是 BaseChatModel 子类（避免与 LangChain 框架耦合过深）
- 而是"代理"模式：接受一个 LLM 实例，提供 .invoke()
- 不支持 fallback 时不报错（静默退化）
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict

logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================
DEFAULT_TIMEOUT = 90.0  # 单次调用超时（秒）🆕 v1.8.7 30→90（minimax 完整 JSON 需 40-60s）
DEFAULT_RETRY_ON_SAME = 1  # 同 provider 重试次数
FALLBACK_CHAIN = ["minimax-anthropic", "deepseek", "minimax-openai"]
# 🆕 v1.8.8 provider 配置（可热加载）
PRIMARY_PROVIDER = "minimax-anthropic"  # 默认主 provider
HEALTHY_PROVIDERS = set()  # 失败后自动从 fallback 移除，恢复后重加
PROVIDER_FAILURE_COUNT = {}  # 失败计数


def get_active_provider() -> str:
    """🆕 v1.8.8 热加载 provider：先 env，再 settings"""
    import os
    # 1. env (启动时设)
    env_p = os.environ.get("LLM_PRIMARY_PROVIDER")
    if env_p and env_p.strip():
        return env_p.strip()
    # 2. settings (.env 文件，运行时可改)
    try:
        from history_footnote.runtime_config import get_setting
        s_p = get_setting("LLM_PRIMARY_PROVIDER", "")
        if s_p and s_p.strip():
            return s_p.strip()
    except Exception:
        pass
    return PRIMARY_PROVIDER
# JSONL 日志文件路径
USAGE_LOG_PATH = Path(os.environ.get(
    "LLM_USAGE_LOG",
    str(Path(__file__).parent.parent.parent / "logs" / "llm_usage.jsonl")
))


# ============================================================
# LLM Usage Logger（线程安全）
# ============================================================
class LLMUsageLogger:
    """LLM 调用日志：JSONL 文件 + 内存聚合"""

    def __init__(self, log_path=None):
        if log_path is None:
            log_path = USAGE_LOG_PATH
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # 内存统计：按 provider 聚合
        self._stats: Dict[str, Dict[str, Any]] = {}
        # 最近 50 条调用（用于面板）
        self._recent: List[Dict[str, Any]] = []
        self._recent_max = 50

    def log(self, record: Dict[str, Any]) -> None:
        """记录一次 LLM 调用"""
        with self._lock:
            # 1. 写 JSONL 文件
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.warning(f"LLM usage log write failed: {e}")
            # 2. 更新内存 stats
            provider = record.get("provider", "unknown")
            if provider not in self._stats:
                self._stats[provider] = {
                    "provider": provider,
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "fallback_calls": 0,  # 因主 provider 失败而调用的次数
                    "timeout_calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "total_latency_ms": 0,
                    "max_latency_ms": 0,
                    "errors": [],
                }
            s = self._stats[provider]
            s["total_calls"] += 1
            if record.get("success"):
                s["successful_calls"] += 1
            else:
                s["failed_calls"] += 1
                error_msg = record.get("error", "unknown")[:200]
                s["errors"].append({
                    "ts": record.get("ts"),
                    "error": error_msg,
                })
                # 只保留最近 10 条错误
                if len(s["errors"]) > 10:
                    s["errors"] = s["errors"][-10:]
            if record.get("fallback"):
                s["fallback_calls"] += 1
            if record.get("timeout"):
                s["timeout_calls"] += 1
            # token
            s["total_input_tokens"] += record.get("input_tokens", 0)
            s["total_output_tokens"] += record.get("output_tokens", 0)
            s["total_tokens"] += record.get("total_tokens", 0)
            # latency
            latency = record.get("latency_ms", 0)
            s["total_latency_ms"] += latency
            s["max_latency_ms"] = max(s["max_latency_ms"], latency)
            # 3. 最近调用
            self._recent.append(record)
            if len(self._recent) > self._recent_max:
                self._recent = self._recent[-self._recent_max:]

    def get_stats(self) -> Dict[str, Any]:
        """获取完整统计"""
        with self._lock:
            # 转为可序列化
            out = {
                "providers": list(self._stats.values()),
                "recent": list(self._recent),
                "totals": {
                    "calls": sum(s["total_calls"] for s in self._stats.values()),
                    "tokens": sum(s["total_tokens"] for s in self._stats.values()),
                    "input_tokens": sum(s["total_input_tokens"] for s in self._stats.values()),
                    "output_tokens": sum(s["total_output_tokens"] for s in self._stats.values()),
                    "latency_ms": sum(s["total_latency_ms"] for s in self._stats.values()),
                    "fallback_count": sum(s["fallback_calls"] for s in self._stats.values()),
                    "timeout_count": sum(s["timeout_calls"] for s in self._stats.values()),
                },
            }
            return out

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return self._recent[-limit:]

    def reset(self) -> None:
        with self._lock:
            self._stats.clear()
            self._recent.clear()


# 全局单例
_usage_logger = LLMUsageLogger()


def get_usage_logger() -> LLMUsageLogger:
    return _usage_logger


# ============================================================
# Token 提取
# ============================================================
def extract_usage(response: Any) -> Dict[str, int]:
    """从 LLM response 提取 token 用量

    LangChain AIMessage 字段：
    - usage_metadata: {input_tokens, output_tokens, total_tokens}
    - response_metadata: {token_usage: {prompt_tokens, completion_tokens, total_tokens}}
    """
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    # 1. AIMessage.usage_metadata
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        um = response.usage_metadata
        usage["input_tokens"] = um.get("input_tokens", 0)
        usage["output_tokens"] = um.get("output_tokens", 0)
        usage["total_tokens"] = um.get("total_tokens", 0)
        return usage
    # 2. AIMessage.response_metadata.token_usage
    if hasattr(response, "response_metadata") and response.response_metadata:
        tu = response.response_metadata.get("token_usage", {})
        if tu:
            usage["input_tokens"] = tu.get("prompt_tokens", 0)
            usage["output_tokens"] = tu.get("completion_tokens", 0)
            usage["total_tokens"] = tu.get("total_tokens", 0)
            return usage
    return usage


# ============================================================
# LLM Wrapper
# ============================================================
class LLMWrapper:
    """LLM 包装器：超时 + Fallback + 日志

    用法：
        wrapped = LLMWrapper(primary_provider="minimax-anthropic")
        # 像普通 LLM 一样使用
        bound = wrapped.bind_tools(tools)  # 透明
        response = bound.invoke([HumanMessage("...")])
    """

    def __init__(
        self,
        primary_provider: str = None,  # 🆕 v1.8.8 None = 用 get_active_provider()
        fallback_chain: Optional[List[str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        retry_on_same: int = DEFAULT_RETRY_ON_SAME,
        era_config: Optional[Dict] = None,
    ):
        self.primary_provider = primary_provider or get_active_provider()  # 🆕 v1.8.8
        self.fallback_chain = fallback_chain or FALLBACK_CHAIN
        # 确保 primary 在最前
        if self.primary_provider not in self.fallback_chain:
            self.fallback_chain = [self.primary_provider] + self.fallback_chain
        else:
            chain = [p for p in self.fallback_chain if p != self.primary_provider]
            self.fallback_chain = [self.primary_provider] + chain
        self.timeout = timeout
        self.retry_on_same = retry_on_same
        self.era_config = era_config or {}
        # 缓存 LLM 实例（per provider）
        self._llm_cache: Dict[str, Any] = {}
        # 锁防止并发创建
        self._create_lock = threading.Lock()
        # 🆕 内部记录 bind_tools 信息（用于 reconstruct）
        self._tools: List[Any] = []

    def _get_llm(self, provider: str) -> Any:
        """获取或创建指定 provider 的 LLM

        失败时返回 None（如缺 API Key），由调用方决定是否跳过
        """
        if provider not in self._llm_cache:
            with self._create_lock:
                if provider not in self._llm_cache:
                    try:
                        from history_footnote.llm_providers import make_llm_for_purpose
                        self._llm_cache[provider] = make_llm_for_purpose(purpose="dm", provider=provider, era_config=self.era_config)  # 🆕 v2.7
                        logger.info(f"[LLMWrapper] Created LLM: {provider}")
                    except Exception as e:
                        logger.warning(f"[LLMWrapper] Failed to create {provider}: {e}")
                        self._llm_cache[provider] = None
        return self._llm_cache[provider]

    def bind_tools(self, tools: List[Any], **kwargs) -> "LLMWrapper":
        """🆕 绑定 tools（透明代理），返回新 wrapper

        新 wrapper 内部每个 provider 都 bind 了 tools

        🆕 v2.7+：接受 **kwargs 透传给底层
        - cache_control={"type": "ephemeral"} → tools 整体加 cache breakpoint
        - 注意：当前 MiniMax-M3 端点**不支持** tools cache_control
          （实测：HTTP 200 OK 但 LangChain parse 失败）
        - 暂时不传 cache_control；如未来 MiniMax 修复，可通过 kwargs 启用
        """
        new_wrapper = LLMWrapper(
            primary_provider=self.primary_provider,
            fallback_chain=self.fallback_chain,
            timeout=self.timeout,
            retry_on_same=self.retry_on_same,
            era_config=self.era_config,
        )
        new_wrapper._tools = list(tools)
        # 立即 bind_tools 到所有 provider 的 LLM（懒加载）
        for provider in new_wrapper.fallback_chain:
            base_llm = new_wrapper._get_llm(provider)
            if base_llm is None:
                logger.warning(f"[LLMWrapper] Skipping {provider} (creation failed)")
                continue
            if hasattr(base_llm, "bind_tools"):
                # ⚠️ 当前禁用 cache_control kwargs 透传（MiniMax-M3 不支持）
                # 如需启用：把下面改成 base_llm.bind_tools(tools, **kwargs) + try/except TypeError
                new_wrapper._llm_cache[provider] = base_llm.bind_tools(tools)
                logger.debug(f"[LLMWrapper] bind_tools on {provider}: {len(tools)} tools")
        return new_wrapper

    @property
    def _llm_with_tools(self) -> Any:
        """兼容 dm_agent 用的 _llm_with_tools 属性"""
        return self._get_llm(self.primary_provider)

    def _invoke_with_timeout(self, llm: Any, messages: List, timeout: float):
        """在独立线程中调用 LLM，主线程等待超时"""
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(llm.invoke, messages)
        try:
            return future.result(timeout=timeout)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def invoke(self, messages: List, timeout: Optional[float] = None) -> Any:
        """调用 LLM，超时则切换到 fallback provider

        Returns:
            AIMessage 响应对象

        Raises:
            RuntimeError: 所有 provider 都失败
        """
        timeout = timeout or self.timeout
        request_id = str(uuid.uuid4())[:8]
        errors = []

        for provider_idx, provider in enumerate(self.fallback_chain):
            is_fallback = provider_idx > 0
            # 同 provider 重试
            for attempt in range(self.retry_on_same + 1):
                llm = self._get_llm(provider)
                ts_start = time.time()
                timeout_occurred = False
                error_msg = None
                success = False
                usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                try:
                    logger.info(
                        f"[LLMWrapper:{request_id}] invoke provider={provider} "
                        f"attempt={attempt + 1} timeout={timeout}s"
                    )
                    response = self._invoke_with_timeout(llm, messages, timeout)
                    latency_ms = int((time.time() - ts_start) * 1000)
                    success = True
                    usage = extract_usage(response)
                    # 记录日志
                    _usage_logger.log({
                        "ts": datetime.now().isoformat(),
                        "request_id": request_id,
                        "provider": provider,
                        "fallback": is_fallback,
                        "attempt": attempt + 1,
                        "success": True,
                        "timeout": False,
                        "latency_ms": latency_ms,
                        **usage,
                    })
                    # 如果是 fallback，记录降级日志
                    if is_fallback:
                        logger.warning(
                            f"[LLMWrapper:{request_id}] ✨ FALLBACK SUCCESS: "
                            f"primary failed, {provider} returned in {latency_ms}ms"
                        )
                    return response
                except FuturesTimeout:
                    timeout_occurred = True
                    error_msg = f"timeout after {timeout}s"
                    latency_ms = int((time.time() - ts_start) * 1000)
                    logger.warning(
                        f"[LLMWrapper:{request_id}] ⏱️  TIMEOUT: provider={provider} "
                        f"after {timeout}s, attempt={attempt + 1}"
                    )
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)[:200]}"
                    latency_ms = int((time.time() - ts_start) * 1000)
                    logger.warning(
                        f"[LLMWrapper:{request_id}] ❌ ERROR: provider={provider} "
                        f"attempt={attempt + 1} {error_msg}"
                    )
                # 记录失败的调用
                _usage_logger.log({
                    "ts": datetime.now().isoformat(),
                    "request_id": request_id,
                    "provider": provider,
                    "fallback": is_fallback,
                    "attempt": attempt + 1,
                    "success": False,
                    "timeout": timeout_occurred,
                    "latency_ms": latency_ms,
                    "error": error_msg,
                    **usage,
                })
                errors.append((provider, error_msg, timeout_occurred))
                # 不重试：直接跳到下个 provider
                break
        # 所有 provider 都失败
        error_summary = "; ".join(
            f"{p}:{'(timeout)' if to else e[:100]}"
            for p, e, to in errors
        )
        raise RuntimeError(
            f"所有 LLM provider 都失败 ({len(errors)} 个): {error_summary}"
        )


# ============================================================
# 全局 wrapper 工厂
# ============================================================
_wrapper_cache: Dict[str, LLMWrapper] = {}
_wrapper_lock = threading.Lock()


def get_wrapped_llm(
    primary_provider: str = "minimax-anthropic",
    era_config: Optional[Dict] = None,
) -> LLMWrapper:
    """获取包装后的 LLM（缓存版）"""
    key = primary_provider
    with _wrapper_lock:
        if key not in _wrapper_cache:
            _wrapper_cache[key] = LLMWrapper(
                primary_provider=primary_provider,
                era_config=era_config,
            )
        return _wrapper_cache[key]


def clear_wrapper_cache() -> None:
    """清空 wrapper 缓存（用于测试）"""
    with _wrapper_lock:
        _wrapper_cache.clear()
