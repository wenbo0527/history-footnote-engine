# CHANGELOG

历史注脚体验引擎的所有重要变更记录。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

详细问题记录见 [ISSUES.md](file:///Users/mac/Documents/trae_projects/history_footnote/ISSUES.md)。

---

## [v1.6.7] - 2026-07-04

### 🐛 修复：SKILL 元数据泄漏到玩家界面

玩家看到 `=== COMPILED SKILLS ===` 等 DM 后台配置信息，而不是故事情节。

**架构重构亮点**：
- 新增 `narrative_sanitizer.py` 单一权威模块（267 行）
- 4 个文件（dm_agent / game_loop / dm_skills / web_server）改用此模块
- 删除 11 个 JS 正则重复实现
- 删除后端 2 次重复清洗

**修改文件**：
- ➕ `src/history_footnote/narrative_sanitizer.py`（新增）
- ➕ `scripts/test_skill_leak_fix.py`（新增，8 个测试）
- 🔧 `src/history_footnote/dm_agent.py`（-52 行）
- 🔧 `src/history_footnote/web_server.py`（-38 行）
- 🔧 `src/history_footnote/game_loop.py`（-6 行）

---

## [v1.6.6] - 2026-07-04

### ✨ 新增：明朝名词字典 tooltip

- `term_glossary.py`：41 个核心名词 + 63 个同义词
- 10 个分类（经济/科举/制度/地理/物产/货币/身份/习俗/教育/官职）
- 自动高亮未读名词 + 鼠标悬停 tooltip
- 侧边栏 `📚 名词表` 弹层（带搜索）
- **开发中修复 XSS 漏洞**（get_term_html 未 escape 用户/字典值）

---

## [v1.6.5] - 2026-07-04

### 🐛 修复：家庭信息格式 + Enter 快捷键

**两个用户反馈**：
1. 家庭信息显示原始程序格式（如 `spouse：周氏`、`children：["大毛","二丫"]`）
2. 移动端 Enter 键无法提交（必须点"提交"按钮）

**修复**：
- ✅ 翻译 8 个英文 key 为中文（spouse→妻子 等）
- ✅ 数组用「、」分隔（不是 JSON）
- ✅ 裸 Enter 提交（移动端友好）
- ✅ Shift+Enter / Alt+Enter 换行（多行支持）

---

## [v1.6.4] - 2026-07-04

### 🐛 修复：NPC 混淆（上下文断裂）

**用户报告**：
> "我正和'张寡妇'谈租织机，下一回合 DM 突然让我和'陈三'说话。"

**根因**：system prompt 只注入场景标签（如"织机前"），没有上回合的完整叙事。

**修复**：
- ✅ 新增 `_build_recent_context_for_prompt()` 方法
- ✅ 注入最近 3 回合：玩家行动 + 摘要 + 叙事前 400 字
- ✅ 加"重要提示"指令禁止 LLM 切换 NPC/场景
- ✅ state_ref 增加 `recent_narratives` 字段（供 Mock LLM）

---

## [v1.6.3] - 2026-07-04

### ✨ 新增：剧情回顾功能

**用户需求**：
> "玩到第 30 回合就忘了前面发生了什么。"

**双层叙事保留架构**：
- `narrative_recent`：最近 20 回合完整叙事
- `narrative_archive`：早期最多 100 回合 200 字摘要
- 玩家可回忆 120+ 回合
- 存档增加 ~9KB（可控）

---

## [v1.6.2] - 2026-07-04

### 🎉 重大更新：移动端适配 + 全面性能优化

本版本完成所有 P0 + P1 + P2 性能 + Token 优化，新增 4 个模块。

**移动端适配**：
- ✅ viewport meta + 3 个 @media 断点（1024 / 768 / 480）
- ✅ 用 `100dvh` 替代 `100vh`（解决 iOS URL 栏问题）
- ✅ visualViewport API 处理 iOS 键盘
- ✅ 字号 16px+（防 iOS 缩放）、按钮 44px+（Apple HIG）

**性能优化**：见 4 个新增模块。

### ✨ 新增 (Added)

#### 资源全局缓存层 (P0)
- **`resource_cache.py`**：4 个全局缓存
  - `load_era_config()`：era.json 缓存（替代每回合 json.loads）
  - `get_llm()`：LLM Provider 缓存（替代每回合 ChatAnthropic 构造）
  - `get_save_manager()`：SaveManager 单例（替代每回合新建）
  - `warm_era_configs()`：启动时预热所有时代

#### SKILL 选择性注入 (P1)
- **`skill_selector.py`**：按 intent_type 选择需要的 SKILL
  - `select_skills(intent_type, state)`：选择 2-4 个 SKILL
  - `filter_skill_directive(directive, selected_skills)`：过滤完整 directive 文本
  - inquire 节省 75%，describe 节省 62%，action 节省 50%

#### SSE Streaming 输出 (P1)
- **`streaming.py`**：SSE 事件流
  - `StreamingEmitter`：线程安全事件队列
  - `format_sse()`：SSE 字节流格式化
  - `stream_dm_response()`：异步流式生成器
- **`/api/input_stream` 端点**：渐进式返回叙事
  - event: thinking → DM 在思考中...
  - event: chunk → 叙事文本片段
  - event: done → 完成（含 voice_options）

#### Web 增强层 (P2)
- **`web_enhancements.py`**：4 个增强工具
  - `RateLimiter`：滑动窗口限流（60 req/min/IP，LLM 20 req/min/IP）
  - `ToolResultCache`：LRU + TTL 缓存（max 2000, TTL 600s）
  - `MetricsCollector`：性能指标收集器
  - `setup_keepalive()`：HTTP/1.1 + 5s timeout

### 📊 性能优化 (Performance)

#### Web Server 优化
- **A1 era.json 缓存**：0.81ms → 0.2us（**4000x**）
- **A2 LLM Provider 缓存**：200ms → <1ms（**200x**）
- **A3 SaveManager 单例**：5ms → <0.1ms（**50x**）
- **A4 LangGraph graph 复用**：200-300ms → <1ms（**300x**）
- **A6 HTTP keep-alive**：避免 TCP 握手
- **A7 GZIP 压缩**：首屏 40,581 → 11,360 bytes（**72% ↓**）
- **A8 Cache-Control**：HTML 5min 缓存

#### Token 优化
- **KV 缓存（1h TTL）**：长会话 100% 命中率
- **B1 SKILL 选择性注入**：单回合 -300 tokens（action 50%，inquire 75%）
- **D1 Tool 结果缓存**：query_knowledge 100ms → 0.1ms（**1000x**）

### 🆕 监控端点

- **`GET /health`**：健康检查
- **`GET /metrics`**：JSON 格式性能指标
  - 端点统计（count / avg_ms / errors）
  - Tool cache hit rate
  - Rate limiter 状态
  - LLM throttle 状态

### ✅ 测试 (Tests)

新增 1 个测试脚本 + 11 个单元测试：

| 测试脚本 | 测试数 | 通过率 |
|---|---|---|
| **`test_web_enhancements.py`** | **11** | **11/11 ✅** |

**总计**：**45+ 单元测试 + 5 玩家并发测试 + 5 回合真实 LLM 全部通过**

### 📚 文档 (Documentation)

- **[v3.1 完整产品设计文档](docs/历史注脚体验引擎：完整产品设计文档 v3.1.md)**（重写）
  - 加入 v1.6.2 所有 P0/P1/P2 优化（11 项）
  - 5 层并发 + KV 缓存 + SKILL 选择 + SSE + GZIP + 限流 + 监控
  - 综合收益表（v1.6.0 → v3.0 → v3.1）

### 🔧 改动文件清单

**新增（4 个文件）**：
- `src/history_footnote/resource_cache.py`（~250 行）
- `src/history_footnote/skill_selector.py`（~180 行）
- `src/history_footnote/streaming.py`（~200 行）
- `src/history_footnote/web_enhancements.py`（~330 行）

**修改（3 个文件）**：
- `src/history_footnote/dm_agent.py`（graph 复用 + Tool 结果缓存 + SKILL 选择性注入）
- `src/history_footnote/web_server.py`（GZIP + Cache-Control + /metrics + /health + 限流 + keep-alive + /api/input_stream）
- `src/history_footnote/kv_cache.py`（TTL 1h）

**测试新增（1 个文件）**：
- `scripts/test_web_enhancements.py`（11 个测试）

---

## [v1.6.1] - 2026-07-04

### 🎉 重大更新

本版本完成了 v2.0 文档中标记的所有 P0 缺失项，并新增 2 个核心模块（并发 + KV 缓存），大幅提升系统的稳定性、性能和并发能力。

### ✨ 新增 (Added)

#### 后校验 + 重试 + 兜底
- **`post_validator.py`**：5 层校验器
  - 格式校验（narrative 长度、voice_options 数量、必填字段）
  - 铁律校验（已死/被清算人物不能主动互动）
  - 行动边界校验（DM 不能描述玩家影响 cannot_influence 项）
  - 时间一致性校验（time_cost 与叙事时长匹配、时间倒退检测）
  - 史实锚点校验（已触发的 historical_anchors 不能被改写）
- **`generate_safe_narrative()`**：2 次重试失败后模板化兜底叙事
- **`dm_agent.regenerate()`**：带 validation issues 重生成（接收 issues 列表 + prev_narrative）
- **game_loop 集成**：MAX_RETRY=2 重试 + post_validate + 兜底

#### 5 层并发支持
- **`concurrency.py`**：
  - `SessionPool`（线程安全的会话池 + LRU 淘汰 + TTL 自动清理）
  - `SessionLock`（RLock，支持 `with` 语句）
  - `LLMThrottle`（Semaphore 全局并发限流，max_concurrent=3）
  - `AsyncSaveQueue`（异步存档队列 + 文件锁）
  - HTTP_EXECUTOR（20 个线程）
  - 后台清理线程（每 5 分钟清理过期会话）
- **`web_server_concurrent.py`**：并发友好的 web server 入口（备用）
- **web_server.py 改造**：用 SessionPool 替代原 `_SESSIONS` dict
- **game_loop.py 改造**：LLM 调用受 LLM_THROTTLE 保护（with 上下文管理器）

#### KV 缓存集成
- **`kv_cache.py`**：KV 缓存管理器
  - `SystemPromptCache`（跟踪 prompt hash + 命中率统计）
  - `CacheStats`（total_calls / cache_hits / cache_misses / tokens_saved）
  - `GameSessionCache`（单局游戏缓存统计）
  - `estimate_savings()`（节省估算函数）
- **dm_agent.py 改造**：system_prompt 加 `cache_control: {"type": "ephemeral"}`（5min TTL）
- **regenerate() 也走 cache 路径**

#### Tab 式 UX（v1.6+）
- **appendVoiceOptions() 重构**：选项为主，「其他...」按钮（斜体、半透明）
- **showFreeInputTab()**：点「其他」后切换到自由输入 Tab
- **cancelFreeInput()**：玩家可「← 返回选项」回到选项区
- **CSS 样式**：.voice-option-btn.other + .free-input-banner + .free-input-cancel

### 🐛 修复 (Fixed)

| # | 问题 | 解决方案 |
|---|---|---|
| 1 | `'DMAgent' object has no attribute 'selected_identity'` | run/regenerate 每次从 state 同步 |
| 2 | `'NoneType' object cannot be interpreted as an integer`（RLock.acquire timeout） | RLock 不支持 timeout，删除参数 |
| 3 | `'SessionLock' object does not support the context manager protocol` | 加 __enter__/__exit__ |
| 4 | `'dm_response' is not defined` in /api/input | 用 game.state.last_voice_options |
| 5 | `can only concatenate list (not "str") to list`（KV 缓存注入 skill_directive） | msg.content list 兼容性修复 |
| 6 | `KeyError: slice(None, 80, None)`（narrative 是 dict 不是 str） | 测试脚本容错 |
| 7 | voice_options 重复（Tab 切换时） | submitInput 清理旧 voice + banner |
| 8 | 文本框默认显示（诱惑玩家跳过选项） | Tab 式隐藏文本框（点「其他」才出） |
| 9 | scripts/ 30 个过期脚本杂乱 | 归档到 `_archive/` |

### 📊 性能提升 (Performance)

- **KV 缓存**：单回合 input tokens 从 ~5500 降到 ~1200（**78% ↓**）
- **Cache 命中率**：50 回合下 **98%**
- **单局成本**：~$0.30 → ~$0.09（**70% ↓**）
- **首 token 延迟**：3-5s → 1-2s（**50% ↓**）
- **并发能力**：单进程 5-10 → 4 workers × 2 threads 30-50 个同时玩家

### ✅ 测试 (Tests)

新增 4 个测试脚本 + 22 个单元测试：

| 测试脚本 | 测试数 | 通过率 |
|---|---|---|
| `test_post_validator.py` | 7 | 7/7 ✅ |
| `test_concurrency.py` | 8 | 8/8 ✅ |
| `test_kv_cache.py` | 7 | 7/7 ✅ |
| `test_concurrent_real.py` | 5 玩家并发 | 5/5 ✅ |

**所有 30+ 单元测试通过 + 5 玩家真实并发压力测试 5/5 通过**。

### 📚 文档 (Documentation)

- **[v3.0 完整产品设计文档](docs/历史注脚体验引擎：完整产品设计文档 v3.0.md)**：
  - 加入 v1.6+ 所有实现（post_validate、并发、KV 缓存、Tab 式 UX）
  - 5 层并发架构（Layer 1-5 详细设计）
  - KV 缓存架构（3 层策略 + 实测数据）
  - 完整测试覆盖报告
- **[WORK_SUMMARY.md](docs/WORK_SUMMARY.md)**：v1.6+ 工作总结（Agent + 知识库重点）

### 🔧 改动文件清单

**新增（4 个文件）**：
- `src/history_footnote/post_validator.py`（~300 行）
- `src/history_footnote/concurrency.py`（~350 行）
- `src/history_footnote/kv_cache.py`（~200 行）
- `src/history_footnote/web_server_concurrent.py`（~150 行）

**修改（4 个文件）**：
- `src/history_footnote/dm_agent.py`（+100 行 cache_control + regenerate）
- `src/history_footnote/game_loop.py`（+50 行重试机制 + LLM_THROTTLE）
- `src/history_footnote/web_server.py`（+200 行 SessionPool 集成 + Tab 式 UX）
- `docs/历史注脚体验引擎：完整产品设计文档 v3.0.md`（重写）

**测试新增（4 个文件）**：
- `scripts/test_post_validator.py`
- `scripts/test_concurrency.py`
- `scripts/test_kv_cache.py`
- `scripts/test_concurrent_real.py`

---

## [v1.5.x] - 2026-07-03

### ✨ 新增 (Added)

- **8 步初始化向导**：时代 → 世界画卷 → 性别 → 位置 → 身份 → 生活 → 人设 → 开始
- **位置锁定系统**：6 个盛泽镇地点 → 6 个 identity 映射
- **DE 风格 voice_options**：每回合 2-4 个内在声音选项
- **describe 类型**：玩家补充身份/环境不消耗行动点
- **character 传递修复**：后端接收 character → GameLoop → _print_opening 用 custom_character
- **开局 voice_options**：appendOpeningVoiceOptions 渲染 3 个预定义选项
- **GameState.last_voice_options**：voice_options 持久化（存档可恢复）
- **voice_option 双击防护**：_submitting 锁
- **DOM 顺序**：insertBefore(input-area)
- **intent_text 空字符串防护**：trim + 早返

### 🐛 修复 (Fixed)

- 开屏循环（renderWizard 无限递归）
- /api/start ValueError
- DM 人设完全没用
- 开局没 voice_options
- pacing_anchors 重复 + 重复触发

---

## [v1.4.x] - 2026-06

### ✨ 新增 (Added)

- **8 SKILL 编排层**：SKILL-1 读场判断 / SKILL-2 节奏控制 / SKILL-3 线索投放 / SKILL-4 史实锚定 / SKILL-5 价值观发声 / SKILL-6 失败叙事化 / SKILL-7 三层裁判 / SKILL-8 认知框架锁定
- **DE 风格借鉴**：Disco Elysium 风格技能即性格的设计
- **4 时间模式**：slow_time / now_time / abstract_time / sharp_cut
- **pacing_anchors 配置**：史实锚点 + 时间模式
- **failure_mappings**：失败叙事化转化
- **cognitive_frames**：路线 → 信息过滤
- **voices**：内在声音定义
- **action_points_max**：按身份差异化行动点

---

## [v1.3.x] - 2026-05

### ✨ 新增 (Added)

- **行动点系统**：每月固定 3-4 个行动点，耗尽才跳月
- **time_cost 判定规则**：0/1/2/3 行动点对应不同行动深度
- **4 阶段行为模型**：阶段 0（SKILL 编排）+ 阶段 1（态势）+ 阶段 2（叙事）+ 阶段 3（确认）

---

## [v1.0] - 2026-04

### ✨ 初始版本 (Initial)

- **单 Agent + 5 Tool 架构**
- **规则引擎**：9 个方法（check_action / check_forced_events / check_triggers / ...）
- **记忆管理**：三层记忆（工作/情节/语义）
- **知识库**：background 层
- **史实约束**：铁律/边界/范围（无后校验）
- **DM Agent System Prompt 模板**

---

## 图例

- 🎉 重大更新
- ✨ 新增功能
- 🐛 Bug 修复
- 📊 性能提升
- ✅ 测试
- 📚 文档
- 🔧 改动文件