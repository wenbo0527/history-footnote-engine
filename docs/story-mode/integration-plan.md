# 🎭 故事模式与主游戏融合方案 (v2.10.22)

> 创建日期: 2026-08-01
> 状态: 待评审

## 📋 问题诊断

当前故事模式是**独立于主游戏之外的孤立系统**:

```
主游戏流:                故事模式流:
─────────              ──────────
StartMenu              /story-mode-demo 路由 (独立页面)
  ↓                      ↓
Wizard (创建角色)        startChapter (独立 session_id)
  ↓                      ↓
/game?session=xxx        /api/scripted/start (独立 API)
  ↓                      ↓
ActionPanel              VoicePill (重复实现)
  ↓                      ↓
submitInput              /api/scripted/input (独立 API)
  ↓
LLM 生成 narrative       静态 narrative 字符串
  ↓                      ↓
NarrativeArea            <pre> 渲染
  ↓
下次玩家输入
```

**核心问题**:
1. 玩家不知道剧本模式存在 (没有入口)
2. 玩家必须选一种模式才能玩 (二选一)
3. 数据双轨: cash/debt/rice/looms 等状态两份
4. UI 重复: VoicePill 重新实现
5. narrative 风格不一致 (LLM 自由 vs 剧本固定)

---

## 🎯 融合目标

**故事模式 = 主游戏的"另一条输入流"**

- ✅ 同一个 session_id, 同一个 game state
- ✅ 同一个 `/game` 路由
- ✅ 同一个 `NarrativeArea` / `ActionPanel` 渲染
- ✅ 玩家在游戏中可切换: LLM 模式 ↔ 剧本模式
- ✅ LLM 失败时自动降级到剧本
- ✅ 剧本进展作为 LLM 提示

---

## 🏗️ 融合架构

### 1. 数据层融合

#### 1.1 扩展 GameState
**位置**: [types.py](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/types.py) → [types.ts](file:///Users/mac/Documents/trae_projects/history_footnote/src/frontend/src/lib/api/types.ts)

```typescript
// 🆕 在 GameState 末尾加
interface GameState {
  ...existing fields...

  // 🆕 v2.10.22: 故事模式状态 (跟主游戏统一存储)
  scripted_mode?: boolean;          // 是否在剧本模式
  scripted_chapter_id?: number;     // 1=家贫, 2=织染, 3=丝绢案
  scripted_node_id?: string;        // 当前剧本节点 (e.g. "intro_1_father_ill")
  scripted_flags?: string[];        // 已解锁 flag (e.g. ["has_debt", "met_qian"])
  scripted_visits?: string[];       // 已访问节点历史
  scripted_chapter_complete?: boolean;
}
```

**好处**:
- 一个 session 一个 state
- 玩家可以从 ch1 玩到 ch3 一气呵成
- 状态无需迁移

#### 1.2 ScriptedVoiceOption 完全复用 VoiceOption
**位置**: [types.py](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/story_mode/types.py)

```python
@dataclass
class ScriptedVoiceOption:
    voice_id: str
    voice_name: str
    description: str = ""          # 🆕 跟 VoiceOption 一致
    intent_text: str = ""          # 🆕 必填 (复用)
    inner_voice: Optional[str] = None
    effects: dict[str, Any] = field(default_factory=dict)
    check: Optional[str] = None
    check_success_node: Optional[str] = None
    check_fail_node: Optional[str] = None
    check_hint: Optional[str] = None
    value_dimension: Optional[str] = None  # 🆕 跟主游戏对齐
```

**好处**:
- 前端 `<VoicePill>` 直接渲染，无需改造
- `submitInput(voice_id=...)` 复用

---

### 2. API 层融合

#### 2.1 路由融合
**位置**: [router_registry.py](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/web_server/router_registry.py)

```python
# 现有路由 (不动)
"/api/input": _input.handle_POST_input,

# 🆕 v2.10.22: 剧本模式 API (保留但改造语义)
"/api/scripted/start": _scripted.handle_POST_scripted_start,
"/api/scripted/input": _scripted.handle_POST_scripted_input,
"/api/scripted/state": _scripted.handle_GET_scripted_state,

# 🆕 v2.10.22: 统一调度 API (新增)
"/api/input_mode": _input.handle_POST_input_mode,  # 玩家在 LLM/剧本间切换
```

#### 2.2 /api/input 增强
**位置**: [input.py](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/web_server/routers/input.py)

```python
def handle_POST_input(handler, body):
    """统一输入入口 (LLM + 剧本)"""
    sid = body.get("session_id")
    inp = body.get("input") or body.get("voice_id")
    
    game = _get_or_load_session(sid)
    state_dict = game.__dict__ if hasattr(game, "__dict__") else game
    
    # 🆕 v2.10.22: 如果剧本模式, 走剧本引擎
    if state_dict.get("scripted_mode"):
        engine = get_engine()
        narr, options, info = engine.handle_input(state_dict, inp)
        # 复用现有 _apply_state_changes 写入
        ...
        return _build_response(game, narr, options, info)
    
    # 否则走 LLM (现有逻辑)
    ...
```

**好处**:
- 玩家不需要切换 API
- `submitInput()` 同一接口
- LLM 失败时自动降级剧本 (已实现)

#### 2.3 /api/scripted/start 改为 chapter 选择
```python
def handle_POST_scripted_start(handler, body):
    """
    🆕 改造: 从"独立启动"改为"章节选择"
    - 已有 session → 启动指定章节 (覆盖 scripted_node_id)
    - 自动从存档恢复之前的 chapter (如已 ch2 完成)
    """
    sid = body.get("session_id")
    chapter_id = body.get("chapter_id", 1)
    
    game = _get_or_load_session(sid)
    engine = get_engine()
    
    # 重置脚本状态
    state_dict = game.__dict__ if hasattr(game, "__dict__") else game
    narr, options = engine.start_chapter(state_dict, chapter_id)
    
    return _build_response(game, narr, options, {...})
```

---

### 3. 前端层融合

#### 3.1 GameView 集成剧本模式
**位置**: [GameView.svelte](file:///Users/mac/Documents/trae_projects/history_footnote/src/frontend/src/lib/components/game/GameView.svelte)

```svelte
<script>
  import { game } from '$lib/stores';
  
  // 🆕 v2.10.22: 剧本模式切换
  let scriptedMode = $derived($game?.scripted_mode ?? false);
  let scriptedChapter = $derived($game?.scripted_chapter_id ?? 0);
  let scriptedNode = $derived($game?.scripted_node_id ?? '');
  
  // 🆕 ActionPanel 接收
  function handleSelectVoice(voice) {
    if (scriptedMode) {
      // 走剧本引擎 (复用 submitInput)
      submitInput({
        session_id: $game.session_id,
        voice_id: voice.voice_id,
        intent_text: voice.intent_text || voice.voice_name,
      });
    } else {
      // 现有 LLM 模式
      submitInput({...});
    }
  }
</script>

{#if scriptedMode}
  <!-- 剧本模式徽章 -->
  <div class="mode-badge scripted">
    🎭 剧本模式 · 第{scriptedChapter}章 · {scriptedNode}
  </div>
{/if}

<ActionPanel ... onselect={handleSelectVoice} />
```

#### 3.2 StartMenu 加剧本入口
**位置**: [StartMenu.svelte](file:///Users/mac/Documents/trae_projects/history_footnote/src/frontend/src/lib/components/home/StartMenu.svelte)

```svelte
<StartMenuCard 
  title="🎭 剧本模式"
  desc="体验固定剧本 (零 LLM)，3 章 77 节点 199 选项"
  onclick={() => goto('/game?scripted=1&chapter=1')}
/>
<StartMenuCard 
  title="🌊 自由模式"
  desc="DM 实时生成 narrative，每次体验都不同"
  onclick={() => goto('/game')}
/>
```

#### 3.3 创建 <StoryModeBadge> 组件
**位置**: `lib/components/game/StoryModeBadge.svelte` (新)

```svelte
<script lang="ts">
  import { game } from '$lib/stores';
  let scripted = $derived($game?.scripted_mode ?? false);
  let chapter = $derived($game?.scripted_chapter_id ?? 0);
  let nodeId = $derived($game?.scripted_node_id ?? '');
</script>

{#if scripted}
  <div class="story-mode-badge">
    🎭 剧本模式
    <span class="chapter">第{chapter}章</span>
    <code class="node">{nodeId}</code>
    <button onclick={() => exitScriptedMode()}>退出</button>
  </div>
{/if}
```

#### 3.4 ActionPanel 不变
`<VoicePill>` 已经能渲染 `inner_voice`, `voice_name`, `intent_text` 等字段。
剧本模式的 voice_options 同样格式, 直接复用。

#### 3.5 NarrativeArea 显示剧本标记
```svelte
{#if $game?.scripted_mode}
  <div class="scripted-marker">📖 剧本节点 · {$game.scripted_node_id}</div>
{/if}
```

---

### 4. GameState mapper 增强
**位置**: [mapper.ts](file:///Users/mac/Documents/trae_projects/history_footnote/src/frontend/src/lib/api/mapper.ts)

```typescript
// 🆕 在 mapBackendState 加
function mapBackendState(raw: any): GameState {
  return {
    ...existing,
    scripted_mode: raw.scripted_mode ?? false,
    scripted_chapter_id: raw.scripted_chapter_id ?? 0,
    scripted_node_id: raw.scripted_node_id ?? '',
    scripted_flags: raw.scripted_flags ?? [],
    scripted_visits: raw.scripted_visits ?? [],
    scripted_chapter_complete: raw.scripted_chapter_complete ?? false,
  };
}
```

**位置**: 后端 `format_state` (web_server/__init__.py 或 state.py)

```python
# 🆕 把 scripted_* 字段写入 state dict
state["scripted_mode"] = state.get("scripted_mode", False)
state["scripted_chapter_id"] = state.get("scripted_chapter_id", 0)
...
```

---

### 5. 跨模式数据流转

#### 5.1 LLM → 剧本 (玩家主动切换)
```
玩家在 /game 设置 → 切换剧本模式
  ↓
POST /api/scripted/start {chapter_id: 1}
  ↓
state.scripted_mode = true
state.scripted_node_id = "intro_1_father_ill"
state.scripted_chapter_id = 1
  ↓
下次 submitInput 走剧本引擎
```

#### 5.2 剧本 → LLM (玩家退出)
```
玩家点击"退出剧本模式"
  ↓
POST /api/scripted/exit
  ↓
state.scripted_mode = false
保留 scripted_flags (作为 LLM 提示)
  ↓
下次 submitInput 走 LLM
  ↓
LLM 收到提示: "玩家经历了第一章: 借债5两，父亲病愈"
```

#### 5.3 剧本模式自动 fallback
```
LLM ProviderAllFailedError
  ↓
检查 state.scripted_mode
  ├─ true → 继续剧本 (无影响)
  └─ false → 自动启动剧本
      ↓
      state.scripted_mode = true
      ↓
      payload.fallback_narrative = ...
      ↓
      前端 toast.info("已切换到剧本模式")
```

---

## 📐 实现步骤

### Phase 1: 数据层融合 (1 天)
- [ ] `types.py` ScriptedVoiceOption 加 `intent_text` / `value_dimension` 字段
- [ ] `types.ts` GameState 加 `scripted_*` 字段
- [ ] `mapper.ts` 透传 scripted_* 字段
- [ ] 后端 `format_state` 写入 scripted_*

### Phase 2: API 融合 (2 天)
- [ ] `/api/input` 检测 scripted_mode 自动路由到剧本引擎
- [ ] `/api/scripted/start` 改为不重置 cash/debt (保留主游戏状态)
- [ ] 新增 `/api/scripted/exit` 退出剧本
- [ ] 现有 LLM fallback 已存在, 验证仍生效

### Phase 3: 前端融合 (3 天)
- [ ] `<StoryModeBadge>` 组件
- [ ] `StartMenu` 加剧本入口卡片
- [ ] `GameView` 集成脚本检测 + 路由
- [ ] `ActionPanel` 复用 (无需改动)
- [ ] `NarrativeArea` 加剧本标记

### Phase 4: 测试 (2 天)
- [ ] 单元测试: scripted_* 字段透传
- [ ] E2E: 在主游戏中启动剧本 → 玩 → 退出 → LLM 继续
- [ ] E2E: 跨章回响 (ch1 → ch2 在主游戏中测试)
- [ ] E2E: LLM 失败时自动降级剧本

### Phase 5: 清理 (1 天)
- [ ] 删除 `/story-mode-demo` 独立路由 (或保留作为 dev 工具)
- [ ] 更新文档
- [ ] commit + push

**总计: ~10 天 (2 周)**

---

## 🎯 融合后的用户体验

### 场景 1: 新玩家
```
StartMenu
  ↓
[🎭 剧本模式]  [🌊 自由模式]
  ↓ (选择剧本)
Wizard (创建角色)
  ↓
/game?session=xxx&scripted=1&chapter=1
  ↓
GameView (剧本模式徽章可见)
  ↓
ActionPanel 显示剧本 voice_options
  ↓
NarrativeArea 显示剧本 narrative (📖 标记)
  ↓
玩家选择 → 剧本引擎响应
  ↓
第 1 章完成 → 提示"进入第 2 章"
  ↓
...
第 3 章完成 → 提示"🎉 完整剧本通关"
```

### 场景 2: LLM 老玩家
```
StartMenu → [🌊 自由模式]
  ↓
Wizard → /game
  ↓
LLM 失败 → toast.warning("已切换到剧本模式")
  ↓
GameView 自动从剧本 ch1 开始
  ↓
玩家继续玩, 体验剧本
  ↓
LLM 恢复 → 玩家选择"退出剧本"
  ↓
继续 LLM 模式 (剧本 flags 作为提示)
```

### 场景 3: 混合玩家 (推荐)
```
玩家选择剧本模式 → 玩第 1 章 → 觉得没新意
  ↓
切到 LLM 模式
  ↓
LLM 收到 "玩家在第一章借了债 +5两"
  ↓
LLM 基于此生成 narrative
  ↓
剧本与 LLM 互补
```

---

## 🎁 融合带来的好处

| 维度 | 融合前 | 融合后 |
|---|---|---|
| **玩家入口** | 不知道剧本模式存在 | StartMenu 双入口 |
| **数据一致性** | 剧本/LLM 状态分离 | 统一 game state |
| **代码复用** | VoicePill/narrative 重写 | 完全复用 |
| **UI 一致性** | 两种风格 | 同一 NarrativeArea 渲染 |
| **fallback 体验** | 突然切换 UI | 透明降级, 同 UI |
| **测试复杂度** | 两套 API 各自测 | 同一 API + 模式标志 |
| **玩家粘性** | 二选一 | LLM↔剧本 互转 |
| **后续扩展** | 加剧本要改前端 | 加剧本只改后端 |

---

## 🎯 风险与缓解

| 风险 | 缓解 |
|---|---|
| 剧本 narrative 跟 LLM 风格不一致 | 统一 narrative 标签格式 (📖 剧本 · 节点) |
| scripted_* 字段污染主游戏 | 用 optional (?) 字段, 不影响现有 |
| ActionPanel 不能识别剧本 voice | 已是同 schema (voice_id + intent_text) |
| 状态保存不兼容 (旧 save 无 scripted_*) | mapper 兜底 (default false / 0 / '') |
| LLM 接管剧本后状态丢失 | scripted_flags 永久保留, 作为 LLM context |

---

## 🎯 备选方案

### 方案 B: 剧本模式作为主游戏的"皮肤"
- 玩家在 StartMenu 选"剧本皮肤"
- 进入游戏后, 全部 UI 都是剧本风格
- 但数据/路由/逻辑完全分离
- **缺点**: UI 重复, 维护成本高

### 方案 C: 剧本模式作为独立可下载 DLC
- 玩家在商店"购买剧本包"
- 解锁后启用
- **缺点**: 太复杂, 不适合 MVP

**我的推荐**: **方案 A (本文档)** — 平衡代码复用和灵活性, 1 周实施, 长期收益高。

---

## 🎯 是否实施？

如果同意, 我将立即:
1. **Phase 1**: 数据层融合 (1 天)
2. **Phase 2**: API 融合 (2 天)
3. **Phase 3**: 前端融合 (3 天)
4. **Phase 4**: 测试 (2 天)
5. **Phase 5**: 清理 (1 天)
6. **总计**: 2 周交付, 增量 commit + push

**优点**:
- 玩家发现剧本模式入口
- LLM 失败时透明降级 (已有 fallback 升级)
- 状态统一, 跨模式无缝
- 代码复用, VoicePill 等不再重写
- 后续可加剧本包扩展

**缺点**:
- 短期工作量大 (2 周)
- 改动可能影响现有 E2E 测试

需要继续吗？