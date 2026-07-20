# 连贯性检查报告 — wanli1587_20260720_142945 30 回合实测

> **日期**：2026-07-20
> **session**：`wanli1587_20260720_142945`
> **总时长**：~25 分钟，30 turns，21 回合（1587/1 → 1588/9）
> **目的**：找出 v2.10.11 在真 LLM 长跑中暴露出的一致性问题（不只单元测试，要看玩家视角体验）

---

## 📋 检测覆盖

| 数据源 | 数量 |
|---|---|
| 玩家 input（player actions）| **30** （e2e ACTIONS_30）|
| 回合（Round）| **21** |
| financial_log | **22 条** |
| 保留 narrative | **3 条**（sliding window）|
| era variables | **9 个** |
| triggered events | **8 个** |

---

## ✅ PASS 项

### 1. 笔法一致（半文半白 + 田契/姜汤等小动作）
三条 narrative 出自 LLM 实时生成，**没有剧本味**，与 "万历十五年 + 织户" 时代设定贴。

例：
> 那是嘉靖四十一年写下的田契……边角磨得起了毛，上头的字倒还清楚——"沈门沈大用"。
> 你把毛笔蘸了墨，重新算了一笔……三亩二分，七两一亩……二十二两多。
> **这就是你全部的家底。** 织机是租来的，作坊是租来的，屋子也是租来的。

### 2. 9 个 era variable 完美贴合 narrative
- `tax_burden = 4`（高） → narrative 真描述 "秋税 20 两"
- `silver_pressure = 3`（中） → "白银短缺、收不来"
- `livelihood = 6`（强） → "玩家技能高、织机熟练"

### 3. 人物对齐
- 沈氏（玩家妻子）— 田契算账时出现，端姜汤 ✅
- 阿宝（玩家孩子）— 乡学读书 ✅
- 赵里长 — R03 turn 4 被访问 ✅
- 王掌柜/王牙人 — 出现并推动经济事件 ✅

### 4. 地点转移
盛泽（R01-R13） → 苏州（turn 22 起运绸缎）→ 回盛泽（R21）
**没有逆向跳时间或无意漂移**。

---

## 🚨 发现的问题清单

### ❌ **CRITICAL-1**：R20 回合被吞

**症状**：cash 时间序列中没有 R20 的任何动作（financial_log 没有 round=20 的记录）。

cash 流：
```
R19 (turn 27) cash = 9.2 → 0.0  （fall）
R21 (turn 30) cash = 0  (stable 0)
```

narrative 时间线：
- N0（round=19）：算田契（应该有 R19）
- N1（round=19）：犹豫
- N2（round=21）：回家坐船

**R20 = 跳号**。LLM 在 R20 期间没有触发 financial log / narrative。

**根因猜测**：LLM 把"去苏州→回盛泽"压缩到了一个跨回合的 narrative (N2)，放弃了中间的 R20。

### ❌ **CRITICAL-2**：cash 归零与 narrative 矛盾

turn 27 输入 "R19 看织造局老师傅"。

按 financial_log：
- R19 sell_silk = +10
- R19 pay_tax = -20
- R19 repay = -2
- 净 = -12

但 player cash `9.2 + (-12) = -2.8` 不该归 0。

实际却 cash = **0.0**。

**根因猜测**：LLM 在 narrative 里提到"卖田契"（N0：算田契 "是最后的底，不到万不得已不能动"暗示可能卖了——但实际 N0 没写卖，只是算账）——所以**可能有"卖田契"的未写入 financial_log 的隐性资金流转**。

### ❌ **CRITICAL-3**："付八文船钱"被记成 repay

**N2**：
> 船靠了码头。你付了八文船钱，跳上青石板。

**R21 financial_log**：
```
R21  1588年9月  repay  -0.008  ← 这条 +0.008
```

→ **narrative 描述"付八文船钱" = 0.008 两**（1 两 = 1000 文合理），但 facts_extractor **没有把"付船钱"识别成 transport_fee 类的支出**，反而归到 `repay`（还债）——

**facts_extractor bug**：中文"付了船钱"或"八文船钱"→ 应识别为 transport_fee，但系统归到 repay。

### ⚠️ **MEDIUM-4**："算田契"被识别成 repay

turn 28 输入 "把家里的田契重新算一遍"。

对应 financial_log：
```
R19  repay  -2.0  ← 这条 note 说 "今快四十年了。边角磨得起了毛..." 完全没提还款
```

→ 玩家行动"算账"被误读成"还款"。facts_extractor 看到"账"+"还"就 panic 出 repay。

**根因**：可能 narrative 中某句有"算账"、"账本"等关键词，触发了一个 weak classifier。

### ⚠️ **MEDIUM-5**："三年下来"时序错乱

**N2 末**：
> **三年下来，白纸黑字写着：三两、五两、五两。**

但实际 session 运行：
- 1587 年 1 月 → 1588 年 9 月 = **20 个月 ≈ 1.7 年**

"三年下来"对不上"1.7 年"。

→ **LLM 凭印象写"三年"，没核对实际日期**。这是叙事自洽 bug。

### ⚠️ **HIGH-6**：cash 跳变 + narrative 不一致

turn 24 (苏州买苏绣样品) 输入 → 即时扣 cash 2 两（合理）
turn 25 (回镇上给王牙人看) — narrative 没保留这条，不确定做了什么
turn 26 (县里拜会新县令) — cash 不变 **但**应该触发消费（车马/礼物）
turn 27 (看织造局老师傅) — cash 9.2 → 0（异常）

最后那一步 cash 归 0 **不是因为 pay_tax 单独发生**（20 两税 + 之前 9.2 = -10.8），必有其他资金流出。

**根因猜测**：LLM 在 R19 期间"自动创作"了**未在 narrative 显式表达的卖田契/借债**事件，没经 facts_extractor。

### ⚠️ **MEDIUM-7**：京城叙事缺失

turn 29 输入："带着绸缎和账本**去京城一趟**"

financial_log + narrative = **完全无京城痕迹**。sliding window 只保留最近 3 条 narrative，可能**京城 narrative 被裁掉了**。

→ 一是 narrative 没真正为京城做叙事（LLM 跳过），二是没做存档。

### ⚠️ **MEDIUM-8**：home → 苏州 → home 时间压缩

从 time series 看：
- turn 22 (R15) 准备运绸缎去苏州
- turn 24 (R15 → R17) 在苏州
- turn 29 (R21) 回镇上
- turn 30 (R21) 盘算

中间 turn 25-28 (R17/R19) **到底在哪？** narrative 不说。如果玩家真的"在苏州"，rounds 不能快进到回家。

### ⚠️ **MEDIUM-9**：苏州到盛泽"船钱 8 文"

24 turn + R17 在苏州买苏绣样品（扣 1 两）
25 turn + R17 在苏州看牙人
26 turn + R19 在县里拜会县令（这就跨城回盛泽了？县令和苏州不是一个地方！）
27 turn + R19 看织造局
28 turn + R19 把田契重新算一遍
29 turn + R21 (R19 → R21 跳跃) 去京城
30 turn + R21 回镇上付船钱

**地理逻辑被打散**：苏州和县令是两个地方。LLM 把"县里拜会县令"理解为苏州之行的延续，错了。

---

## 🛠 修复优先级

### P0（必须修 — 不修不能上线）

1. **facts_extractor 中文识别精度**：避免把 "算账/船钱/八文" 误判为 repay
2. **cash accounting 中间层**：每回合 cash 进出对账，不允许凭空归零
3. **narrative sliding window 加深**：recent_narratives 至少保留 10-20 条（避免丢用户重要的叙事）

### P1（强烈推荐）

4. **DM prompt 加固**：明确"必须写日期推进"、"不容忍'三年下来'与实际日期不符"
5. **locator / place tracking**：每次 player input 时把"地点"作为必填 attribute 注入 narrative
6. **timer consistency check**：turn → round 映射验证，不允许 turn 跳 round

### P2（应该修 — 但 v2.10.13 可以拖）

7. **events 触发与 financial_log 对账**：每个 non-financial event 必须附 financial trace
8. **京城叙事备份**：独立字段存，避免被 sliding 覆盖

---

## 🎯 总结

| 维度 | 评分 | 备注 |
|---|---|---|
| **故事连贯** | ⭐⭐⭐☆☆ | 笔法统一，时代贴 |
| **财务一致** | ⭐☆☆☆☆ | 4 处可识别 bug |
| **时序一致** | ⭐⭐☆☆☆ | R20 跳号、"三年"不符 |
| **变量一致** | ⭐⭐⭐⭐⭐ | era variables 完美 |
| **人物一致** | ⭐⭐⭐⭐☆ | 沈氏/王掌柜 都对得上 |
| **地点连贯** | ⭐⭐☆☆☆ | 盛泽→苏州→回盛泽 模糊 |
| **整体可玩** | ⭐⭐⭐☆☆ | 真 LLM 沉浸感强，但玩家会看出"诡异" |

**核心结论**：

- **叙事笔法 = 真 LLM 化**，可看
- **financial_log = 严重错**，需 facts_extractor 重做或加 manual validation
- **时序/地理 = 弱项**，需 prompt 加固 + 强字段注入

**建议**：在 v2.10.13 / v2.10.14 集中修 facts_extractor + DM prompt，**否则玩家玩 30 回合后会发现 cash 莫名归零**，直接影响产品体验。

---

## 📚 关联文件

- 测试脚本：[tests/test_v21011_30r_real_e2e.py](file:///Users/mac/Documents/trae_projects/history_footnote/tests/test_v21011_30r_real_e2e.py)
- 测试报告：[docs/log/2026-07-19-v2.10.11-real-30r-e2e.md](file:///Users/mac/Documents/trae_projects/history_footnote/docs/log/2026-07-19-v2.10.11-real-30r-e2e.md)
- Session 复盘：见 [dev-server](http://127.0.0.1:8765/api/state?session_id=wanli1587_20260720_142945)
- Session persistent 存档：`tests/_e2e_progress/wanli1587_20260720_142945.json`

---

**🚦 决策点**：要不要把 P0 三项立刻做？任何一项继续放着都会让玩家卡钱（"为什么我没卖绸缎但 cash 跳 -2？"）。
