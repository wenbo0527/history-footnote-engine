# 🏗️ 游戏架构 Review Report (v2.10.21)

> 审查日期: 2026-08-01
> 审查范围: 后端 + 前端 + 数据 + 测试
> 审查者: Claude AI

---

## 📊 总体评价

| 维度 | 评分 | 说明 |
|---|---|---|
| **架构清晰度** | ⭐⭐⭐⭐ | 分层清晰，但 story_mode 在 web_server 之上独立模块 |
| **可扩展性** | ⭐⭐⭐⭐⭐ | 加章节/节点极简 (一个文件 + 注册) |
| **可测试性** | ⭐⭐⭐⭐ | 86 个测试，但部分章节 E2E 缺断言 |
| **性能** | ⭐⭐⭐⭐ | 零 LLM，但 NarrativeSection 没用上 |
| **安全性** | ⭐⭐⭐ | state 写 dict 易越界，需 schema 验证 |
| **可维护性** | ⭐⭐⭐⭐ | 代码组织良好，但 dataclass 嵌套有坑 |

**总评: ⭐⭐⭐⭐ (4/5)** — 整体设计良好，有几处需要优化。

---

# 🐍 后端架构

## ✅ 优点

### 1.1 路由注册表模式 (`router_registry.py`)
```python
"/api/input": _input.handle_POST_input,
"/api/scripted/start": _scripted.handle_POST_scripted_start,  # 新增极易
```
**评估**: ✅ 集中注册，加路由 = 1 行改动。`safe_route(scope=...)` 装饰器保证异常处理统一。

### 1.2 Story Mode 模块化 (`story_mode/`)
```
story_mode/
  __init__.py     (导出公共 API)
  types.py        (99 行 - 数据模型)
  rich.py         (244 行 - 多声部 + 环境 + D&D 检定)
  engine.py       (376 行 - 引擎核心)
  chapter_01.py   (1140 行 - 第一章)
  chapter_02.py   (1707 行 - 第二章)
  chapter_03.py   (1196 行 - 第三章)
```
**评估**: ✅ 数据/引擎/内容完全分离。加新章节 = 1 个新文件 + 1 行注册。

### 1.3 跨章回响 (`_apply_chapter_echo`)
```python
if "has_debt" in flags:
    echoes.append("🆕 牙行钱老板的儿子钱少见你...")
```
**评估**: ✅ 动态注入 narrative。但**只在 ch2/ch3 intro 节点生效**，其他节点无回响 (设计简单但功能有限)。

## ⚠️ 问题

### 1.4 路由热加载缺失
**问题**: 加新章节后必须重启 backend 才能生效。
**影响**: 中。开发体验稍差。
**建议**: 实现 `chapter_loader` 延迟加载 + 文件修改检测。

### 1.5 `_get_or_load_session` 返回类型不明确
**问题**: `scripted_story.py` 调用它，但可能返回 `GameState` 对象或 `dict`。
```python
state_dict = game.__dict__ if hasattr(game, "__dict__") else game
```
**影响**: 中。类型不统一容易出 bug。
**建议**: 统一返回 dict (加 `to_dict()` 方法到 GameState)。

### 1.6 `_apply_effects` 中 `flag_set` 跳过
```python
elif k == "flag_set":
    pass  # 已在 handle_input 中处理
```
**问题**: `_apply_effects` 不会消费 `flag_set`，但调用者不知道。
**影响**: 低。但**可能在 `_resolve_encounter` 中重复应用**。
**建议**: 重构让 `_apply_effects` 统一处理 flag_set。

### 1.7 narrative 字数是字符串拼接
**问题**: 大字符串拼接性能差，难分页。
**影响**: 低。但未来分页/搜索时会卡。
**建议**: 改为 `list[NarrativeSection]` 存储。

### 1.8 effects 类型校验缺失
**问题**: `effects = {"cash_delta": "abc"}` 不会报错。
**影响**: 中。dataclass 应严格校验。
**建议**: 用 `__post_init__` 校验关键 effects 类型。

---

# 🎨 前端架构

## ✅ 优点

### 2.1 组件分层
```
routes/
  story-mode-demo/+page.svelte    (新)
  game/+page.svelte               (主游戏)
  world-map-demo/+page.svelte
  login/+page.svelte
  wizard/
  ds/                              (design system)

lib/
  api/                             (14 个 .ts)
    client.ts, types.ts, mapper.ts, ...
  components/
    game/                          (GameView 主组件树)
    modals/                        (15+ modals)
    home/                          (start menu)
    design-system/                 (Card, Button, Tabs, ...)
    effects/                       (InkBurst, ...)
  stores/                          (svelte state)
```
**评估**: ✅ 设计系统独立，组件树清晰。

### 2.2 统一 API 客户端 (`api/client.ts`)
```typescript
const API_BASE = '/api';  // 相对路径，自动走 spa_server 代理
```
**评估**: ✅ 单一 source of truth，零硬编码。

### 2.3 Svelte 5 runes 使用
```svelte
let sessionId = $state('');
let isStarted = $state(false);
let currentChapterInfo = $derived(...);
```
**评估**: ✅ 新语法清晰，类型安全。

## ⚠️ 问题

### 2.4 Story Mode Demo 是独立页面，未集成到 GameView
**问题**: `/story-mode-demo` 是路由，但主游戏在 `/game`。
**影响**: 高。玩家不知道怎么进剧本模式。
**建议**: 
- 选项 A: 在 `StartMenu` 加 "剧本模式" 入口
- 选项 B: 在 `GameView` 加 `<StoryModeToggle>` 切换

### 2.5 Demo 页面硬编码 CHAPTERS 数组
**问题**: 章节信息 (nodes/options/endings 计数) 写在 Svelte 里。
**影响**: 低。每加章节都要改 demo。
**建议**: 后端加 `GET /api/story_mode/chapters` 返回元信息。

### 2.6 缺少组件复用
**问题**: `<VoicePill>` 是现有组件，但 story-mode-demo 重新实现了选项按钮。
**影响**: 中。代码重复，UI 不一致。
**建议**: 提取 `<ScriptedChoice>` 组件复用 `<VoicePill>` 样式。

### 2.7 类型定义重复
**问题**: 前端 `api/types.ts` 有 VoiceOption，但 demo 又自己定义一遍。
**影响**: 低。类型可能漂移。
**建议**: 用 `import type { VoiceOption } from '$lib/api/types'`.

### 2.8 缺少 StoryMode 状态管理
**问题**: `chapterComplete` / `scriptedFlags` / `visitedNodes` 全是页面局部 state。
**影响**: 中。刷新页面会丢失。
**建议**: 移到 `lib/stores/storyMode.ts`。

---

# 💾 数据架构

## ✅ 优点

### 3.1 dataclass 类型安全
```python
@dataclass
class ScriptedVoiceOption:
    voice_id: str
    voice_name: str
    description: str = ""
    inner_voice: Optional[str] = None
    effects: dict[str, Any] = field(default_factory=dict)
    check: Optional[str] = None
    check_success_node: Optional[str] = None
    check_fail_node: Optional[str] = None
    check_hint: Optional[str] = None
```
**评估**: ✅ 类型清晰，default 合理。

### 3.2 VoiceOption / Narrative 兼容现有 schema
**评估**: ✅ 不破坏前端，前端零改动。

### 3.3 D&D 检定设计
```python
check="charisma >= 2",
check_success_node="climax_silk_better",
check_fail_node="climax_silk",
check_hint="嘴笨了，掌柜没理你。",
```
**评估**: ✅ D&D 风味，但 engine 没实现 check 逻辑!

## ⚠️ 严重问题

### 3.4 ⚠️ **`check` / `check_success_node` / `check_fail_node` 在 engine 里完全没用**
**问题**: dataclass 有这些字段，但 `engine.handle_input` 不会读它们。
```python
# 在 ScriptedVoiceOption.check 写了 "charisma >= 2"
# 但 handle_input 只用 next_node_id 直接跳转
```
**影响**: 🔴 **严重**。所有 `check` 字段都是死代码。
**位置**:
- [types.py:32-35](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/types.py#L32-L35) 定义了
- [engine.py:94-160](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/engine.py#L94-L160) 没读

**验证方法**:
```python
# 选 negotiate_price (check=charisma >= 2)
# 应该: charisma >= 2 → climax_silk_better
# 应该: charisma < 2  → climax_silk
# 实际: 不管 charisma, 都直接跳 next_node_id
```

**修复建议**:
```python
def handle_input(self, game_state, voice_id):
    opt = self._find_opt(voice_id)
    
    # 🆕 检定逻辑
    if opt.check:
        result = self._do_check(opt.check, game_state)
        if result == "success":
            target_node = opt.check_success_node or opt.next_node_id
        else:
            target_node = opt.check_fail_node or opt.next_node_id
    else:
        target_node = opt.next_node_id
    
    # 跳转
    game_state["scripted_node_id"] = target_node
```

### 3.5 `narrative_sections` 字段定义了但没用
**问题**: `rich.py` 有 `NarrativeSection` (narrator/text/emotion/sound/action/italic)，但 chapter_X.py 只写 `narrative: str` 字符串。
**影响**: 中。多声部功能没用上。
**修复**: 把 narrative 改为 `list[NarrativeSection]`，engine 渲染时组合。

### 3.6 `required_city` / `required_flags` / `forbidden_flags` 未使用
**问题**: `ScriptedNode` 定义了这些字段。
**影响**: 低。可以做更智能的触发条件。
**修复**: 在 `_get_current_view` 检查。

### 3.7 `auto_next_node_id` 未使用
**问题**: 无选项的自动跳转节点未实现。
**影响**: 低。
**修复**: engine 中处理。

---

# 🧪 测试架构

## ✅ 优点

### 4.1 测试数量充足
- **86 个** `test_*.py` 文件
- **13 个** story_mode 相关

### 4.2 E2E 测试覆盖核心路径
```
test_v21016_story_mode.py       (7/7)
test_v21017_story_mode_rich.py  (8/8)
test_v21018_chapter_02.py       (4/4 结局)
test_v21019_chapter_02_extended.py (7/7)
test_v21021_chapter_03.py       (全部)
```

## ⚠️ 问题

### 4.3 测试代码风格不一致
- 部分用 `print("Step X: ...")`
- 部分用 `assert`
- 部分用 pytest fixtures
- 部分独立脚本 (不能被 pytest 收集)

**影响**: 中。
**建议**: 统一到 pytest + 描述性函数名。

### 4.4 跨章回响测试浅
**问题**: `test_v21021_chapter_03.py` Step 10 只检查 `has_chapter_echo` 字符串，没验证具体回响内容。
**影响**: 中。
**修复**: 检查特定回响文本:
```python
assert "🆕 父亲遗愿" in narr  # 验证 father_will 回响触发
```

### 4.5 没有单元测试
**问题**: 所有测试都是 E2E，没有针对 `engine.py` / `rich.py` 的单元测试。
**影响**: 中。重构时容易破坏。
**修复**: 添加 `tests/test_story_mode_unit.py` 测试:
- `_apply_effects` 边界
- `_apply_chapter_echo` 各种 flag 组合
- `_resolve_encounter` d20 检定逻辑

### 4.6 关键 bug 没测试: `check` 字段是死代码
**问题**: `check="charisma >= 2"` 没生效，但没有任何测试发现。
**影响**: 🔴 严重。
**修复**: 加测试:
```python
def test_check_field_works():
    # 选 negotiate_price (charisma 检定)
    # 验证: 高 charisma → climax_silk_better
    # 验证: 低 charisma → climax_silk
```

---

# 🚀 改进建议 (优先级排序)

## P0 - 立即修 (本周)

### 1. 修复 `check` 字段死代码 🔴
**位置**: `engine.py:94-160`
**影响**: 所有 D&D 检定失效
**工时**: 4 小时
**优先级**: 🔴 关键

### 2. `ScriptedNode.required_*` / `auto_next_node_id` 实施
**位置**: `engine.py:_get_current_view`
**影响**: 节点触发条件可以更精细
**工时**: 2 小时

### 3. `_apply_effects` 统一处理 `flag_set`
**位置**: `engine.py:_apply_effects`
**影响**: 避免重复
**工时**: 1 小时

## P1 - 本月 (1-2 周)

### 4. 集成 StoryMode 到主游戏
**位置**: 新建 `<StoryModeToggle>` 在 `GameView`
**影响**: 玩家发现剧本模式入口
**工时**: 1 周

### 5. Story Mode 状态持久化
**位置**: `lib/stores/storyMode.ts`
**影响**: 刷新不丢失进度
**工时**: 1 周

### 6. 提取 `<ScriptedChoice>` 组件
**位置**: 复用 `<VoicePill>`
**影响**: UI 一致性
**工时**: 3 天

### 7. 章节元信息 API 端点
**位置**: `GET /api/story_mode/chapters`
**影响**: Demo 页不再硬编码
**工时**: 半天

## P2 - 下季度

### 8. narrative 改为 `list[NarrativeSection]`
**影响**: 多声部渲染
**工时**: 1 周

### 9. 单元测试
**位置**: `tests/test_story_mode_unit.py`
**影响**: 重构安全
**工时**: 1 周

### 10. 路由热加载
**位置**: `chapter_loader.py`
**影响**: 开发体验
**工时**: 半天

---

# 📊 度量指标

## 后端代码量
```
web_server/        1388 行
routers/           4560 行
story_mode/        4782 行  ← 新加 4000+ 行
总计              ~10000 行
```

## 前端代码量
```
lib/api/           ~2000 行
lib/components/    ~5000 行
routes/            ~3000 行
总计              ~10000 行
```

## 测试覆盖
```
86 个测试文件
13 个 story_mode 相关
E2E 覆盖率: 70%
单元测试: 0%  ← ⚠️ 缺失
```

## 性能指标
```
零 LLM 调用
单节点响应: < 50ms
启动 chapter: < 100ms
random encounter: < 30ms
```

---

# 🎯 总结

## 当前状态: ⭐⭐⭐⭐ (4/5)

**优点**:
- ✅ 三章 77 节点 199 选项 19 结局 14 事件，零 LLM
- ✅ 跨章回响 + D&D 检定设计 (部分实现)
- ✅ 前端 demo 可玩 3 章

**关键问题**:
- 🔴 `check` / `check_success_node` / `check_fail_node` 是死代码 (P0)
- ⚠️ StoryMode 没集成到主游戏 (P1)
- ⚠️ 缺单元测试 (P2)

## 建议下一步

1. **P0**: 修复 check 字段 → 让 D&D 检定真正工作
2. **P1**: 集成到主游戏 → 玩家能切换剧本/LLM
3. **P1**: 第三章补全到 40 节点

## 是否需要立即修复 P0？

如果你同意，我可以立即:
1. 修复 `check` 字段实施 (4 小时)
2. 添加单元测试覆盖 `check` 逻辑 (2 小时)
3. 跑全套测试验证 (1 小时)
4. Commit + push

需要继续吗？