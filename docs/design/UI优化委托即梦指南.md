# 🎨 UI 优化委托即梦指南（v2.7+）

> **版本**：v1.0
> **日期**：2026-07-09
> **作者**：Claude
> **状态**：🆕 待实施

---

## 📋 文档目的

本文档作为"向即梦（AI 设计师）提交 UI 优化任务"的**标准化指南**。包含：

1. 项目背景与设计现状
2. 8 大可优化方向
3. 4 阶段 prompt 模板
4. ROI 排序的实施清单
5. 1 个超长完整 prompt（可直接复制）

---

## 🎯 项目背景

### 是什么

**历史注脚体验引擎** — 一个明万历十五年（1587）背景的 AI 当 DM 文字 RPG 游戏。

- **玩法**：玩家当苏州府吴江县盛泽镇织工，通过对话 + 选择 + 命运卡推动剧情
- **特色**：DE（极乐迪斯科）风格内在声音选项 + 8 SKILL 编排
- **完成度**：v2.7 — 66 个测试，命运卡完整闭环 + 完全可重放

### 当前设计系统

| 维度 | 现状 |
|---|---|
| **主色** | 宣纸米色 `#f5efe1` + 墨色 `#2c2416` + 朱砂 `#a02828` + 青铜 `#8b6f47` |
| **字体** | 宋体优先（Noto Serif SC / Source Han Serif SC）|
| **原则** | 留白为美（"计白当黑"）+ 慢节奏（800-1500ms 动效）+ 弱阴影 |
| **组件** | 13 个 design-system（Button / Card / Dialog / Chapter / Seal / Toast / ...）|
| **页面** | 主页（start menu）/ 8 步初始化向导 / 游戏页（侧栏 + 叙事 + 行动面板）|

### 文件结构

```
src/frontend/src/
├── lib/
│   ├── styles/
│   │   ├── tokens.css          # 设计令牌（颜色/字体/空间）
│   │   ├── base.css            # 全局基础样式
│   │   ├── index.css           # 入口
│   │   └── utilities.css       # 工具类
│   ├── components/
│   │   ├── design-system/      # 13 个原子组件
│   │   ├── game/               # 游戏专用组件
│   │   ├── modals/             # 弹层
│   │   └── layout/             # 布局
│   └── stores/                 # 状态管理
└── routes/
    ├── +layout.svelte          # 全局布局
    ├── +page.svelte            # 主页
    ├── game/                   # 游戏页
    ├── wizard/                 # 初始化向导
    └── login/                  # 登录
```

---

## 🎯 8 大可优化方向

### 1. 视觉风格 — 整体观感升级

#### 现状

| 元素 | 现状 | 缺什么 |
|---|---|---|
| 背景 | 静态米黄纯色 | **水墨晕染**效果（淡墨渐变 + 纸纹）|
| 章节标题 | 静态文字 | **装饰花纹**（回字纹/云纹/水波纹 SVG）|
| 印章 | 无 | **朱砂印章**（旋转 8° + 阴影 + 残缺纹理）|
| 边框 | 朴素 1px | **纸张撕裂边**（noise + clip-path）|
| 留白 | 多 | 优秀（保留）|

#### 即梦可给

- "水墨宣纸纹理背景图（低对比度 5% 透明，可平铺）"
- "明式家具木雕纹样 SVG（边框装饰元素，2-3 套）"
- "朱砂印章效果设计稿（带残缺纹理 + 旋转）"
- "明代刺绣图案（用于 loading 屏装饰）"

#### 验收标准

- 章节标题**有边框装饰**（不是光秃秃文字）
- 关键按钮**有印章 hover 效果**
- 背景**有水墨渐变**（不是纯色）

---

### 2. 字体 — 中西融合

#### 现状

| 用途 | 当前字体 |
|---|---|
| 标题/正文 | `Noto Serif SC`（思源宋体）|
| 数字 | `Noto Sans SC`（思源黑体）|
| 英文 | `Cormorant Garamond`（衬线）|
| 等宽 | `JetBrains Mono`|

#### 改进点

- 标题和正文**用同一个字体**（缺层次）
- 数字用**现代黑体**（缺历史感）
- 没有**品牌字体**（无标识）

#### 即梦可给

- 字体方案 4 套：
  - 标题：方正清刻本悦宋 / 康熙字典体（题字风格）
  - 正文：思源宋体 SC（保留）
  - 数字：Cormorant Garamond 衬线（古典数字感）
  - 英文：Cormorant Garamond / EB Garamond（保留）
- 特殊段落**字距/行距**精细调整（如开场"万历十五年，正月。"）

#### 验收标准

- 标题字体**明显区别于**正文
- 数字（财务、回合）**用衬线**（不是黑体）
- 开场白**字距加大**（有"题首"感）

---

### 3. 图标系统 — 一致性

#### 现状

| 元素 | 现状 |
|---|---|
| 主角 | `👤` emoji |
| 命运卡 | `🎴 / 💰 / ❤️ / ⏳ / ⚡` emoji 混用 |
| 状态 | `● / ○` 文字符号 |
| 菜单 | `▾ / ▸ / ↻ / →` ASCII 符号 |
| 财务 | `💰` emoji |

#### 改进点

- emoji **跨平台不一致**（Apple / Google / Microsoft 渲染不同）
- 按钮**无图标**（纯文字）
- 整体**风格不统一**（混用 emoji + ASCII）

#### 即梦可给

- "国风线性图标库（48 个核心图标，1.5px stroke SVG 矢量）"：
  - 角色：5 个（夫妻/子/女/老人/织工）
  - 命运卡：6 个（钱/心/时/力/护/知）
  - 状态：8 个（任务/期限/警告/成功/失败/暂停/继续/重试）
  - 位置：10 个（家/茶馆/织机/牙行/米行/码头/庙/书塾/市集/官府）
  - 行动：6 个（输入/发送/刷新/分享/复制/关闭）
  - 文档：5 个（书架/字典/纪事/规则/版本）
  - 系统：8 个（设置/帮助/退出/音量/亮度/锁屏/通知/账户）
- "印章式 emoji 替换方案（米色描边 + 朱砂填充）"

#### 验收标准

- 命运卡 6 种类型**用统一风格**图标（不是 emoji）
- 按钮**有图标**（不是纯文字）
- 所有图标**1.5px stroke 线性**风格

---

### 4. 动效 — 慢节奏美学

#### 现状

| 元素 | 当前 |
|---|---|
| 基础动效 | 800-1500ms（已有，慢节奏）|
| 章节切换 | **无**（直接换文字）|
| 命运卡抽卡 | **无**（直接显示）|
| 印章效果 | **无** |
| 文字渐入 | **无**（整段出现）|

#### 改进点

- 缺少"水墨"风格的细节动效
- 缺少"印章盖落"的物理感
- 缺少"命运卡翻牌"的立体感

#### 即梦可给

- **4 个动效 keyframes**：
  1. **章节切换水墨扩散**
     ```css
     @keyframes ink-spread {
       0% { clip-path: circle(0% at 50% 50%); opacity: 0; }
       60% { opacity: 1; }
       100% { clip-path: circle(150% at 50% 50%); opacity: 1; }
     }
     /* 时长 1200ms ease-out */
     ```
  2. **命运卡翻牌**
     ```css
     @keyframes card-flip {
       0% { transform: rotateY(0deg); }
       50% { transform: rotateY(90deg) translateY(-20px); }
       100% { transform: rotateY(360deg); }
     }
     /* 时长 1500ms cubic-bezier(0.4, 0, 0.2, 1) */
     ```
  3. **印章盖落**
     ```css
     @keyframes seal-stamp {
       0% { transform: scale(2) rotate(15deg); opacity: 0; }
       60% { transform: scale(0.9) rotate(7deg); opacity: 1; }
       80% { transform: scale(1.05) rotate(8deg); }
       100% { transform: scale(1) rotate(8deg); }
     }
     /* 时长 600ms ease-out */
     ```
  4. **文字渐入（一个字一个字）**
     ```css
     @keyframes char-fade-in {
       0% { opacity: 0; transform: translateY(4px); }
       100% { opacity: 1; transform: translateY(0); }
     }
     /* 间隔 30ms，每个字 200ms */
     ```

#### 验收标准

- 章节切换**有过渡动画**（不是瞬切）
- 命运卡**有翻牌**效果
- 印章按钮 hover **有盖落**动画
- 叙事**逐字**出现（不是整段）

---

### 5. 角色插画 — 视觉锚点

#### 现状

| 元素 | 现状 |
|---|---|
| 主角 | `👤` emoji |
| 沈氏（妻）| 无 |
| 阿宝（子）| 无 |
| 场景 | 无 |
| 事件 | 无 |

#### 改进点

- 玩家**对角色无视觉印象**（只有名字）
- 场景**全靠想象**（无锚点）
- 命运卡使用**无仪式感**

#### 即梦可给（图片生成）

> **重要**：根据 `Image Guidelines`，网页图片用：
> ```
> https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt={prompt}&image_size={size}
> ```
>
> `image_size` ∈
> - `square_hd` / `square` — 头像
> - `portrait_4_3` / `portrait_16_9` — 角色立绘
> - `landscape_4_3` / `landscape_16_9` — 场景

**4 张场景插画 prompt**：

1. **盛泽镇全景（封面）**
   ```
   Prompt: A panoramic illustration of Wanli-era (1587) Suzhou Wujiang Shengze town, Jiangnan water village, silk weavers' workshops along the canal, traditional Ming dynasty architecture with white walls and black tiled roofs, boats on the river, misty morning atmosphere, Chinese ink wash painting style with light watercolors, soft beige paper texture background, minimalist composition with lots of white space (negative space), no text, cinematic lighting
   Image Size: landscape_16_9
   ```

2. **织机坊内部**
   ```
   Prompt: Interior of a Ming dynasty silk weaver's workshop, two wooden looms, mulberry leaves and silk threads in the corner, wife cooking in the background, warm and humble atmosphere, soft natural light from the window, Chinese ink wash painting style with light colors, beige paper background, minimalist composition
   Image Size: landscape_4_3
   ```

3. **茶馆**
   ```
   Prompt: A small Ming dynasty tea house interior, wooden tables and benches, a few townsfolk drinking tea and chatting, the storyteller holding a book, warm lighting, Chinese ink wash painting style, muted colors, beige paper background, traditional Chinese interior details
   Image Size: landscape_4_3
   ```

4. **码头（市集）**
   ```
   Prompt: A bustling Jiangnan water town dock in the late Ming dynasty, merchants loading goods onto boats, silk bales, mulberry baskets, townsfolk in traditional clothing, a stone bridge in the background, Chinese ink wash painting style, soft colors, beige paper texture, cinematic composition
   Image Size: landscape_4_3
   ```

**2 张角色立绘**：

5. **沈氏（妻）**
   ```
   Prompt: A young Ming dynasty Chinese woman (age 25), simple but neat clothing, hair in a traditional bun with a single wooden hairpin, gentle smile, holding a kitchen knife, standing in a humble kitchen, Chinese ink wash painting style with light watercolors, soft and warm
   Image Size: portrait_4_3
   ```

6. **阿宝（子）**
   ```
   Prompt: An 8-year-old Ming dynasty Chinese boy, wearing a simple scholar robe, holding a half-eaten rice cake, running out from a courtyard, lively and innocent expression, Chinese ink wash painting style, soft colors
   Image Size: portrait_4_3
   ```

#### 验收标准

- 主页有**盛泽镇封面**（不是空白）
- CharCard 主角/沈氏/阿宝**有立绘**（不是 emoji）
- 4 个核心场景**有插画**（开局/家/茶馆/码头）

---

### 6. 布局 — 排版美学

#### 现状

| 元素 | 现状 |
|---|---|
| 三栏（侧栏 + 主区）| 朴素 280/1fr |
| 章节标题 | 居中 + 普通文字 |
| 段落 | 居中（部分左对齐）|
| 批注栏 | 无 |

#### 改进点

- 标题**居中**（缺"题首"感）
- 没有**批注/落款**栏（缺"手稿"感）
- 章节**无装饰边框**

#### 即梦可给

- "国风书籍内页版式设计稿（横排/竖排/批注栏各 1 套）"
- "分栏比例建议（4:6 / 3:7 / 5:5 含用途）"
- "批注样式模板（落款 + 印章位置）"

#### 验收标准

- 章节标题**有装饰边框**（回字纹/云纹）
- 叙事**首字下沉**（已有 FirstLetter 组件，但可以更国风）
- 长叙事**有竖排批注栏**（PC 端）

---

### 7. 主题色板 — 历史感

#### 现状（4 主色）

| 颜色 | Hex | 用途 |
|---|---|---|
| 宣纸 | `#f5efe1` | 背景 |
| 墨色 | `#2c2416` | 文字 |
| 朱砂 | `#a02828` | 强调 |
| 青铜 | `#8b6f47` | 边框 |

#### 缺（建议 +4）

| 颜色 | 建议 Hex | 用途 | 场景 |
|---|---|---|---|
| **月白** | `#e8e4d3` | 次背景 | 章节标题底色 |
| **水绿** | `#7a9a8a` | 自然 | 春/夏季节 |
| **靛青** | `#3a4a6b` | 严肃 | 官府/制度 |
| **赭石** | `#8a5a3a` | 温暖 | 冬/老物件 |

#### 情境背景色

| 情境 | 渐变 |
|---|---|
| 黎明 | `#f5efe1 → #ede0c5`（米黄→暖米）|
| 午后 | `#f5efe1 → #ede4cc`（米黄→米黄深）|
| 黄昏 | `#f5efe1 → #d4b08a`（米黄→赭石）|
| 夜晚 | `#2c2416 → #3a3220`（墨色深→墨色浅）|

#### 即梦可给

- "明式国风配色方案（6-8 色，含 hex / 用途 / 场景）"
- "江南四季色调（春绿/夏蓝/秋赭/冬灰）"
- "情境背景色渐变（黎明到夜晚 4 套）"

#### 验收标准

- tokens.css **加 4 颜色**（月白/水绿/靛青/赭石）
- 章节/事件**有情境背景色**（不是统一米黄）

---

### 8. 数据可视化 — 国风

#### 现状

| 元素 | 现状 |
|---|---|
| 数字 | 思源黑体 |
| 进度条 | 朴素渐变 |
| 关系网 | 无 |
| 时间线 | 普通文字列表 |

#### 改进点

- 财务数字**用现代黑体**（缺历史感）
- 进度条**朴素**（缺仪式感）
- 关系网**缺失**（玩家看不清 NPC 间关系）

#### 即梦可给

- "财务/健康/关系视觉化方案（毛笔字 + 印章）"
- "进度条样式（朱砂渐变 + 印章边框）"
- "关系网图（盛泽镇 NPC 关系可视化，水墨节点 + 关联线）"

#### 验收标准

- 财务数字**用衬线字体**（不是黑体）
- 进度条**有印章边框**
- 关系网**有可视化**（人物档案页）

---

## 📝 4 阶段 prompt 模板

### 阶段 1：风格定位

```
你是 UI 设计师。请基于这个项目：
- 万历十五年 (1587) 背景
- AI 当 DM 的文字 RPG 游戏
- 当前设计：宣纸/墨色/朱砂/青铜 + 宋体
- 目标：现代极简 × 明代国风雅致

请给我：
1. 视觉风格定位（3 句话）
2. 6-8 色色板（含 hex）
3. 字体方案（标题/正文/数字/英文）
```

### 阶段 2：组件优化

```
请帮我重新设计这些组件：
1. Button（4 种：主/次/危险/禁用）
2. Card（角色卡 + 任务卡 + 财务卡）
3. Modal（弹层：命运卡使用 / 人物档案 / 剧情回顾）
4. Toast（提示：成功/警告/错误）

要求：
- 风格统一（明代国风雅致）
- 动效慢节奏（800-1500ms）
- 弱阴影（不破坏素雅）
- 给我 SVG/CSS 代码
```

### 阶段 3：插画需求

```
请生成下列插画（用即梦图片生成）：
1. 盛泽镇全景（开局封面）
2. 织机坊内部（家庭场景）
3. 茶馆（社交场景）
4. 码头（市集场景）

要求：
- 风格：明代工笔 + 现代极简
- 色调：宣纸底 + 墨色
- 构图：留白为主（计白当黑）
- 尺寸：1920x1080（封面）+ 800x600（场景）
```

### 阶段 4：动效设计

```
请设计下列动效：
1. 章节切换（水墨扩散）
2. 命运卡抽卡（3D 翻牌）
3. 印章盖落（缩放 + 旋转）
4. 文字渐入（一个字一个字）

要求：
- 时间曲线：cubic-bezier(0.4, 0, 0.2, 1)
- 时长：800-1500ms
- 缓动：ease-out（不要 linear）
- 给我 CSS keyframes 代码
```

---

## 🎯 ROI 排序实施清单

| # | 任务 | 难度 | 收益 | 状态 |
|---|---|---|---|---|
| 1 | **国风色板扩充**（+4 色）| 低 | 高 | ⬜ |
| 2 | **印章按钮组件** | 中 | 高 | ⬜ |
| 3 | **水墨背景图** | 中 | 高 | ⬜ |
| 4 | **章节装饰花纹 SVG** | 中 | 中 | ⬜ |
| 5 | **盛泽镇场景插画 ×4** | 中 | 中 | ⬜ |
| 6 | **动效 keyframes 库** | 中 | 中 | ⬜ |
| 7 | **图标系统统一** | 高 | 中 | ⬜ |
| 8 | **角色立绘 ×2** | 高 | 中 | ⬜ |
| 9 | **明式字体方案** | 低 | 中 | ⬜ |
| 10 | **关系网图可视化** | 高 | 低 | ⬜ |

**建议**：先做 #1 + #2 + #3 + #6（高 ROI），后做 #4 + #5（中等 ROI）。

---

## 🚀 1 个超长完整 prompt（可直接复制）

```
你是 UI 设计师 + 平面设计师 + 动效设计师三合一。

任务：帮我优化"历史注脚体验引擎"（一个万历十五年背景的 AI 当 DM 的文字 RPG 游戏）的 UI。

## 项目背景
- 时代：明万历十五年（1587），苏州吴江盛泽镇
- 主角：织工家庭
- 玩法：对话 + 选择 + 命运卡 + 文字地图
- 受众：喜欢"国风"+"中国历史"+"叙事游戏"的玩家

## 当前设计系统
- 主色：宣纸米色 #f5efe1 + 墨色 #2c2416 + 朱砂 #a02828 + 青铜 #8b6f47
- 字体：宋体优先（Noto Serif SC）
- 原则：留白为美（"计白当黑"）+ 慢节奏（800-1500ms 动效）+ 弱阴影
- 已有：13 个 design-system 组件（Button / Card / Dialog / Chapter / Seal / Toast / ...）

## 我需要你提供
1. **风格定位**（3 句话总结）
2. **扩充色板**（6-8 色，含 hex + 用途 + 场景）
3. **字体方案**（标题/正文/数字/英文 4 套，推荐名字）
4. **3 个核心组件重设计**：
   - Button（含 4 种状态）
   - Modal（命运卡使用 + 人物档案）
   - Toast（含图标 + 文字 + 操作）
   给我 SVG/CSS/HTML 代码
5. **4 张插画 prompt**（用于即梦图片生成）：
   - 盛泽镇全景（封面，1920x1080）
   - 织机坊（场景，800x600）
   - 茶馆（场景，800x600）
   - 码头（市集，800x600）
6. **4 个动效 keyframes**：
   - 章节切换（水墨扩散）
   - 命运卡翻牌
   - 印章盖落
   - 文字渐入
7. **图标系统建议**（48 个核心图标的清单）
8. **3 个排版规则**（分栏 / 字距 / 段落）
9. **1 个首页 Landing 设计稿描述**（给 Figma 用）

## 输出格式
- Markdown 分章节
- CSS 代码用 ```css 包裹
- SVG 用 ```xml 包裹
- 插画 prompt 用 code block + 关键细节
```

---

## 📐 集成指南（即梦输出后如何落码）

### 颜色（直接加到 tokens.css）

```css
:root {
  /* 原 4 色保留 */
  --color-paper: #f5efe1;
  --color-ink: #2c2416;
  --color-cinnabar: #a02828;
  --color-bronze: #8b6f47;

  /* 🆕 即梦给的新色 */
  --color-moon-white: #e8e4d3;     /* 月白 */
  --color-water-green: #7a9a8a;    /* 水绿 */
  --color-indigo: #3a4a6b;         /* 靛青 */
  --color-ochre: #8a5a3a;          /* 赭石 */

  /* 🆕 情境背景渐变 */
  --bg-dawn: linear-gradient(180deg, #f5efe1 0%, #ede0c5 100%);
  --bg-dusk: linear-gradient(180deg, #f5efe1 0%, #d4b08a 100%);
  --bg-night: linear-gradient(180deg, #2c2416 0%, #3a3220 100%);
}
```

### 字体（更新 tokens.css）

```css
:root {
  --font-display: "方正清刻本悦宋", "Noto Serif SC", serif;
  --font-body: "Noto Serif SC", serif;
  --font-numeric: "Cormorant Garamond", "Noto Serif SC", serif;  /* 衬线数字 */
  --font-en: "Cormorant Garamond", "EB Garamond", Georgia, serif;
}
```

### 动效（新增 animations.css）

```css
/* 🆕 水墨扩散 */
@keyframes ink-spread {
  0% { clip-path: circle(0% at 50% 50%); opacity: 0; }
  60% { opacity: 1; }
  100% { clip-path: circle(150% at 50% 50%); opacity: 1; }
}

/* 🆕 翻牌 */
@keyframes card-flip {
  0% { transform: rotateY(0deg); }
  50% { transform: rotateY(90deg) translateY(-20px); }
  100% { transform: rotateY(360deg); }
}

/* 🆕 印章盖落 */
@keyframes seal-stamp {
  0% { transform: scale(2) rotate(15deg); opacity: 0; }
  60% { transform: scale(0.9) rotate(7deg); opacity: 1; }
  80% { transform: scale(1.05) rotate(8deg); }
  100% { transform: scale(1) rotate(8deg); }
}

/* 🆕 文字渐入 */
@keyframes char-fade-in {
  0% { opacity: 0; transform: translateY(4px); }
  100% { opacity: 1; transform: translateY(0); }
}
```

### 插画（直接用 Image Generation 替换 emoji）

```svelte
<!-- CharCard.svelte 主角头像 -->
<img
  src="https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=A%20young%20Ming%20dynasty%20Chinese%20silk%20weaver%20male%2C%20age%2030%2C%20portrait%2C%20ink%20wash%20style&image_size=portrait_4_3"
  alt="李半仙"
  class="char-card-portrait"
/>
```

---

## 📂 文件命名建议

新增文件：
- `src/frontend/src/lib/styles/animations.css` — 动效库
- `src/frontend/static/images/scenes/` — 场景插画
- `src/frontend/static/images/characters/` — 角色立绘
- `src/frontend/static/icons/` — 图标库

修改文件：
- `src/frontend/src/lib/styles/tokens.css` — 加 4 色
- `src/frontend/src/lib/styles/base.css` — 加 3 个动效 class
- `src/frontend/src/lib/components/design-system/Button.svelte` — 加印章效果
- `src/frontend/src/lib/components/game/CharCard.svelte` — emoji 换立绘

---

## ✅ 验收清单

完成所有 10 项后检查：

- [ ] tokens.css 加 4 色（月白/水绿/靛青/赭石）
- [ ] 4 个动效 keyframes 入库
- [ ] 4 张场景插画（盛泽镇/织机/茶馆/码头）
- [ ] 2 张角色立绘（沈氏/阿宝）
- [ ] 48 个 SVG 图标替换 emoji
- [ ] Button 加印章 hover 效果
- [ ] CharCard 头像换立绘
- [ ] 章节标题加装饰边框
- [ ] 命运卡有翻牌动画
- [ ] 叙事文字逐字渐入

---

## 🔗 相关文档

- [产品设计文档 v4.0](./产品设计文档.md) — 主设计
- [01-decision-log Decision 006](../01-decision-log.md#decision-006--现代-cssv27--clamp--container-queries) — 现代 CSS
- [Field Registry v2.7](../api/FIELD_REGISTRY.md) — API 字段

---

**作者注**：本文档是"委托任务"的**清晰标准**。即梦读完应能 80% 准确输出结果，剩下 20% 需多次迭代对齐。
