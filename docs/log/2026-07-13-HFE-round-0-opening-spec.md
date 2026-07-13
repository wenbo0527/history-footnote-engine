# 🆕 HFE · Round 0 Opening 规范

**日期**：2026-07-13
**作者**：wenbo0527
**状态**：✅ 用户确认 + 测试保护

---

## 📜 规范内容

第 0 回合（开局）的 `narrative` 必须是以下 4 段格式：

```
欢迎来到【万历十五年】 ♂/♀
你是 {name} — {hometown}
【开局处境】{starting_situation}
日期：{current_date}
```

### 字段来源

| 段 | 来源 | 默认值 |
|---|---|---|
| 时代名 `【万历十五年】` | `era_config.era_name` | 硬编码 |
| 性别符号 `♂` / `♀` | `state.player_gender` | - |
| 角色名 `{name}` | `state.custom_character.name` | "？" |
| 家乡 `{hometown}` | `state.custom_character.hometown` | "盛泽镇" |
| 开局处境 `{starting_situation}` | `state.custom_character.starting_situation` | session.py setdefault 兜底 |
| 日期 `{current_date}` | `state.current_date` | 时代开始日期（万历十五年 1 月） |

### 示例

> 欢迎来到【万历十五年】 ♂
> 你是 沈织户 — 盛泽镇
> 【开局处境】今早推开家门，织工的活计照旧，但心里总有些不安。
> 日期：1587年1月

### 实际验证（v2.10.4-patch3）

文博 2026-07-13 19:00 CST 入局后看到的第 0 回合文本：

```
欢迎来到【万历十五年】 ♂
你是 沈织户 — 盛泽镇
【开局处境】今早推开家门，织工的活计照旧，但心里总有些不安。
日期：1587年1月
```

✅ 用户确认：**接受这个作为第 0 回合标准 opening**。

---

## 🔧 改动

### 1. `GameState.append_narrative` 加 `narrative_type` 参数

**文件**：[game_state.py:626](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/game_state.py#L626-L657)

```python
def append_narrative(self, round_number: int, narrative: str, summary: str,
                      player_input: str = "", chosen_voice: str = "",
                      current_date: str = "", chapter_id: int = 0,
                      narrative_type: str = "response") -> None:
    """🆕 v2.10.4-patch3: 记录 narrative 类型（让前端 mapper 准确识别）

    - narrative_type: "opening"（开局）/ "story"（章节叙事）/"response"（玩家行动后）/"system"（系统）
    - 默认 "response"（向后兼容）
    """
    entry = {
        ...
        "type": narrative_type,  # 🆕 v2.10.4-patch3
    }
```

### 2. `session.py: handle_POST_start` 为 opening 传 `narrative_type="opening"`

**文件**：[routers/session.py:79](file:///Users/mac/Documents/trae_projects/history_footnote/src/history_footnote/web_server/routers/session.py#L79)

```python
if opening_text:
    # 🆕 v2.10.4-patch3: 明确标记 round 0 是 opening
    # （之前 type 字段为 null，靠前端 mapper fallback）
    game.state.append_narrative(0, opening_text, "开场", narrative_type="opening")
```

---

## 🧪 测试保护

**新文件**：[tests/test_round0_opening.py](file:///Users/mac/Documents/trae_projects/history_footnote/tests/test_round0_opening.py)（10 用例）

| 测试类 | 覆盖点 |
|---|---|
| `TestAppendNarrativeType` | append_narrative 默认 type=response / 显式 type=opening/system/story / 其他字段保留 |
| `TestOpeningTextFormat` | 7 段必备文本（万历 / 性别符号 / 名字 / 家乡 / 开局处境 / 职业 / 日期） + ♀ 验证 |
| `TestFormatStateRound0` | format_state 透传 type="opening" / "response" 到 recent_narratives |
| `TestSessionStartOpeningType` | session.py 源码层面验证 narrative_type="opening" 存在 |

测试结果：**10/10 PASSED** ✅

---

## 🎯 关键价值

### 之前（v2.10.4-patch3 之前）

```python
# 后端 round 0 narrative 的 entry 是：
{"round": 0, "narrative": "欢迎来到...", "summary": "开场", ...}  # type 字段缺失

# 前端 mapper.ts 收到 type=null，靠 fallback：
"latest.type ?? 'opening'"
```

### 之后

```python
# 后端 round 0 narrative 的 entry 是：
{"round": 0, "narrative": "欢迎来到...", "summary": "开场", "type": "opening", ...}

# 前端 mapper 准确识别 type="opening"：
# - 渲染上不用 fallback
# - 未来可按 type 区分（opening 特殊 UI、response 常规、story 章节高亮）
```

### 防御价值

- **未来重构 / 拆分 mapper 时**——type 字段不再是"null + fallback"脆弱链
- **未来添加新类型**（如 `system`/`event`/`settlement`）—— 加测试即可
- **未来 fast-fail**——如果 session.py 忘了传 narrative_type，测试 `TestSessionStartOpeningType` 会失败

---

## 🔗 关联

- [v2.10.3 P1-C 总结](file:///Users/mac/Documents/trae_projects/history_footnote/docs/log/2026-07-13-HFE-v2.10.3-4-总结.md)（同样修 type 字段让前端类型更安全）
- [v2.10.4-patch3 总结](file:///Users/mac/Documents/trae_projects/history_footnote)（issue_reporter/config 同步 + this opening fix）
- [v2.10.3-4 周期总结](file:///Users/mac/Documents/trae_projects/history_footnote/docs/log/2026-07-13-HFE-v2.10.3-4-总结.md)
- [mapper.ts 类型守卫](file:///Users/mac/Documents/trae_projects/history_footnote/src/frontend/src/lib/api/mapper.ts)（前端用 type 字段的位置）