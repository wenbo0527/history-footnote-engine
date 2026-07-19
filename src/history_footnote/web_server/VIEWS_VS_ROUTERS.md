# 🆕 v2.10.9 web_server 分层说明

## 三层职责

```
┌─────────────────────────────────────────────────────────┐
│  routers/ (HTTP 边界层)                                     │
│  ─ 19 个文件,60+ endpoint                                   │
│  ─ 函数命名: handle_GET_xxx / handle_POST_xxx                 │
│  ─ 职责: 解析 HTTP 请求 → 调 views/* → 返回 JSON 响应          │
│  ─ 可依赖: views/, handler_base, 业务模块                       │
└────────────────────────┬────────────────────────────────┘
                         │ 正常调用
┌────────────────────────▼────────────────────────────────┐
│  views/ (业务编排层)                                         │
│  ─ 2 个文件: format_state.py (纯函数), session.py (会话管理)    │
│  ─ 职责: 业务逻辑编排,不涉及 HTTP                              │
│  ─ 🆕 v2.10.9 P2-2: 禁止反向 import routers/                 │
└────────────────────────┬────────────────────────────────┘
                         │ 正常调用
┌────────────────────────▼────────────────────────────────┐
│  handler_base.py / 业务模块 / saves/                          │
└─────────────────────────────────────────────────────────┘
```

## 命名边界

| 关注点 | routers/ | views/ |
|---|---|---|
| HTTP 状态码、Header、Cookie | ✅ | ❌ |
| 解析 query / body JSON | ✅ | ❌ |
| 业务编排（如 session 创建） | ⚠️ 调 views | ✅ |
| 数据序列化（如 game → dict） | ❌ | ✅ (format_state.py) |
| 会话管理（如 session 池） | ❌ | ✅ (session.py) |

## 关键约束

### ✅ 允许
- `routers/handle_POST_input` 调用 `views/session.new_session()`
- `routers/state/format_response` 调用 `views/format_state.format_state()`
- `views/format_state` 引用业务模块（narrative/, rule/, saves/...）

### ❌ 禁止
- **views → routers 反向依赖**（🆕 v2.10.9 P2-2 修复）
  - 违规示例：`from history_footnote.web_server.routers.input import X`
  - 修复方式：在 views/ 层 inline 一个简化版（不依赖 LLM / HTTP 边界）
  - 验证：`tests/test_v2109_views_no_reverse_dep.py`

## 历史背景

### 循环依赖来源

`views/session.py` 在存档加载时，原本有：
```python
from history_footnote.web_server.routers.input import _context_aware_voices
```

这是**分层错误**：
- views/session.py 是业务层（创建 session / 加载存档）
- routers/input.py 是 HTTP 层（处理 /api/input 请求）
- 业务层不应依赖 HTTP 层

### P2-2 修复

在 `views/session.py` 末尾 inline `_load_fallback_voices()` 函数：
- 关键字匹配，零 LLM 成本
- 等价于 `routers/input.py._fallback_keyword_voices()`
- 注释说明存档加载场景无需 LLM

### 长期演进

如果未来 views 与 routers 的边界变复杂，考虑：
1. 抽出 `services/` 层（业务核心，views 和 routers 都依赖）
2. 把 `_context_aware_voices` 移到 `narrative/voices.py`（已存在的业务模块）
3. 引入依赖注入框架（但当前规模不必要）