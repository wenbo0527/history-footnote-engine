# 事件 ID 命名规范（v1.7.30+）

> 解决核心问题：**当 LLM 自由生成 narrative 时，如何识别/捕获结构化变更？**

## 核心思路

所有"结构化变更"（财务/城市/家人/财产/库存）通过标准化 **EventId** 标识。
DM 在 narrative 后输出 `<events>` XML 块，后端解析为 GameState 变更。

## EventId 命名格式

```
<domain>.<action>.<subject>.<detail>
```

- `domain`：领域（fin / city / fam / gen / prop / inv）
- `action`：动作（sell/buy/borrow/...）
- `subject`：对象（silk/thread/...）—— **可选**
- `detail`：细节（city_id / member_id / ...）—— **可选**

## 已定义 EventId 列表

### 财务（fin.*）

| EventId | 含义 | 字段 | 示例 |
|---|---|---|---|
| `fin.sell_silk` | 卖绸 | amount, location, note | `<event id="fin.sell_silk" amount="0.5" location="盛泽" note="卖湖绫一匹"/>` |
| `fin.buy_thread` | 买丝 | amount, location, note | `<event id="fin.buy_thread" amount="2.0" location="盛泽"/>` |
| `fin.pay_tax` | 缴税 | amount, location, note | `<event id="fin.pay_tax" amount="1.5" location="盛泽" note="夏税"/>` |
| `fin.borrow` | 借钱 | amount, location, note | `<event id="fin.borrow" amount="2.0" location="盛泽" note="向王二叔借"/>` |
| `fin.repay` | 还钱 | amount, location, note | `<event id="fin.repay" amount="1.0" location="盛泽"/>` |
| `fin.deposit_interest` | 存款利息 | amount | （月度自动结算）|
| `fin.debt_interest` | 欠债利息 | amount | （月度自动结算）|
| `fin.workshop_rent` | 铺面租金 | amount | （月度自动结算）|
| `fin.monthly_burn` | 月基础开销 | amount | （月度自动结算）|
| `fin.gift_in` | 收到礼金 | amount, from | `<event id="fin.gift_in" amount="0.3" from="邻居王二叔"/>` |
| `fin.gift_out` | 送出礼金 | amount, to | `<event id="fin.gift_out" amount="0.5" to="里长家"/>` |

### 城市（city.*）

| EventId | 含义 | 字段 | 示例 |
|---|---|---|---|
| `city.arrive.{city_id}` | 到达城市 | city_id, note | `<event id="city.arrive.suzhou" note="阊门码头登岸"/>` |
| `city.leave.{city_id}` | 离开城市 | city_id, note | `<event id="city.leave.suzhou"/>` |

### 家人（fam.*）

| EventId | 含义 | 字段 | 示例 |
|---|---|---|---|
| `fam.meet.{member_id}` | 与家人相见 | member_id, location | `<event id="fam.meet.fm_wife"/>` |
| `fam.health.{member_id}.{status}` | 家人健康变化 | member_id, status | `<event id="fam.health.fm_son.sick" status="sick"/>` |
| `fam.death.{member_id}` | 家人亡故 | member_id | `<event id="fam.death.fm_father"/>` |
| `fam.relationship.{member_id}.{score_delta}` | 关系分变化 | member_id, score_delta | `<event id="fam.relationship.fm_wife.+10"/>` |

### 谱系（gen.*）

| EventId | 含义 | 字段 |
|---|---|---|
| `gen.ancestor.{entry_id}.known` | 得知祖先 | entry_id, name, generation |
| `gen.ancestor.{entry_id}.location` | 祖先位置变化 | entry_id, location |

### 城市财产（prop.*）

| EventId | 含义 | 字段 |
|---|---|---|
| `prop.buy.{city_id}` | 在某城市买财产 | city_id, type, name, value, rent_per_month |
| `prop.sell.{city_id}` | 卖财产 | city_id, prop_id |
| `prop.rent_change.{city_id}` | 租金变化 | city_id, prop_id, rent_per_month |

### 跨城库存（inv.*）

| EventId | 含义 | 字段 |
|---|---|---|
| `inv.buy.{city_id}.{item_id}` | 在某城市买货 | city_id, item_id, type, name, qty, unit_value |
| `inv.sell.{city_id}.{item_id}` | 在某城市卖货 | city_id, item_id, qty, unit_value |
| `inv.transfer.{item_id}.{from}_{to}` | 跨城运货 | item_id, from, to, qty |
| `inv.consume.{item_id}` | 消耗库存 | item_id, qty, reason |

## DM 输出格式

```xml
<narrative>
（玩家在阊门码头的所见所闻 + 困境 + 钩子）
</narrative>

<events>
  <event id="fin.sell_silk" amount="0.5" location="盛泽" note="卖湖绫一匹给吴掌柜"/>
  <event id="city.arrive.suzhou" note="阊门码头登岸"/>
</events>
```

**注意**：
- `<events>` 块在 `<narrative>` 之后
- 每条 event 独立一行
- 必填字段：id；选填字段：amount/location/note/...

## 后端解析路径

```
DM 输出
   ↓
event_parser.parse_events()
   ↓
[{"id": "fin.sell_silk", "amount": "0.5", ...}]
   ↓
event_parser.apply_event(state, event)
   ↓
state.apply_financial_change(...)  // 触发校验 + log
   ↓
GameState 持久化（自动）
```

## 校验机制

每类事件有严格校验：
- 财务类：amount 必须 ≤ 100 两（apply_financial_change 上限）
- 城市类：city_id 必须在 era.world.cities 中
- 家人类：member_id 必须在 state.family_members 中
- 财产类：city_id + prop_id 必须有效
- 库存类：qty ≥ 0，city_id 有效

校验失败 → 静默跳过 + 错误日志（不阻断叙事）

## 与 4 类持久化的关系

| 持久化字段 | 触发 EventId |
|---|---|
| `cash/rice/debt/monthly_burn/financial_log` | `fin.*` |
| `family_members` | `fam.*` |
| `genealogy` | `gen.*` |
| `city_properties` | `prop.*` |
| `inventory` | `inv.*` |
| `current_city` | `city.*` |

## 3 层识别（设计）

| Layer | 触发 | 准确率 | 实现 |
|---|---|---|---|
| 1 | DM 输出 `<events>` 块 | 100% | v1.7.30+ 默认 |
| 2 | narrative 模糊匹配（动词+金额+物品）| 70-80% | v1.7.30+ fallback |
| 3 | 玩家主动标注 | 100% | v1.7.30+ 兜底 |

## 月度结算（Settlement）

每月（每 3 回合）自动结算：
1. `fin.monthly_burn` —— 玩家 cash 减少
2. `fin.deposit_interest` —— cash 0.3% 利息
3. `fin.debt_interest` —— debt 1.5% 利息
4. `fin.workshop_rent` —— 4 城市铺面租金累加
5. `inv.consume.*` —— 玩家 + 同城家人口粮消耗

结算时统一调 `state.apply_financial_change()`，自动入 log。

## 持续扩展

加新 EventId = 加 1 个 case（`event_parser._apply_*_event`） + 加 1 行 type_map。
