# 📜 故事模式 第二章 + 第三章 详细设定计划

> 版本: v2.10.17+ Phase 11
> 编剧: 沈茂（盛泽织工）/ 沈茂之子 玩家
> 时代: 万历十五年 (1587) · 江南丝绸业
> 参考史料: 《吴江县志》《万历邸钞》《金瓶梅》《醒世姻缘》《天工开物》

---

## 🧭 整体剧情架构

```
第一章《家贫》  [夏初 · 盛泽镇]      → 父病·债台·抉择
第二章《织染》  [夏中-秋初]            → 苏州订单·家庭·兴衰
第三章《丝绢案》[秋-冬初]              → 织造太监·税关·政治风暴
                 ↓
         第四章《...》(后续)
```

**核心悬念 (3 章总)**:
- 玩家如何从负债织工 → 小康之家？
- 沈家与苏州恒德祥的订单能否如期交货？
- 万历年间"丝绢折纳"加派税关的浪潮如何影响盛泽？

---

# 🌾 第二章 《织染》

> 时间: 万历十五年六月至九月（约 16 回合）
> 地点: 盛泽镇 ↔ 苏州府
> 主线: 苏州订单 / 家庭考验 / 织机扩张

## 📖 剧情背景

父亲病愈（承接第一章结局 flag `father_better`），你接到苏州恒德祥的 30 匹夏绸订单（承接 `has_order_suzhou`）。六月的盛泽镇正值梅雨季，丝绸生意进入旺季，但也暗藏风险——苏州织造太监即将南下采办，牙行收购价波动。

主线矛盾:
1. **订单 vs 织机**: 30 匹夏绸要 2 月完成，但梅雨潮湿丝线易断
2. **扩张 vs 风险**: 张叔提议合股扩大织坊，但需投入 8 两
3. **家庭 vs 事业**: 张氏怀孕 / 父亲欲言又止的秘密
4. **价格 vs 信用**: 牙行压价 vs 苏州订单

## 🎭 新角色

| 角色 | 身份 | 性格 | 备注 |
|---|---|---|---|
| **张氏（妻）** | 已登场 | 坚韧/谨慎 | 第二章怀孕（flag `wife_pregnant`） |
| **苏州恒德祥掌柜** | 新登场 | 精明/守信 | 订单甲方，姓孙 |
| **张叔（张守仁）** | 已登场 | 厚道/老练 | 第二章提议合股 |
| **织染坊赵师傅** | 新登场 | 嗜酒/手艺绝 | 染色关键人，欠酒债 |
| **钱老板之子·钱少** | 新登场 | 纨绔/暗中相助 | 第二章伏笔 |
| **王婆（接生婆）** | 新登场 | 能干/八卦 | 妻子生产剧情 |
| **苏州织造衙门书吏** | 新登场 | 势利/可买通 | 政治线伏笔 |
| **母亲** | 已登场 | 慈爱/软弱 | 第二章揭"传家金簪"谜 |

## 📊 经济系统（第二章）

| 项目 | 数值 |
|---|---|
| 起始 cash | -5 到 +12（取决于第一章结局） |
| 苏州订单尾款 | +12 两（30 匹夏绸） |
| 月息 | 0.15 两（已欠债的话） |
| 织机 1 架 | 月产 4 匹绸 |
| 织机 2 架 | 月产 7 匹 |
| 织机 3 架 | 月产 9 匹（需雇工） |
| 雇工月钱 | -1 两/人 |
| 妻怀孕费用 | -3 两（生产） |
| 织机维修 | -1 两/次 |
| 染料成本 | -0.5 两/匹（绮霞罗） |

## 🌳 第二章节点分支图

```
intro_ch2_start (15 nodes 起步)
├─ 收尾第一章 flag → 选择开局基调
│   ├─ flag "prosperous" → intro_ch2_prosperous (家境小康)
│   ├─ flag "father_secret" → intro_ch2_secret (父亲密谈)
│   └─ 默认 → intro_ch2_normal (普通开局)

intro_ch2_prosperous (苏州订单)
├─ take_summer_order → escalation_ch2_weave (赶织夏绸)
├─ expand_loom → escalation_ch2_expand (扩张织坊)
└─ train_apprentice → escalation_ch2_master (收徒)

intro_ch2_normal (梅雨季节)
├─ borrow_for_order (借钱周转)
├─ wait_for_sun (等梅雨停)
└─ help_neighbor (帮周大娘) → flag "zhou_favor"

escalation_ch2_weave (赶织 30 匹)
├─ hire_help → hire_worker_xiao_chen (雇陈小)
├─ buy_quality_silk (买上等丝) → climax_ch2_quality
├─ dye_with_zhao (找赵师傅染) → climax_ch2_dye
└─ family_first (陪张氏) → wife_pregnant flag

climax_ch2_quality (上等丝交货)
├─ deliver_success → resolution_ch2_prosperous (订单大成功)
├─ deliver_partial → resolution_ch2_normal (部分完成)
└─ deliver_late → resolution_ch2_loss (违约赔款)

climax_ch2_dye (染色危机)
├─ 赵师傅醉酒 → fail (颜色不均)
├─ 自己研究 → success (习得染色) → flag "master_dyer"
└─ 找苏州师傅 → success (但贵 2 两)

climax_ch2_zhang_secret (父亲秘密)
├─ reveal → reveal_father_secret (父亲当年"丝绢案"蒙冤)
├─ 父亲去世前托付 → flag "father_will"
└─ 隐瞒 → flag "father_silent"

resolution_ch2_*** (5 个结局)
├─ prosperous (订单大胜·家庭美满)
├─ normal (平稳过关)
├─ loss (违约负债·声誉受损)
├─ outcast (破产再卖织机)
└─ pregnant_loss (妻子难产·婴儿夭折) → 隐藏结局
```

### 总节点目标: **35-40 节点**
### 总选项目标: **80-100 选项**
### 总结局目标: **5 个** (含 1-2 隐藏)

## 🎲 第二章随机事件 (5 个)

1. **☔ 梅雨连绵** (round 2-4, city=shengze, prob=0.4)
   - 触发条件: round >= 2
   - 检定: luck ≥ 2
   - 大成功: 抢晴天赶织 5 匹，cash +2
   - 成功: 正常节奏
   - 失败: 丝线断 3 匹，cash -1, silk_loss flag

2. **🎨 赵师傅求酒** (round 3-8, flag=master_dyer)
   - 触发条件: 已认识赵师傅
   - 检定: charisma ≥ 3
   - 大成功: 赵师傅传授独门染色技法，flag `knew_color_master`
   - 成功: 正常染色
   - 失败: 染色失败，cash -1

3. **💰 苏州牙行抢单** (round 4-9, city=suzhou)
   - 触发条件: city=suzhou
   - 检定: charisma ≥ 4
   - 大成功: 苏州新订单 +15 两
   - 成功: 加单 +8 两
   - 失败: 抢单失败, 但有 1 银赔偿

4. **🤰 妻子难产** (round 6-10, flag=wife_pregnant)
   - 触发条件: 妻子已孕
   - 检定: cash >= 3 (郎中费)
   - 成功: 母子平安 flag `child_born`
   - 失败: 难产妻子亡 flag `wife_dead` → 隐藏结局

5. **📜 织造太监采办** (round 8-12, prob=0.5)
   - 触发条件: 接近章节末
   - 检定: 无 (强制 fail)
   - 太监采办引发市场动荡，绸价波动
   - 玩家选择:
     - 借机卖高价 (greedy)
     - 拒绝 (righteous) → flag `refused_eunuch`
     - 普通出货 (safe)

## 🔀 跨章回响 (从第一章)

| 第一章 flag | 第二章影响 |
|---|---|
| `has_debt` | 每月扣息 -0.15 两 |
| `sold_loom` | 月产 -2 匹 |
| `met_big_merchant` | 苏州订单额外加成 |
| `learned_qixia` | 第二章可织"绮霞罗" (价值 +50%) |
| `zhou_favor` | 周大娘帮你找苏州买家 |
| `father_secret` | 第二章触发父亲密谈节点 |
| `pa_silk_urgent` | stamina -=5, 第二章开头疲态 |
| `prosperous` | 开局 +5 两 extra |
| `saw_outcast` | 镇上熟人, 容易借到工具 |
| `zhang_loan` | 张叔信任, 合股成功率 +20% |
| `zhang_helped` | 张叔主动提议合股 |
| `met_zhang` | 张叔基础好感 |

## 🎯 第二章关键节点详细设计

### Node: `intro_ch2_prosperous` (开局·家境小康)
```
【夏·雨·盛泽镇·辰时】
梅雨连绵，盛泽镇的河面上漂着水雾。
你站在自家院中，屋檐挂着水珠。两架织机静默。
张氏端着姜汤出来：'相公，进屋歇歇。'
——承接第一章"兴家结局"，这是沈家的小康之年。

[选项]
1. 🧵 赶织苏州订单 (cash +5 net, 2 月期限)
2. 🏠 修缮房屋 (cash -3, 父亲满意)
3. 💑 陪伴张氏 (flag wife_pregnant)
4. 📖 听父亲讲故事 (flag father_secret → 触发)
```

### Node: `climax_ch2_dye` (染色危机)
```
你把织好的素绸送到赵师傅处染色。
赵师傅接过绸，眼里一亮：'好料！但这颜色...'
他皱眉：'我近来得了一种怪病，染出来总不匀。'
张氏闻声从灶房出来：'莫不是又喝多了？'
赵师傅苦笑：'嫂子聪明。欠了酒债，心里苦。'

[检定] charisma ≥ 3
- 大成功: '赵老弟，我请你看大夫！' → 赵师傅传授染色技法
- 成功: 正常染色，cash -0.5
- 失败: 赵师傅染坏了 3 匹，cash -3

[后续选项]
1. 找苏州师傅 (贵 2 两，但稳)
2. 自己研究 (习得染色，但慢)
3. 重新买丝再织 (cash -4)
```

### Node: `climax_ch2_zhang_secret` (父亲秘密)
```
父亲把你叫到床前，声音微弱：
'儿啊，有些事为父一直瞒着你...'
他颤巍巍从枕下摸出一卷泛黄的文书。
'这是万历九年，为父给苏州织造局织一批贡绸的凭据。'
'那年太监李保采办，贪墨了银两，把罪名推到为父头上。'
'为父被打入大牢三月，虽最后平反，但再无力...'
他握住你的手：'这卷文书，你要替为父保管好。'
'若有朝一日...用得着。'

[选项]
1. 问父亲详情 → reveal_father_secret
2. 安慰父亲养病 → flag `father_will`
3. 不再追问 → flag `father_silent`

[后续影响]
- flag `father_will` → 第三章核心剧情触发
- flag `father_silent` → 第三章无此线
```

### 5 个第二章结局 (详细)

#### 1. `resolution_ch2_prosperous` - 兴家结局
```
秋初结算，你交了订单，攒下了二十两。

苏州恒德祥孙掌柜登门：'沈老弟手艺了得，来年继续。'
张氏抱着孩子（已满月），面有喜色：'相公，咱们...'

父亲安然无恙（若 flag father_better），或已安详离世
（若 flag father_secret → 临终托付）。

——万历十五年秋，沈家已非吴下阿蒙。

[选项]
1. ▶ 继续第三章《丝绢案》
2. ↺ 重玩
```

#### 2. `resolution_ch2_normal` - 平凡结局
```
订单如期完成，但利润微薄。
你带着十二两银子回家，松了口气。
张氏端来粥：'相公，歇歇吧。'
——日子还在继续。

[选项]
1. ▶ 继续第三章
2. ↺ 重玩
```

#### 3. `resolution_ch2_loss` - 违约结局
```
订单晚了半月，孙掌柜叹气：'沈老弟，这次...只能给八两。'
你攥着银钱回家，张氏一句话也没说。
父亲咳得更厉害了。
——商誉受损，flag `merchant_disgraced`

[选项]
1. ▶ 继续第三章 (困难模式)
2. ↺ 重玩
```

#### 4. `resolution_ch2_outcast` - 破产结局
```
又卖了织机，又卖了家具。
你蹲在空荡荡的屋中，满脸木然。
——梅雨、违约、赵师傅醉酒... 接踵而至。

[选项]
1. ↺ 重玩
```

#### 5. `resolution_ch2_widow` - 丧妻结局 (隐藏)
```
张氏难产，母子俱亡。
你抱着空襁褓，一夜白头。
父亲：'儿啊，这命...'
——flag `wife_dead`，孤身入第三章
```

---

# ⚖️ 第三章 《丝绢案》

> 时间: 万历十五年九月至次年二月（约 16 回合）
> 地点: 盛泽镇 / 苏州府 / 织造衙门
> 主线: 织造太监采办 / 政治漩涡 / 父亲冤案

## 📖 剧情背景

承接第二章。万历十五年秋，**苏州织造太监李保**（原型: 万历朝织造太监）南下采办贡绸。他手眼通天，与税关勾结，强买强卖。盛泽镇的织工们面临严峻选择：要么配合（卖高价、得好处），要么反抗（守清白、但得罪权贵）。

**核心剧情**: 父亲当年（万历九年）被李保诬陷的丝绢案真相浮出水面。第二章 flag `father_will`/`father_secret` 触发**复仇线**——玩家可以选择为父申冤，或隐忍不发。

**历史背景参考**:
- 万历年间 "一条鞭法" 推行后丝绢折纳加派
- 织造太监采办贡品，强征强买
- 江南织工抗税事件 (万历二十九年苏州织工抗税，但万历十五年还在酝酿)

## 🎭 第三章新角色

| 角色 | 身份 | 性格 | 备注 |
|---|---|---|---|
| **李保（太监）** | 苏州织造太监 | 贪婪/狠毒 | 主要反派 |
| **李保爪牙·周七** | 太监亲信 | 凶残/唯利 | 跑腿 |
| **苏州织造局书吏·宋明** | 新登场 | 圆滑/有良心 | 关键中间人，可买通 |
| **盛泽镇里正·周德** | 新登场 | 怕事/老实 | 镇里管事 |
| **苏州府学秀才·林文清** | 新登场 | 正直/理想主义 | 知识分子线 |
| **张居正遗党·王忠** | 新登场 | 落魄/有心机 | 政治伏笔 |
| **沈家表叔·沈万** | 新登场 | 富商/远亲 | 经济援助线 |
| **苏州织工·刘二** | 新登场 | 血性/冲动 | 抗税领袖 |

## 🌳 第三章节点分支图

```
intro_ch3_start (依赖第二章结局)
├─ flag prosperous → intro_ch3_prosperous (家境小康)
├─ flag normal → intro_ch3_normal (普通开局)
├─ flag loss → intro_ch3_loss (商誉受损, 困难)
├─ flag outcast → intro_ch3_outcast (破产开局)
└─ flag widow → intro_ch3_widow (丧妻开局)

intro_ch3_prosperous
├─ accept_eunuch_order (接太监订单) → escalation_ch3_complicity
├─ refuse_eunuch → escalation_ch3_resistance
└─ mediate → escalation_ch3_diplomacy

intro_ch3_loss
├─ seek_mercy (求太监减免) → fail → escalation_ch3_humiliation
├─ flee_to_suzhou → escalation_ch3_suzhou
└─ submit_completely → escalation_ch3_slavery

climax_ch3_conspiracy (李保阴谋)
├─ 父亲遗物 (flag father_will) → reveal_conspiracy_evidence
├─ 苏州织工血书 → join_resistance
└─ 沉默 → flag `silenced`

climax_ch3_tax (税关压迫)
├─ submit_tax (缴税) → 平安但穷
├─ resist_tax (抗税) → join_resistance → 大结局
└─ flee_tax (逃跑) → flag `fugitive`

climax_ch3_evidence (父亲冤案证据)
├─ submit_to_court → 出首 → escalation_ch3_trial
├─ burn_evidence → 隐忍 → flag `evidence_burned`
└─ sell_evidence → flag `sold_evidence` (卖给李保) → 大坏结局

resolution_ch3_*** (6 个结局)
├─ vindicator (申冤成功·父亲平反)
├─ resistance_leader (抗税领袖·牺牲)
├─ survivor (苟活·保全家业)
├─ rich_traitor (卖证据·发财·失名节)
├─ fugitive (流亡他乡)
└─ dead (死于抗税)
```

### 总节点目标: **40-50 节点**
### 总选项目标: **100-120 选项**
### 总结局目标: **6 个** (含 3 隐藏)

## 🎲 第三章随机事件 (6 个)

1. **🏛️ 税关加派** (round 1-3, prob=0.6) - 强制 fail
   - 织造太监要求每匹绸加税 0.3 两
   - 玩家: 接受/抗税/逃跑

2. **📜 织工血书** (round 2-6, prob=0.3) - 检定: courage ≥ 3
   - 大成功: 加入抗税联盟, flag `resistance_member`
   - 成功: 旁观
   - 失败: 被太监爪牙盯上, flag `watched`

3. **💰 表叔沈万求见** (round 3-8, prob=0.4) - 检定: kinship
   - 大成功: 表叔资助 15 两, flag `uncle_aid`
   - 成功: 仅得 5 两
   - 失败: 表叔拒见

4. **⚔️ 周七上门** (round 4-10, prob=0.5) - 检定: charisma ≥ 3
   - 大成功: 周七反而帮玩家 (伏笔回收)
   - 成功: 周七不再骚扰
   - 失败: 玩家被打, stamina -=20

5. **🤝 宋明书吏告密** (round 6-12, prob=0.25) - 检定: luck ≥ 4
   - 大成功: 获得太监采办账本 (扳倒李保关键)
   - 成功: 获得部分账本
   - 失败: 反被太监知晓, flag `compromise_found`

6. **🩸 织工起义** (round 10-16, prob=0.6) - 检定: courage
   - 大成功: 起义成功, flag `revolution_succeeded`
   - 成功: 玩家侥幸存活
   - 失败: 玩家被擒, 死/流放

## 🔀 跨章回响 (第一章 + 第二章 → 第三章)

| flag | 第三章影响 |
|---|---|
| **第一章** | |
| `has_debt` | 第一章债滚到第三章, 仍欠 3 两 |
| `met_big_merchant` | 苏州有人脉, 减少太监盘剥 |
| `sold_loom` | 月产 -2 匹 (无力购新机) |
| `zhou_favor` | 周大娘可帮你找苏州秀才林文清 |
| **第二章** | |
| `prosperous` (ch2) | 开局 cash +10 |
| `merchant_disgraced` (ch2) | 商誉受损, 苏州订单减少 |
| `master_dyer` (ch2) | 织染技艺高, 抗税时可召集同行 |
| `father_will` (ch2) | ⭐ 第三章核心: 父亲冤案线 |
| `father_secret` (ch2) | ⭐ 第三章核心: 揭露真相 |
| `knew_color_master` (ch2) | 染色独特, 太监可能求购 |
| `zhang_helped` (ch2) | 张叔可联合抗税 |
| `child_born` (ch2) | 第三章孩子, 家庭羁绊 |
| `wife_dead` (ch2) | 第三章孤身, 抗税决心 +1 |

## 🎯 第三章关键节点详细设计

### Node: `intro_ch3_prosperous` (家境小康开局)
```
【秋·晴·盛泽镇·午时】
金风送爽，盛泽镇的桂花开了。
你站在自家院中，三架织机吱呀作响。
张氏抱着刚满月的孩子，面有喜色。

忽然，镇东牙行来人：'沈老弟，苏州来了大人物。'
'织造局李公公要采办贡绸，整个盛泽镇都要出力。'

——这是万历十五年最大的一笔生意。
——但也是最危险的一笔。

[选项]
1. 主动接订单 (高利, 但风险)
2. 拒绝, 坚守本分 (低利, 但安全)
3. 暗中周旋 (中等, 需智慧)
4. 寻找盟友 (抗税前兆)
```

### Node: `climax_ch3_conspiracy` (父亲冤案·关键剧情)
```
承接 flag `father_will` / `father_secret`

夜深，你独自在灯下展开父亲遗下的文书。
那是一卷泛黄的丝绢, 上面有万历九年的官印。
你认出了几个名字：
- '织造太监李保' (采办贪墨)
- '原吴江县令王公' (现已升迁苏州知府)
- '父亲沈茂' (被诬陷, 流放三月)

——证据确凿。

[选项]
1. 递状苏州府 → 出首 → climax_ch3_trial
   - 大成功: 知府王公秉公办理, flag `father_vindicated`
   - 成功: 知府受理, 但被太监势力干扰
   - 失败: 反被太监陷害, flag `evidence_leaked`
2. 焚毁文书 → 隐忍 → flag `evidence_burned` → 平安但内心愧疚
3. 卖给太监 → 求财 → flag `sold_evidence` → 大坏结局
```

### Node: `climax_ch3_tax` (税关压迫·主线剧情)
```
李保的爪牙周七挨家挨户'收税'。
'每匹绸 0.3 两, 一两不能少！'
你看着张氏和孩子, 心中纠结。

[选项]
1. 缴税 (cash -3, 平安)
2. 抗税 (高风险, 高回报) → join_resistance
   - 检定: courage ≥ 4
   - 成功: 加入抗税联盟
   - 失败: 被擒, 死/流放
3. 逃跑 (flag `fugitive`) → 流亡他乡
4. 找苏州秀才林文清 (知识界支持) → climax_ch3_intellectual
```

### 6 个第三章结局 (详细)

#### 1. `resolution_ch3_vindicator` - 申冤成功 (大圆满)
```
苏州知府亲自审案, 李保伏法。
父亲当年的冤案平反, 朝廷下旨褒奖。
'沈氏一门, 忠义可风。'
你跪在父亲坟前：'爹, 您的冤屈昭雪了。'

张氏抱着孩子：'相公, 咱们回家。'
——flag `father_vindicated`, 玩家可开启第四章"中兴"

[后续选项]
1. ▶ 继续第四章《中兴》
2. ↺ 重玩
```

#### 2. `resolution_ch3_resistance_leader` - 抗税领袖 (悲剧英雄)
```
万历十五年十一月, 苏州织工起义。
你站在最前面, 率领盛泽镇的织工冲向税关。
刀光剑影, 血染青石。

最终, 朝廷派兵镇压。
你倒在血泊中, 看着张氏和孩子。
'活下去...'

——flag `revolution_succeeded` (短期胜利, 长期失败)
——flag `hero_dead` (玩家死, 家人被张叔照顾)
```

#### 3. `resolution_ch3_survivor` - 苟活者 (生存结局)
```
你缴了税, 隐忍不发。
李保被调走 (后任太监接手), 风波暂息。
家业保全, 但心中有愧。

父亲坟前, 你沉默良久。
'爹, 原谅儿子...'
——flag `survived_persecution`, 商誉仍在, 孩子长大

[选项]
1. ▶ 继续第四章
2. ↺ 重玩
```

#### 4. `resolution_ch3_rich_traitor` - 卖证据 (大坏结局)
```
你把父亲的文书卖给了李保, 得银 30 两。
李保笑着：'沈老弟识时务。'
你回家, 张氏问起, 你支吾其词。

三个月后, 父亲坟前被人泼了粪。
——flag `sold_evidence`, 你成了全镇公敌
——flag `family_disgraced`

[选项]
1. ↺ 重玩
```

#### 5. `resolution_ch3_fugitive` - 流亡 (边缘结局)
```
你没接太监订单, 也没抗税, 连夜逃走。
张氏抱着孩子, 跟着你沿运河南下。
盛泽镇在身后渐渐远去。
——flag `fugitive`, 你在杭州/南京开始新生活

[选项]
1. ▶ 杭州支线
2. ↺ 重玩
```

#### 6. `resolution_ch3_dead` - 死于抗税 (悲壮结局)
```
税关前, 你身中三刀。
周七狞笑：'这就是抗税的下场！'
你倒下, 看着天上的云。
'爹, 媳妇, 孩子... 对不住...'
——flag `hero_dead`, 家人被张叔照顾
```

---

# 🎯 节点数 & 选项数统计

## 第二章

| 类型 | 数量 |
|---|---|
| 节点 (含变体) | **35-40** |
| 选项 | **80-100** |
| 结局 | **5** (含 1-2 隐藏) |
| 随机事件 | **5** |
| 新角色 | **8** |
| 跨章回响 flags | **12** (从第一章) |

## 第三章

| 类型 | 数量 |
|---|---|
| 节点 (含变体) | **40-50** |
| 选项 | **100-120** |
| 结局 | **6** (含 3 隐藏) |
| 随机事件 | **6** |
| 新角色 | **8** |
| 跨章回响 flags | **17** (从第一+二章) |

## 两章合计

| 维度 | 第一章 | 第二章 | 第三章 | 三章总 |
|---|---|---|---|---|
| **节点** | 22 | 35-40 | 40-50 | 97-112 |
| **选项** | 55 | 80-100 | 100-120 | 235-275 |
| **结局** | 5 | 5 | 6 | **16** (含 6-7 隐藏) |
| **随机事件** | 3 | 5 | 6 | 14 |
| **角色** | 7 | 8 | 8 | **23** |
| **跨章回响** | - | 12 | 17 | - |

**重玩价值**: 由于 17 个跨章回响 flags + 14 个随机事件, 玩家至少需要 **8-10 次** 不同选择才能探索完整剧情。

---

# 📅 实施时间表

| 周 | 内容 | 产出 |
|---|---|---|
| 第 1 周 | 第二章: 节点设计 + 20 个节点实现 | 30+ 选项 |
| 第 2 周 | 第二章: 剩余 15 节点 + 5 随机事件 | 60+ 选项 |
| 第 3 周 | 第三章: 节点设计 + 20 个节点 | 30+ 选项 |
| 第 4 周 | 第三章: 剩余 25 节点 + 6 随机事件 | 70+ 选项 |
| 第 5 周 | 跨章回响 + E2E 测试 + 文档 | 全链路测试 |

**总计**: 5 周 = **6000-7000 行代码** + **15000-20000 字剧本**

---

# 🧪 自动化测试设计

## 跨章回响测试
```python
def test_ch1_to_ch2_flags():
    """验证第一章 flag 影响第二章"""
    # 选择有 debt 的开局
    ch1 = play_to_completion("borrow_money → buy_silk → chapter_complete")
    assert ch1.state.scripted_flags == {"has_debt", ...}
    
    # 进入第二章
    ch2 = start_chapter(2)
    # 验证第二章开头 cash 受 debt 影响
    assert ch2.state.cash < 5  # 因还息
```

## 多结局可达性测试
```python
def test_ch2_endings_reachable():
    """验证第二章 5 个结局都可达"""
    paths = [
        ("borrow_money → buy_silk_quality → repay", "resolution_ch2_prosperous"),
        ("borrow_money → wait → wait", "resolution_ch2_normal"),
        ("borrow_money → delay → delay", "resolution_ch2_loss"),
        ("sell_loom → sell_second → outcast", "resolution_ch2_outcast"),
        ("wife_pregnant → no_money", "resolution_ch2_widow"),
    ]
    for path, expected_ending in paths:
        result = simulate(path)
        assert result.ending == expected_ending
```

## LLM 降级集成测试
```python
def test_llm_fallback_starts_ch2():
    """LLM 失败时自动降级并启动第二章"""
    # Mock LLM 抛 ProviderAllFailedError
    mock_llm_failure()
    
    # 调用 /api/input
    resp = post("/api/input", {"input": "继续游戏"})
    
    # 应该收到 fallback_narrative (剧本模式自动启动第二章)
    assert resp.status == 503
    assert "fallback_mode" in resp.json()
    assert resp.json()["fallback_mode"] == "scripted"
    assert "ch2" in resp.json()["fallback_narrative"] or "第二章" in resp.json()["fallback_narrative"]
```

---

# 📋 下一步行动

**我建议立刻开始**: 第二章 20 个核心节点 (1 周)

| Day | 工作 |
|---|---|
| 1-2 | 节点设计稿 + 开局 4 节点 + 4 随机事件 |
| 3-5 | escalation 节点 (订单/扩张/家庭) + 8 节点 |
| 6-7 | climax 节点 (染色/秘密/税关) + 8 节点 + E2E |

**相关资源**:
- 现有 `chapter_01.py` 作为模板
- `rich.py` 多声部工具已就绪
- `engine.py` 已支持随机事件 + 环境注入
- `types.py` 数据模型完整

**需要确认的问题**:
1. 第二章的张氏怀孕剧情：是否需要详细设计？(影响死亡/生存线)
2. 第三章的李保反派：是否引入历史真实人物（李保是万历年间真实存在）
3. 父亲冤案"丝绢案"：是否对应万历九年真实事件（虚构但合理）
4. 是否需要在第二章引入新角色名字投票/调研？

需要我开始实现第二章的前 20 节点吗？

---

> 📌 **下一步**: 我将根据这个计划开始写第二章的具体节点和选项。预计 1 周完成核心 20 节点 + 5 结局 + 5 随机事件。