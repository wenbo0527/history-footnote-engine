# API 字段名规范（v1.7.23）

## 核心原则

1. **统一复数集合名**（list/dict of items）: `archives`, `options`, `voice_options`, `narratives`, `recents`
2. **`last_*` 前缀** = 上一回合的值（与 `recent_*` 不同）
3. **`recent_*` 前缀** = 最近 N 个回合的 list
4. **错误响应**统一用 `{"error": "msg", "error_id": "..."}`（含 error_id 用于排查）

## 端点字段规范

| 端点 | 关键字段 | 说明 |
|---|---|---|
| `POST /api/start` | `session_id, last_voice_options, recent_narratives, ...` | 开局 |
| `POST /api/input` | `recent_narratives[-1].narrative, last_voice_options, ...` | 普通回合 |
| `POST /api/input_stream` | SSE events + `event: done` 含全量 | 流式回合 |
| `GET /api/state?session_id=X` | 全 state | 状态查询 |
| `POST /api/recap` | `recent[] / archive[]` | 剧情回顾 |
| `GET /api/archives` | `archives[]` (list) | 存档列表 |
| `POST /api/llm/stats` | `totals, providers` | LLM 统计 |
| `POST /api/sanitize` | `cleaned` | 清洗 |
| `POST /api/render_narrative` | `html` | 渲染 |
| `POST /api/merge_voice_options` | `options, source` | 选项合并 |
| `POST /api/extract_terms` | `new_terms, marked_text` | 词条提取 |

## 不再支持的字段

| 旧字段 | 状态 | 替换为 |
|---|---|---|
| `sessions` (dict) | ❌ v1.7.23 后 | `archives` (list) |
| `narratives` (flat) | ⚠️ deprecated | `recent_narratives` / `recent` |
| `merged` | ❌ v1.7.23 后 | `options` |
| `voice_options` (string) | ❌ v1.7.0 后 | `last_voice_options` (list of dict) |
| `round` (R0) | ⚠️ 默认 1 | `round_number` (设计如此) |

## 添加新端点 checklist

- [ ] 端点路径以 `/api/` 开头
- [ ] 错误响应包含 `error` 字段（+ `error_id` UUID 短串）
- [ ] 成功响应符合上表字段规范
- [ ] 跑 `python scripts/generate_api_doc.py` 自动更新 OpenAPI
- [ ] 写测试到 `scripts/test_*.py`（用 `request_status` / `request_ok` 辅助）

## 工具

- `scripts/generate_api_doc.py` — 从 web_server.py AST 扫描，生成 OpenAPI 3.0
- `scripts/test_api_field_consistency.py` — 验证所有端点响应字段符合规范