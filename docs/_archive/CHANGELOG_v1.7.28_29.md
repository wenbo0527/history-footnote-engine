# v1.7.28 + v1.7.29 Changelog

**发布日期**：2026-07-08
**调研依据**：[stress_test_report_v1.7.28.md](stress_test_report_v1.7.28.md)

---

## v1.7.29 — Skill 塌房修复（2026-07-08）

### 🔴 修复塌房 4：SKILL-2 慢时间触发过宽

**问题**：玩家输入"先看看家里情况"被判定为 `slow_time`（detail 4/5），导致每步都触发内心独白/价值观发声，玩家体验"小说化"。

**根因**（`dm_skills.py:413-424`）：决策树用"含看看/听听+6+字"判定问询，**不区分"自己看"和"问别人"**。

**修复**：新增 `_is_genuine_inquire()` 辅助函数（55 行），要求：
- 5+ 字
- 必含问询动词（问/打听/请教/聊聊 等）
- 必有具体对象（人名/概念/地点）
- 反模式排除（先/我要/我准备/细看/环视 等）

**测试**：`scripts/test_skills_stress.py` — 红旗数 4 → 0

### 🔴 修复塌房 5：SKILL-7 身份铁律（cannot_access 子串）

**问题**：织工说"我去科举考试"通过身份审核（明朝织工/商籍/匠籍**制度上**不能进学）。

**根因**（`dm_skills.py:730-733`）：用子串匹配 `if forbidden in player_input`，玩家换说法就绕过。

**修复**：新增**意图词典系统**（120 行）：
- `INTENT_PATTERNS` 6 个意图的正则
- `INTENT_FORBIDDEN_IDS` 意图 × 身份矩阵
- `INTENT_REJECT_TEMPLATES` 叙事拒绝模板
- `_detect_intent()` 智能识别玩家意图
- 意图铁律**优先于** iron_laws

**支持的意图**：
- `participate_imperial_exam`（科举）
- `audience_emperor`（见皇帝）
- `join_army`（参军）
- `appeal_to_emperor`（告御状）
- `go_capital`（去京城）
- `become_monk`（出家）

**测试**：`scripts/test_skill7_intent.py` — 27/27 通过

### 🔴 修复塌房 6：史实锚点触发后不标记

**问题**：同一锚点每回合都被检测到，玩家会看到"矿税监又来了！"

**根因**（`dm_skills.py:551-555`）：
- `HistoricalAnchor.triggered` 字段是 `False`（从来不改）
- 没人把 anchor_id 加进 `state.triggered_events`
- SKILL-4 只检查 `triggered_events` 排除，**但没人标记**

**修复**：SKILL-4 触发时**立即**：
1. 把 anchor_id 加进 `triggered_events`（in-place mutation）
2. 设 `triggered=True`
3. 用 set 去重（同一回合多次"触发"只标记一次）
4. 铺垫阶段不标记（避免误锁）

**测试**：`scripts/test_skill4_anchor.py` — 6/6 通过

### 🔴 修复塌房 3：知识库 layer 优先级

**问题**："朝廷" 一次命中 7 条，LLM 不知道哪条优先，可能提前剧透 NPC。

**修复**（`knowledge_base.py:107-127`）：query 后**按 layer 排序**：
- `background` (优先级 0) — 时代背景，最普适
- `principle` (优先级 1) — 制度原理
- `scene` (优先级 2) — 场景知识
- `entity` (优先级 3) — 人物/地点（**容易剧透**）

排序 tie-breaker：关键词命中数倒序。

**测试**：`scripts/test_kb_layer_priority.py` — 5/5 通过
- "朝廷" → 3 个 background 在前
- "皇帝" → 3 个 background 在前
- "戚继光" → 1 个 entity 排前（关键词命中 2 次）

---

## v1.7.28 — 输入验证（2026-07-08）

### 🆕 新模块：InputValidator（280 行）

**位置**：`src/history_footnote/input_validator.py`

**6 种检测维度**：

| reason | 触发 | 友好提示 |
|---|---|---|
| `empty` | 嗯/好/!/??? | "你似乎还没输入什么" |
| `meta_query` | 你是谁/show me the code/ignore previous | "我是 DM，只关心万历年间的故事" |
| `era_violation` | 手机/wifi/AI/公务员/我是秦始皇/清朝 | "「X」在万历年间并不存在" |
| `meta_command` | /admin/SQL 注入/XSS | "系统指令无法在游戏中执行" |
| `too_long` | > 200 字 | "请控制在 200 字以内" |
| `low_relevance` | 4 字以上 + 知识库 0 匹配 | **不阻断**，只 toast 软提示 |

**双层防御**：
- 客户端：InputArea 预检
- 服务端：`/api/input` 验证

### 🔴 修复塌房 1+2：知识库空查询整库注入（致命）

**问题**（`knowledge_base.py:75-92`）：空 keywords + 无 scene/layer/entry_ids 时返回**全部 69 条**。

**修复**（`knowledge_base.py:74-86`）：
```python
# 🆕 v1.7.28 修复：空查询守卫
if not keywords and not scene and not layer:
    return []

# 关键词过滤：必须是有效中文 2-4 字 token
if keywords:
    keywords = [kw for kw in keywords if kw and len(kw) >= 2]
```

**测试**：`scripts/test_kb_collisions.py` — 8/8 修复

---

## 改动文件清单

| 文件 | 改动 | 版本 |
|---|---|---|
| `src/history_footnote/knowledge_base.py` | +12 行（空查询守卫）+25 行（layer 优先级）| v1.7.28 + v1.7.29 |
| `src/history_footnote/input_validator.py` | **新建 280 行** | v1.7.28 |
| `src/history_footnote/web_server/routers/input.py` | +35 行（验证 + soft_warning）| v1.7.28 |
| `src/history_footnote/dm_skills.py` | +120 行（intent 词典）+55 行（_is_genuine_inquire）+15 行（triggered 标记）| v1.7.29 |
| `src/frontend/src/lib/components/game/InputArea.svelte` | +80 行（错误 UI + 客户端预检）| v1.7.28 |
| `src/frontend/src/lib/components/game/GameView.svelte` | +18 行（服务端错误处理）| v1.7.28 |
| `scripts/test_skills_stress.py` | **新建 270 行** | v1.7.28 |
| `scripts/test_kb_collisions.py` | **新建 90 行** | v1.7.28 |
| `scripts/test_input_validator.py` | **新建 130 行** | v1.7.28 |
| `scripts/test_skill7_intent.py` | **新建 90 行** | v1.7.29 |
| `scripts/test_skill4_anchor.py` | **新建 95 行** | v1.7.29 |
| `scripts/test_kb_layer_priority.py` | **新建 60 行** | v1.7.29 |
| `docs/stress_test_report_v1.7.28.md` | **新建 445 行** | v1.7.28 |
| `docs/CHANGELOG_v1.7.28_29.md` | **本文件** | v1.7.28 + v1.7.29 |

**合计**：约 1700 行改动/新增

---

## 测试结果汇总

| 脚本 | 关注点 | v1.7.27 | v1.7.28 | v1.7.29 |
|---|---|---|---|---|
| `test_skills_stress` | 4 个 SKILL × 20 玩家输入 | 4 红旗 | - | **0 红旗** |
| `test_kb_collisions` | 知识库空查询 | 8/8 塌房 | **8/8 修复** | 8/8 |
| `test_input_validator` | 非游戏内容拦截 | - | - | **33/33 通过** |
| `test_skill7_intent` | 身份铁律（意图识别）| 织工科举通过 | - | **27/27 通过** |
| `test_skill4_anchor` | 史实锚点标记 | 重复触发 | - | **6/6 通过** |
| `test_kb_layer_priority` | 知识库排序 | 顺序错乱 | - | **5/5 通过** |

**总测试**：**99 个 case，99/99 通过**

---

## 行为对比（修复前 vs 修复后）

### 场景 1：玩家输入"嗯"

| | 修复前 | 修复后 |
|---|---|---|
| 前端 | 提交 | 客户端拦截，error UI 提示"你似乎还没输入什么" |
| 后端 | 整库 69 条注入 LLM | 400 + `{"error": "empty", "suggestion": "..."}` |
| LLM 成本 | 浪费 ¥0.5-2 | 0 |

### 场景 2：织工说"我去科举考试"

| | 修复前 | 修复后 |
|---|---|---|
| SKILL-1 | 路线 imperial_exam | 路线 imperial_exam |
| SKILL-7 | free / allow（织工通过）| plausible / reject_narratively |
| 叙事 | "你考上了进士，光宗耀祖"（荒谬）| "你被人拦下：读书人才能入考场，你一个织工/商贩/农户..." |

### 场景 3：玩家写"我听说矿税监要来"（round=38）

| | 修复前 | 修复后 |
|---|---|---|
| SKILL-4 | sharp_cut | sharp_cut |
| triggered 标记 | 永不标记 | 立即标记 |
| round=39 | 又触发矿税监（重复）| 不会再触发（已标记） |

### 场景 4：玩家写"朝廷最近如何"

| | 修复前 | 修复后 |
|---|---|---|
| 知识库匹配 | 7 条（按 entries 顺序）| 7 条（**background 排前**）|
| LLM 引用 | 容易提前剧透"戚继光"等 | 先引用"万历时代概貌"等时代背景 |

---

## 性能影响

| 指标 | 修复前 | 修复后 | 变化 |
|---|---|---|---|
| 知识库查询（无效输入）| 30K tokens | 0 tokens | **-100%** |
| 知识库查询（有效输入）| 30K tokens | 30K tokens | 持平 |
| LLM 错误调用（空/无效输入）| 浪费 | 0 | **-100%** |
| 史实锚点重复触发 | 100% 重复 | 0 重复 | **-100%** |
| 织工科举等铁律塌房 | 100% 绕过 | 0 绕过 | **-100%** |

---

## 仍存在的风险

| 风险 | 严重度 | 计划 |
|---|---|---|
| 关键词匹配是 substring + 2-4 字贪心 | 中 | v1.8.0 升级为 embedding |
| SKILL-1 长度阈值 `> 50` 过高 | 中 | v1.7.30 |
| 史实锚点按 round 编号（不是日期）| 高 | v1.7.30 |
| Tools 调用靠 LLM 决定 | 高 | 待观察 |
| `run_dm_skills` 兼容旧接口混用 | 中 | v1.8.0 清理 |
| 知识库 69 条 vs 0 narrative snippets | 中 | v1.8.0 |
| pacing_anchors 只 1 条 | 中 | v1.8.0 扩到 10+ |

---

## 升级指引

```bash
# 1. 拉取 v1.7.29
git pull origin v1.7.29

# 2. 运行所有测试
source .venv/bin/activate
python scripts/test_skills_stress.py        # 应该 0 红旗
python scripts/test_kb_collisions.py        # 8/8 修复
python scripts/test_input_validator.py      # 33/33 通过
python scripts/test_skill7_intent.py        # 27/27 通过
python scripts/test_skill4_anchor.py        # 6/6 通过
python scripts/test_kb_layer_priority.py    # 5/5 通过

# 3. 启动后端
python -m history_footnote
```

---

**发布人**：Trae + Mac
**关联文档**：
- [调研报告](stress_test_report_v1.7.28.md)
- [CHANGELOG（本文件）](CHANGELOG_v1.7.28_29.md)
