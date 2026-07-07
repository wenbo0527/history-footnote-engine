# 调研报告：特定场景下Agent越用Token消耗越少是否可能？

## 核心结论

**有可能，但需要严格限定“越用越少”的含义。** Agent的token消耗不会因为“用久了”就自动下降——它不是学习曲线。但在特定场景下，通过工程手段可以让Agent的**单次请求有效成本**随使用递减，递减幅度可达60%-90%。核心机制有三条：

1. **Prompt Caching（前缀缓存）**：最成熟、最立竿见影的机制，缓存命中率越高，单次请求成本越低
2. **记忆工程（Memory Engineering）**：让Agent跨session积累知识，减少重复检索和冗余上下文
3. **上下文工程（Context Engineering）**：渐进式加载、惰性工具注入，按需喂信息而非全量塞入

关键区分：**“越用token越少”≠“模型变聪明了”，而是“工程上避免了重复计算”。**

---

## 一、为什么Agent天然“越用越贵”？

先理解问题的反面——为什么不做优化的Agent一定是越跑越贵的。

### 1.1 Agent的token消耗结构

Agent不是“调用次数多”，而是“每次调用上下文重”。一个典型Agent工作流的token消耗构成：

| 消耗环节 | 占比 | 特征 |
|---------|------|------|
| System Prompt（每次重复发送） | 30%-40% | 固定成本，随调用次数线性增长 |
| 工具描述（Tool Definitions） | 15%-25% | 工具越多，描述越长 |
| 对话历史（Context Window） | 20%-30% | 多轮对话累积增长 |
| 实际输出（Agent响应） | 10%-20% | 唯一产生价值的部分 |

**核心洞察：Agent 80%+ 的token消耗是重复的、可优化的。**

### 1.2 “滚雪球”效应

实测数据（含工具调用膨胀）：

| 轮次 | 实测消耗 |
|------|---------|
| 第1轮 | ~2，100 tokens |
| 第5轮 | ~22，000 tokens |
| 第20轮 | ~102，000 tokens |
| 第30轮 | ~200，000+ tokens |

第30轮的消耗是第1轮的100倍。这是因为LLM的API是无状态的——模型本身没有跨请求的记忆，每一轮交互都必须把之前所有的对话历史、工具描述、系统指令全部重新发送。

### 1.3 历史依赖型架构的根本问题

北京邮电大学等机构的研究指出，主流Agent架构是“历史依赖型”的——模型做第t步决策时，输入的是从0到t-1的所有历史信息。这导致两个致命伤：
- **计算成本的指数级灾难**：Transformer注意力机制计算量随上下文长度平方增长
- **信号被噪声淹没**：长历史中充斥冗余信息，分散模型注意力

---

## 二、让Agent“越用越省”的三大机制

### 2.1 Prompt Caching：砍掉60%-90%输入成本

**这是目前最成熟、最立竿见影的“越用越省”机制。**

#### 原理

Prompt Caching的核心思路：当多个请求的前缀相同（比如同一份system prompt + 同样的工具定义），底层不用每次都重新做注意力计算，而是直接复用之前的KV Cache数据。

关键点：**缓存是字节级前缀匹配，不是语义匹配。** 字节1-3000跟上次请求完全一样→命中；第3001个字节变了→后面全重算。

#### 计价机制

Anthropic的计价结构（Sonnet 4.6 / Opus 4.7）：

| 类型 | 单价倍率 | 说明 |
|------|---------|------|
| 普通输入 | 1.0× | base price |
| Cache write | 1.25× | 第一次把内容写进缓存 |
| Cache read | 0.1× | 命中缓存的后续请求 |

**净收益 = 命中次数 × 0.9 - 0.25。** 至少要在5分钟TTL里命中1次才不亏，命中2次以上才开始真省。

#### 生产级数据

- **Claude Code**：缓存命中率92%，成本降低81%
- **阿里云通义团队**（KVCache in the Wild论文，2025）：to-B场景下97%的缓存命中来自单轮请求的system prompt共享；to-C场景62%的KV Cache block可被复用
- **Manus团队 @peakji**：公开指出缓存命中率（Cache Hit Rate）是衡量生产级AI Agent最核心的单一指标
- **Claude Code团队**：cache hit rate下降会触发生产事故级别的告警——对Anthropic而言，cache miss就是production incident

#### 什么场景下“越用越省”效果最明显？

Prompt Caching在以下场景效果最佳：

1. **长system prompt + 频繁短查询**（客服/编程助手）：system prompt动辄上万token，每次查询都重复发送，缓存后每次只付0.1×
2. **多工具多步骤流程**：工具定义固定不变，缓存后每一步都省
3. **知识库互动**：整篇文档缓存后，多次提问无需重复上传
4. **代码助手**：代码库摘要缓存后，自动补全和问答成本骤降

**关键条件：前缀越稳定、调用越频繁，“越用越省”效果越显著。**

#### 局限性

- TTL有限：默认5分钟，最长1小时（需额外付费）
- 字节级匹配：一个空格、一个时间戳、一个用户ID差异，全部miss
- 缓存生命周期极短：to-B场景下P99仅97秒
- 只省输入成本，不省输出成本

---

### 2.2 记忆工程（Memory Engineering）：跨session积累，减少重复检索

**这是让Agent“越用越聪明”从而间接省token的机制。**

#### 核心思路

让Agent拥有跨session的持久记忆，避免每次都从零开始。代表工具/实践：

| 工具/实践 | 核心机制 |
|----------|---------|
| LLM Wiki | 把项目知识结构化存储，Agent按需查阅而非全量塞入上下文 |
| Letta | 长期记忆管理，自动决定什么该记、什么该忘 |
| Mem0 | 智能记忆层，跨对话保持用户偏好和上下文 |
| QoderWork Memory | 代码级记忆，记住之前的决策和踩坑 |

#### “越用越省”的逻辑

1. **第一次**：Agent需要大量token来理解上下文、检索知识、建立认知
2. **后续**：Agent已有记忆，只需增量更新，跳过重复检索和冗余解释
3. **RTK集成**（Retrieval-Token-Knowledge）：据51CTO文章，RTK集成可实现Token消耗再降60%-80%

#### 与Prompt Caching的区别

- Prompt Caching是**同一session内**的缓存，省的是重复计算
- 记忆工程是**跨session**的知识积累，省的是重复检索和冗余上下文

两者叠加效果：Prompt Caching砍掉重复计算成本，记忆工程砍掉重复信息获取成本。

---

### 2.3 上下文工程（Context Engineering）：按需喂信息，而非全量塞入

#### 核心策略

1. **渐进式上下文加载（Progressive Disclosure）**：先给Agent最少必要信息，按需追加，而非一开始就塞满上下文
2. **工具与MCP的惰性加载**：不把所有工具描述一次性塞入prompt，只在需要时才加载相关工具
3. **语义缓存（Semantic Cache）**：不是字节级匹配，而是语义级匹配——相似的问题直接返回缓存答案，根本不调用模型
4. **模型路由与级联**：简单问题用小模型（便宜），复杂问题才用大模型（贵），避免杀鸡用牛刀
5. **子Agent委派**：主Agent只做调度，具体执行交给专门的子Agent，每个子Agent的上下文更小更聚焦

#### 实测效果

- OpenClaw实测：每轮固定开销从~11，500 token降到~6，500 token，降幅43%
- Prompt Caching + 模型路由组合：降本80%
- 多智能体协同系统：通过系统性优化策略，Token使用成本可降低60%-80%

---

## 三、哪些场景下“越用越省”最可能实现？

综合以上机制，**“越用token越少”需要同时满足以下条件**：

### 3.1 必要条件

| 条件 | 为什么必须 |
|------|----------|
| **前缀稳定** | Prompt Caching依赖字节级前缀匹配，system prompt和工具定义不能频繁变动 |
| **调用频繁** | 缓存TTL只有5分钟-1小时，调用间隔太长缓存就失效了 |
| **场景收敛** | 同类问题反复出现，语义缓存才能命中 |
| **知识可沉淀** | 场景中的知识可以结构化存储，让记忆工程发挥作用 |

### 3.2 最适合的场景

1. **客服/工单处理Agent**：system prompt固定、问题类型收敛、知识库可沉淀——三大机制全部适用
2. **代码助手/编程Agent**：项目上下文稳定、工具定义固定、代码知识可积累——Claude Code已验证92%缓存命中率
3. **数据分析Agent**：查询模式收敛、数据schema固定、分析逻辑可沉淀
4. **文档审核Agent**：审核规则固定、文档类型收敛、审核经验可积累

### 3.3 不适合的场景

1. **探索性/创造性任务**：每次请求差异大，前缀不稳定，缓存命中率低
2. **低频调用场景**：调用间隔超过TTL，缓存来不及命中
3. **多用户独立上下文**：每个用户的前缀不同，缓存无法跨用户复用
4. **长链推理任务**：上下文持续膨胀，历史依赖型架构的“滚雪球”效应难以避免

---

## 四、学术前沿：从架构层面解决“越跑越贵”

### 4.1 STEP-HRL：层级强化学习

北京邮电大学等机构提出的STEP-HRL框架，试图从架构层面打破历史依赖型Agent的“越跑越贵”问题：
- 核心思路：不再把所有历史信息塞入prompt，而是通过层级强化学习让Agent学会“只看关键信息做决策”
- 效果：减少上下文膨胀，同时提升决策质量

### 4.2 Agent Lightning：无代码改造的强化学习

微软亚洲研究院提出的Agent Lightning框架：
- 将Agent的执行经验转化为RL训练数据
- Agent越用越多的执行数据→训练信号→模型本身变强→同样任务需要更少token
- 这是唯一一条“模型本身变聪明→token自然减少”的路径，但需要工程投入

---

## 五、总结：一张图看清“越用越省”的全景

```
Agent "越用越省" 的三层机制
├── 第一层：Prompt Caching（同session内）
│   ├── 机制：前缀字节匹配，复用KV Cache
│   ├── 效果：输入成本降至10%
│   ├── 条件：前缀稳定 + 调用频繁
│   └── 代表：Claude Code 92%命中率，成本降81%
│
├── 第二层：记忆工程（跨session）
│   ├── 机制：知识沉淀，减少重复检索
│   ├── 效果：Token消耗再降60%-80%
│   ├── 条件：知识可结构化 + 场景收敛
│   └── 代表：LLM Wiki + Mem0 + Letta
│
└── 第三层：上下文工程（架构级）
    ├── 机制：按需加载，渐进式披露
    ├── 效果：单轮开销降40%-80%
    ├── 条件：工具可惰性加载 + 模型可路由
    └── 代表：Progressive Disclosure + 语义缓存 + 子Agent委派
```

**最终判断**：Agent“越用token越少”在特定场景下完全可能，但不是自动发生的——它是一系列工程决策的结果。最立竿见影的是Prompt Caching（当天见效），最深远的是记忆工程（持续积累），最根本的是上下文工程（架构重构）。三者叠加，理论上可以将Agent的token成本降低一个数量级。

---

## 信息来源

1. 2026 Agent Token成本优化实战：Prompt Caching + 模型路由组合降本80% - CSDN (https：//blog.csdn.net/tzchao111/article/details/159769315)
2. OpenClaw Token成本优化完全指南：实测降低43%的方案 - CSDN (https：//blog.csdn.net/qcx23/article/details/160032780)
3. Prompt Caching： AI Agent的隐形基础设施 - CSDN (https：//blog.csdn.net/Python_0011/article/details/158929410)
4. Agent为何“越跑越贵”？STEP-HRL引入层级强化学习 - 腾讯云 (https：//cloud.tencent.com/developer/article/2698424)
5. AI Agent省50%Token的秘密：Prompt Caching到底缓存了什么 - CSDN (https：//blog.csdn.net/2401_87961121/article/details/161480685)
6. Claude prompt caching用对了能省60-80%输入费 - CSDN (https：//blog.csdn.net/cmzznet/article/details/161059736)
7. 一块被忽视的算力金矿：关于Prompt Caching你需要知道的一切 - 51CTO (https：//www.51cto.com/aigc/11620.html)
8. LLM Prompt Cache深度解析 - CSDN (https：//blog.csdn.net/m0_59163425/article/details/158852000)
9. Anthropic新功能解读：提示词缓存 - CSDN (https：//blog.csdn.net/m0_59163425/article/details/149233528)
10. 如何降低大模型调用带来的成本 - CSDN (https：//blog.csdn.net/2403_86965941/article/details/162494489)
11. AI Coding省80% Token还越用越聪明？LLM Wiki + RTK + AGENTS.md三件套实战全解 - 51CTO (https：//www.51cto.com/article/846985.html)
12. Agentic AI实战：如何降低Token成本 - 51CTO (https：//www.51cto.com/article/843049.html)
13. 《多智能体协同：基于大语言模型的工程实践与系统构建》- 周佺喜，电子工业出版社，2026
14. Agent Lightning： Adding reinforcement learning to AI agents without code rewrites - Microsoft Research (https：//www.microsoft.com/en-us/research/blog/agent-lightning-adding-reinforcement-learning-to-ai-agents-without-code-rewrites/)

访问时间：2026-07-07
