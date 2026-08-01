# 🏗️ 故事模式架构 v2.10.24 (重构版)

> 日期: 2026-08-01
> 重构内容: 拆分 engine.py + 依赖注入 + 常量集中 + 服务分层

## 📊 重构前后对比

| 维度 | 之前 (v2.10.23) | **现在 (v2.10.24)** | 改善 |
|---|---|---|---|
| engine.py 行数 | 520 | **382** | -27% |
| 最大文件 | engine.py (520) | chapter_02.py (1707) | 分离关注点 |
| 测试入口 | 1 个 (ScriptedStoryEngine) | 5 个 (engine + 4 services) | 单元测试 |
| 章节加载 | `if/elif` 在 engine | ChapterLoader | 可缓存/可测试 |
| D&D 检定 | engine 内联 | CheckService (注入) | 可 mock RNG |
| 效果应用 | engine 内联 | EffectsService | 可扩展 |
| 跨章回响 | engine 内联 | ChapterEchoService | 可单测 |
| 常量散落 | 散落在 engine | constants.py | 单一源 |

## 🏗️ 新架构 (5 层)

```
┌─────────────────────────────────────────────────────────┐
│              Routers (web_server/routers/)              │
│  scripted_story.py / input.py  → 调 engine              │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│             ScriptedStoryEngine (engine.py)             │
│  - handle_input / start_chapter / exit_scripted_mode   │
│  - 委托给 4 个 services (依赖注入)                       │
│  - 382 行 (原 520 行)                                   │
└─────┬──────────┬─────────────┬────────────┬─────────────┘
      │          │             │            │
      ▼          ▼             ▼            ▼
┌─────────┐ ┌─────────┐ ┌─────────────┐ ┌──────────────┐
│ Check   │ │ Effects │ │  Chapter    │ │  Chapter     │
│ Service │ │ Service │ │  Echo       │ │  Loader      │
│         │ │         │ │  Service    │ │              │
│ - D&D   │ │ - cash_ │ │ - 跨章回响  │ │ - 缓存       │
│ - d20   │ │   delta │ │   注入      │ │ - 元信息     │
│ - attr  │ │ - flag_ │ │             │ │              │
│         │ │   set   │ │             │ │              │
└─────────┘ └─────────┘ └─────────────┘ └──────────────┘
      │                          │
      ▼                          ▼
┌─────────────────────────────────────────────┐
│           constants.py / types.py           │
│  - DC_BASE, DC_PER_VALUE (D&D)              │
│  - ATTR_MOD_FLAGS (属性加成)                │
│  - RESOURCE_ATTRS (资源硬性)                │
│  - CHAPTER_INFO (前端用)                    │
│  - ScriptedChapter / Node / VoiceOption     │
└─────────────────────────────────────────────┘
```

## 📂 文件清单

```
src/history_footnote/story_mode/
├── __init__.py           20 行  - 公共 API 导出
├── types.py             103 行  - 数据模型 (dataclass)
├── constants.py         115 行  🆕 v2.10.24 - 常量集中
├── check_service.py     136 行  🆕 v2.10.24 - D&D 检定 (注入)
├── effects.py            62 行  🆕 v2.10.24 - 效果应用
├── chapter_echo.py       97 行  🆕 v2.10.24 - 跨章回响
├── chapter_loader.py     99 行  🆕 v2.10.24 - 章节加载
├── engine.py            382 行  ✨ -27% (委托给 services)
├── rich.py              244 行  - 多声部 + 环境 (不变)
├── chapter_01.py       1140 行  - 第一章数据
├── chapter_02.py       1707 行  - 第二章数据
└── chapter_03.py       1196 行  - 第三章数据
```

## 🔑 关键设计

### 1. 依赖注入 (DI)
```python
class ScriptedStoryEngine:
    def __init__(
        self,
        chapter: Optional[ScriptedChapter] = None,
        check_service: Optional[CheckService] = None,    # 🆕 注入
        effects_service: Optional[EffectsService] = None,  # 🆕 注入
        echo_service: Optional[ChapterEchoService] = None,  # 🆕 注入
        rng: Optional[random.Random] = None,            # 🆕 注入 RNG
    ):
```

**好处**:
- 测试时可注入 mock RNG (确定性结果)
- 可替换实现 (e.g. 不同 check_service)
- 单元测试更纯净

### 2. ChapterLoader 单例缓存
```python
# 之前: engine 内部 if/elif
if chapter_id == 1: self.chapter = get_chapter_01()
elif chapter_id == 2: self.chapter = get_chapter_02()
elif chapter_id == 3: self.chapter = get_chapter_03()

# 现在: 统一加载器 (可测试/可清缓存)
from history_footnote.story_mode.chapter_loader import get_chapter, clear_cache
self.chapter = get_chapter(chapter_id)
```

### 3. 常量集中
```python
# 之前: 散落在 engine.py 4 个地方
attr_mod_flags = {...}  # 在 _resolve_attr 里
dc = 10 + value * 2     # 在 _do_check 里
threshold = value * 2 + 10  # 在 _do_check 里

# 现在: 一个文件
from history_footnote.story_mode.constants import DC_BASE, DC_PER_VALUE, ATTR_MOD_FLAGS
dc = DC_BASE + value * DC_PER_VALUE
```

### 4. Services 拆分原则
- **CheckService**: 表达式解析 + d20 + 属性 (单一职责: 检定)
- **EffectsService**: delta 应用 + flag_set + city_move (单一职责: 效果)
- **ChapterEchoService**: 跨章回响 (单一职责: 回响注入)
- **ChapterLoader**: 单例缓存 + 元信息 (单一职责: 加载)

## 🎯 新增公共 API

### ChapterLoader
```python
from history_footnote.story_mode.chapter_loader import (
    get_chapter,           # 获取章节 (单例)
    clear_cache,           # 清空缓存 (测试用)
    list_chapters,         # 列出所有章节元信息 (前端用)
    get_chapter_info,      # 获取单个章节元信息
)

# 前端: GET /api/story_mode/chapters
chapters = list_chapters()
# → [{"id": 1, "title": "家贫", "nodes": 22, "options": 55, ...}, ...]
```

### CheckService (可单测)
```python
from history_footnote.story_mode.check_service import CheckService

cs = CheckService(rng=random.Random(42))  # 注入 RNG
result, d20 = cs.do_check("charisma >= 2", game_state)
attr = cs.resolve_attr("charisma", game_state)
```

### EffectsService
```python
from history_footnote.story_mode.effects import EffectsService

EffectsService.apply(game_state, {"cash_delta": -5})
added = EffectsService.apply_flag_set(game_state, ["flag1", "flag2"])
EffectsService.apply_city_move(game_state, "suzhou")
```

## 🧪 验证

| 测试 | 结果 |
|---|---|
| 18 个单元测试 | ✅ 18/18 通过 |
| 集成测试 (test_v21022_integration.py) | ✅ 7/7 通过 |
| engine.py 行数 | 520 → 382 (-27%) |

## 🎯 改进建议 (后续)

### P1
1. **narrative 改 NarrativeSection**: 现在 narrative 是字符串, 应改为 `list[NarrativeSection]` 支持多声部
2. **RequiredCity/Flags 在 _get_current_view 实施**: `ScriptedNode` 定义了但没读
3. **AutoNextNode 实施**: 无选项节点的自动跳转

### P2
4. **路由热加载**: 加新章节不用重启 backend
5. **指标埋点**: 检定成功率 / 选项点击率 / 玩家路径分析

## 🎯 当前故事模式架构评分

| 维度 | 之前 | **现在** |
|---|---|---|
| 可扩展性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 可测试性 | ⭐⭐⭐⭐ (18 测试) | ⭐⭐⭐⭐⭐ (可单测 services) |
| 关注点分离 | ⭐⭐ (engine 大杂烩) | ⭐⭐⭐⭐⭐ (4 services) |
| 可维护性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ (常量集中) |
| 可读性 | ⭐⭐⭐ | ⭐⭐⭐⭐ (engine 只做编排) |