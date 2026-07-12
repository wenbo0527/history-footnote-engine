# ISSUES - 问题与解决记录

> 玩家 / 用户反馈的问题、修复方案、回归测试。
> 与 `CHANGELOG.md` 互补：CHANGELOG 记录"做了什么"，ISSUES 记录"为什么这么做"。

## 📋 目录

- [v1.6.x 系列问题](#v16x-系列问题)
  - [Issue #1: 移动端底部内容被截断 (v1.6.2)](#issue-1-移动端底部内容被截断-v162)
  - [Issue #2: 故事上下文不一致/NPC 混淆 (v1.6.4)](#issue-2-故事上下文不一致npc-混淆-v164)
  - [Issue #3: 家庭字段显示原始程序格式 (v1.6.5)](#issue-3-家庭字段显示原始程序格式-v165)
  - [Issue #4: Enter 键无法提交（移动端）](#issue-4-enter-键无法提交移动端-v165)
  - [Issue #5: SKILL 元数据泄漏到玩家界面 (v1.6.7)](#issue-5-skill-元数据泄漏到玩家界面-v167)
  - [Issue #6: 修复分布散乱（架构问题） (v1.6.7)](#issue-6-修复分布散乱架构问题-v167)
- [v1.6.x 新增功能](#v16x-新增功能)
  - [Feature #1: 剧情回顾 (v1.6.3)](#feature-1-剧情回顾-v163)
  - [Feature #2: 明朝名词字典 tooltip (v1.6.6)](#feature-2-明朝名词字典-tooltip-v166)
- [v2.10.x 系列问题](#v210x-系列问题)
  - [Issue #7: 章节蓝图 chapter2-10 缺失导致玩家卡死 (v2.10.1 W52 P0-1)](#issue-7-章节蓝图-chapter2-10-缺失导致玩家卡死-v2101-w52-p0-1)
  - [Issue #8: LLM JSON 解析失败 9.7% (v2.10.1 W52 P0-2)](#issue-8-llm-json-解析失败-97-v2101-w52-p0-2)
- [未解决问题 / 已知限制](#未解决问题--已知限制)

---

## v1.6.x 系列问题

### Issue #1: 移动端底部内容被截断 (v1.6.2)

**用户报告**：
> "在手机上玩，底部输入框被截断了，看不到"提交"按钮。"

**根因分析**：
| 维度 | 实际情况 |
|---|---|
| viewport | ❌ 无 `<meta name="viewport">`，浏览器按 980px 桌面宽度渲染 |
| CSS | ❌ 无任何 `@media` 断点（侧边栏 320px 占据 50% 屏幕）|
| 布局 | ❌ `body { height: 100vh; overflow: hidden }` 阻塞 `position: sticky` |
| 字号 | ❌ 14px 触发 iOS Safari 自动放大 |
| 触屏目标 | ❌ 按钮 < 44px（Apple HIG 不达标）|

**修复**（commit `33c4406`）：
- ✅ 加 viewport meta + theme-color + apple-web-app
- ✅ 用 `100dvh` 替代 `100vh`（解决 iOS URL 栏变化）
- ✅ 加 3 个响应式断点：1024 / 768 / 480
- ✅ 移动端 sidebar 移到底部（grid-template-areas）
- ✅ textarea font-size ≥ 16px（防 iOS 缩放）
- ✅ 按钮 min-size 44px
- ✅ `window.visualViewport` API 处理 iOS 键盘
- ✅ `-webkit-overflow-scrolling: touch` 弹性滚动

**验证**：
- Chrome headless 截图 375×812 / 768×1024 / 1200×800 全部正确
- 5 玩家并发测试无 regression

**相关文件**：
- `src/history_footnote/web_server.py`（CSS 段 + JavaScript 段）

---

### Issue #2: 故事上下文不一致/NPC 混淆 (v1.6.4)

**用户报告**：
> "我正和'张寡妇'谈租织机的事，下一回合 DM 突然让我和'陈三'说话。张寡妇没说完呢。"

**Bug 截图（用户提供）**：
```
张寡妇听完，没有立刻答应，也没有拒绝。她看了你一眼：
"租钱怎么算？"
...
━━━ 行动点耗尽，进入 1587年3月 ━━━
> 讨价还价
第1回合 · 日常

陈三等着你回话。六匹素绸在柜台上摆着...
```

**根因分析**：
1. system prompt 只注入了 `recent_scenes`（场景标签如"织机前/茶馆"）
2. 和 `recent_inputs`（玩家原话）
3. **没有注入上几回合的完整叙事正文**
4. LLM 只能从场景标签猜 NPC → 张寡妇/陈三混淆

**修复**（commit `b4930c9`）：
- ✅ 新增 `_build_recent_context_for_prompt()` 方法
- ✅ 注入最近 3 回合：玩家行动 + 摘要 + 叙事前 400 字
- ✅ 加"重要提示"指令：明确禁止 LLM 切换 NPC/场景
- ✅ 注入当前关键变量（让 LLM 知道银两/织机状态）
- ✅ state_ref 增加 `recent_narratives` 字段（供 Mock LLM 同步）
- ✅ run() + regenerate() 双路径都更新

**验证**：
- 7 个新单元测试（`test_context_consistency.py`）
- 5 回合真实 LLM 测试：赵里长持续 1-3 回合，沈氏持续 5 回合

**关键测试断言**：
```python
def test_npc_consistency_simulation():
    state.append_narrative(1, "张寡妇说：'租钱怎么算？'...")
    result = method(agent)
    assert "张寡妇" in result, "❌ 张寡妇未保留在上下文中"
```

**相关文件**：
- `src/history_footnote/dm_agent.py:1027-1086`

---

### Issue #3: 家庭字段显示原始程序格式 (v1.6.5)

**用户报告**：
> "我家人的名字显示出来是这样的：· spouse：周氏（桂花） · children：["大毛（9岁）","二丫（5岁）]"

**根因分析**：
- [`web_server.py:1066`](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/web_server.py#L1066) 之前代码：
  ```js
  escapeHtml(typeof v === 'string' ? v : JSON.stringify(v))
  ```
- 数组被 `JSON.stringify()` 直接序列化
- key 是英文（spouse/children/elderly），没翻译

**修复**（commit `263cd84`）：
- ✅ 加 8 个 key 翻译：spouse→妻子、children→子女、elderly→老人、parents→父母等
- ✅ 数组用「、」连接（不是 JSON）
- ✅ 保留 XSS escapeHtml 防护（新增测试验证）
- ✅ 兼容 dict/字符串/数组多种类型

**效果对比**：

| Before | After |
|---|---|
| · spouse：周氏（桂花） | · 妻子：周氏（桂花） |
| · children：["大毛（9岁）","二丫（5岁）"] | · 子女：大毛（9岁）、二丫（5岁） |
| · elderly：老娘沈王氏（58岁...） | · 老人：老娘沈王氏（58岁...） |

**相关文件**：
- `src/history_footnote/web_server.py:1063-1089`

---

### Issue #4: Enter 键无法提交（移动端） (v1.6.5)

**用户报告**：
> "我在手机上输入完了，必须手动点"提交"按钮，键盘上的"完成"按钮没法用。"

**根因分析**：
- 之前只监听 `Ctrl+Enter` 提交
- 移动端没 Ctrl 键 → 完全无法用快捷键
- 桌面端用户也被迫只能用快捷键（多按 Ctrl）

**修复**（commit `263cd84`）：
- ✅ 裸 `Enter` → 提交（移动端友好）
- ✅ `Shift+Enter` / `Alt+Enter` → 换行（保留多行能力）
- ✅ `Ctrl+Enter` / `Cmd+Enter` → 提交（兼容桌面）
- ✅ Placeholder 加快捷键提示

**相关文件**：
- `src/history_footnote/web_server.py:1458-1475`

---

### Issue #5: SKILL 元数据泄漏到玩家界面 (v1.6.7)

**用户报告**：
> "我选了动作，结果给我返回的是一长串配置信息：=== COMPILED SKILLS FOR DM - Round 1B (Continuation) === # COMPILED DM SKILLS - Round 1B ## Generated: ... ## ⏱️ SKILL-2 节奏控制 → now_time ..."

**Bug 截图（用户提供）**：
```
=== COMPILED SKILLS FOR DM - Round 1B (Continuation) ===
# COMPILED DM SKILLS - Round 1B
## Generated: 2027-01-19 22:55:08
## Decision Mode: now_time

### Applied Skills for This Turn:
## ⏱️ SKILL-2 节奏控制 → now_time
  现在时间：正常推进
  时间跨度: 半天
  ...
```

**根因分析**：
1. system prompt 包含 `_build_skill_directive()` 输出的 SKILL 指令段
2. LLM 第二次调用（生成 narrative 时）偶尔把这段复制到 `narrative` 字段
3. JSON 解析失败时，fallback 把整段 LLM 输出塞进 narrative
4. 前端无任何清洗 → 直接显示给玩家

**修复（4 层防御 → 1 层 + 架构重构）**（commit `637e36b`）：

| 层 | 措施 | 状态 |
|---|---|---|
| 1. 源头净化 | `_build_skill_directive` 加 "⚠️ 关键禁忌" 指令 | ✅ 保留 |
| 2. JSON 提取 | 从 markdown 中提取首个 JSON 块 | ✅ 由 sanitizer 接管 |
| 3. 后端清洗 | `narrative_sanitizer.sanitize()` 剥离 SKILL 元数据 | ✅ **统一在这里** |
| 4. 前端兜底 | 调用 `/api/sanitize` 端点 | ✅ **不再本地实现** |

**关键算法改进**（测试中发现的问题）：
- SKILL 段只吃**缩进行**（避免吃后面的真叙事）
- 单行 SKILL 标题也单独清洗
- `min_length` 阈值从 30 降到 5（"米缸里有米"是有效叙事）
- `Decision Mode` / `Generated` 兼容无 `\n` 结尾

**相关文件**：
- `src/history_footnote/narrative_sanitizer.py`（**新增**，267 行）
- `src/history_footnote/dm_agent.py`（-52 行，删除本地实现）
- `src/history_footnote/web_server.py`（-38 行，删除 JS 正则）

---

### Issue #6: 修复分布散乱（架构问题） (v1.6.7)

**用户/我自己反思**：
> "前几次 v1.6.7 的修复散布在 5 个地方：dm_skills / dm_agent / game_loop / web_server（Python 2 份、JS 1 份），而且 game_loop 还做了重复清洗。"

**架构审视**：

| 之前 | 之后 |
|---|---|
| 4 套 Python 正则重复实现 | ✅ 1 套（`narrative_sanitizer.py` 单一权威）|
| 11 个 JS 正则独立维护 | ✅ 0 个（前端调 `/api/sanitize` 端点）|
| 后端清洗 2 次（dm_agent + game_loop）| ✅ 1 次（只在 `extract_narrative_node`）|
| 嵌套在 LangGraph 节点内 | ✅ 独立函数模块（纯函数易测试）|

**是否需要沉淀到 LangGraph 节点**？

**不需要**。理由：
- 清洗是**纯字符串变换**（无状态变化、无决策分支）
- LangGraph 节点适合"决策类"（if-else / 并行 / 状态转换）
- 当前架构："LangGraph 节点 = 编排，纯函数 = 实现" 正是 LangChain 官方推荐
- 如果未来要做"清洗失败时重试 LLM"，再沉淀为节点

**相关文件**：
- `src/history_footnote/narrative_sanitizer.py`（核心模块）
- `scripts/test_skill_leak_fix.py`（8 个测试覆盖边缘 case）

---

## v1.6.x 新增功能

### Feature #1: 剧情回顾 (v1.6.3)

**用户需求**：
> "玩到第 30 回合就忘了前面发生了什么。能不能加个剧情回顾？"

**设计**：双层叙事保留 + 弹层 UI

**实现**（commit `5c2a6c1`）：
- `GameState.narrative_recent`：最近 20 回合完整叙事
- `GameState.narrative_archive`：早期最多 100 回合 200 字摘要
- `GameState.get_recap(recent_count, archive_count)` 方法
- `POST /api/recap` 端点
- 前端 `📖 剧情回顾` 按钮（侧边栏）

**效果**：
- 玩家可回忆 120+ 回合
- 存档增加 ~9KB（可控）

---

### Feature #2: 明朝名词字典 tooltip (v1.6.6)

**用户需求**：
> "什么是'牙行'、'湖丝'？我不懂明朝名词，能否在第一次出现时给个解释？"

**实现**（commit `67fee97`）：
- `term_glossary.py`：41 个核心名词 + 63 个同义词
- 10 个分类：经济/科举/制度/地理/物产/货币/身份/习俗/教育/官职
- 自动高亮未读名词（下划线+?图标）
- 鼠标悬停显示 tooltip
- 玩家读过后标记为"已读"，不再高亮
- 侧边栏 `📚 名词表` 弹层（带搜索）

**示例**：
```html
你去了 <span class="term-new" data-term="牙行">牙行</span>，那里可以...
              ↓ 鼠标悬停
   牙行 [经济]
   明代专门撮合买卖双方的中介机构...
```

**开发中发现 XSS 漏洞**（写测试时发现）：
- `get_term_html()` 没 escape 用户/字典值
- 已修复：所有字段都通过 `escape_html()`

---

## v2.10.x 系列问题

### Issue #7: 章节蓝图 chapter2-10 缺失导致玩家卡死 (v2.10.1 W52 P0-1)

**问题描述**：
> 仅 `chapter1_blueprint.json` 存在（v1 行）。玩家游玩到第 7 章时，`coordinator._init_first_chapter` 抛 `FileNotFoundError`，原代码 silent log 后退出，章节化叙事直接中断，玩家卡死。

**信号源**：
- 真 LLM smoke ERROR：`第 7 章蓝图加载失败: 蓝图文件不存在: /root/.../chapter7_blueprint.json`
- 紧接着：硬编码路径也失败 → "章节化就此退出（无法继续）"

**根因**：
- `eras/{era}/` 只有第 1 章蓝图 JSON
- `coordinator._init_first_chapter` 的两层 try-except 在硬编码失败时仅 `_LOG.error`，不抛
- 玩家卡在当前章节，强制重启也无效（章节状态仍异常）

**修复**（commit `f5d640e`）：
- 3 层 fallback 链路：
  1. LLM 实时生成（如有 `_llm`）
  2. 静态最小可用 blueprint（"第 N 章"+ 应急场景 + W85 5 字段）
  3. 放弃（保留向后兼容，不 raise）
- 新方法 `_static_fallback_init(chapter_id)` 内联应急 blueprint

**验证**：
- `tests/test_w85_p01_blueprint_fallback.py` 7 用例全通过
- mock `facade.init_chapter` 抛 FileNotFoundError → 静态 fallback 自动初始化

**相关文件**：
- `src/history_footnote/chapter/coordinator.py`（`_static_fallback_init` + `_init_first_chapter` 改写）
- `tests/test_w85_p01_blueprint_fallback.py`（7 新测试）

---

### Issue #8: LLM JSON 解析失败 9.7% (v2.10.1 W52 P0-2)

**问题描述**：
> 真 LLM smoke 230s 内 5 个 ERROR + 14 WARN（"章节蓝图校验失败"）。主因 LLM 返回非标准 JSON（`Expecting ',' delimiter` 字符 2264 位错位），JSON 解析失败触发 fallback，章节叙事内容不如 LLM 实时生成。

**信号源**：
- `nohup.out.w52a` + `/tmp/w52_real_llm_smoke.log`
- 主失败模式：LLM 输出长 JSON 时偶尔漏转义换行 / 含 markdown 代码块 / 含括号嵌套

**根因**：
- `route_detector._classify_intent_with_llm` 使用 `re.search(r"\{[\s\S]*\}")` 简易提取
- non-greedy 在第一个 `}` 停下 → 长 JSON 截断
- 不支持 markdown 包裹 / 控制字符 / 加粗标记

**修复**（commit `b75c738`）：
- 改用项目统一工具 `extract_json_from_text`（`narrative_sanitizer.py` W32-W66）
- 5 种容错能力：
  1. markdown ```json ... ``` 包裹
  2. 文本末尾 {...} 块（greedy）
  3. 括号深度匹配（嵌套对象不被截断）
  4. 控制字符清洗（裸换行/制表符）
  5. markdown 加粗清洗（**xxx** → xxx）
- 清理 unused `re` import

**验证**：
- `tests/test_w85_p02_json_tolerance.py` 11 用例全通过
- 全量回归 290/290 PASSED

**相关文件**：
- `src/history_footnote/chapter/route_detector.py`（`_classify_intent_with_llm` 改写）
- `tests/test_w85_p02_json_tolerance.py`（11 新测试）
- `src/history_footnote/narrative_sanitizer.py`（共用工具，无需改）

---

## 未解决问题 / 已知限制

### 限制 1：长局（>100 回合）narrative_archive 仍会截断
**现象**：超过 100 回合后，archive 也会被 LRU 淘汰
**当前缓解**：archive 保留 200 字摘要，丢失信息有限
**未来方案**：v1.7 引入 LLM 智能回顾（动态生成 300 字摘要）

### 限制 2：narrative_sanitizer 用"缩进"判断 SKILL 段边界
**风险**：如果 LLM 输出 SKILL 段内容时不用缩进，会被当作"非缩进真叙事"跳过清洗
**当前缓解**：单行 SKILL 标题 + Decision Mode / Generated 单行也清洗
**未来方案**：增加更多"基于内容"的模式

### 限制 3：term_glossary 词条仅 41 个
**现状**：覆盖常用词，但"牙祭"、"年节"等习俗类词较少
**未来方案**：根据游戏数据动态收录新词（自动提取高频词）

### 限制 4：term_glossary 同义词表手工维护
**风险**：新添加的同义词需手动登记
**未来方案**：AI 自动识别同义词（一对一映射）

---

## 📊 修复时间线（v1.6.2 → v1.6.7）

```
2026-07-04  v1.6.2 移动端适配 (Issue #1)
2026-07-04  v1.6.3 剧情回顾功能 (Feature #1)
2026-07-04  v1.6.4 修复 NPC 混淆 (Issue #2)
2026-07-04  v1.6.5 家庭格式 + Enter 快捷键 (Issue #3, #4)
2026-07-04  v1.6.6 名词字典 tooltip (Feature #2)
2026-07-04  v1.6.7 修复 SKILL 泄漏 + 架构重构 (Issue #5, #6)
```

---

## 🔗 相关文档

- [CHANGELOG.md](file:///Users/mac/Documents/trae_projects/history_footnote/CHANGELOG.md) - 版本变更日志
- [README.md](file:///Users/mac/Documents/trae_projects/history_footnote/README.md) - 项目说明
- `docs/01-decision-log.md` - 决策日志

---

**最后更新**：2026-07-04
**维护者**：AI Assistant + 用户
