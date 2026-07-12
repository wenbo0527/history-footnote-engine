# api/ · HTTP API 文档

> **目的**:后端 HTTP API 端点 + 字段规范

## 📋 文件列表

| 文件 | 主题 |
|---|---|
| [FIELD_REGISTRY.md](FIELD_REGISTRY.md) | 字段注册表:前端 type ↔ 后端字段名映射 |
| [openapi.yaml](openapi.yaml) | OpenAPI 3 规范(自动生成) |

## 🔍 快速定位

| 我想... | 看这里 |
|---|---|
| **看所有 API 端点** | [openapi.yaml](openapi.yaml) |
| **看字段命名规则** | [FIELD_REGISTRY.md](FIELD_REGISTRY.md) |
| **后端代码** | [../../src/history_footnote/web_server/](../../src/history_footnote/web_server/) |

## 🔗 关联

- [architecture/产品设计文档.md](../architecture/产品设计文档.md) - 整体设计
- [deploy/DEPLOYMENT_GUIDE.md](../deploy/DEPLOYMENT_GUIDE.md) - 部署相关
- [test/](../test/) - 测试与质量

## 📊 端点统计

| 类别 | 数量 | 路径 |
|---|---|---|
| **基础** | 5 | /api/version, /api/eras, /api/identities, /api/menu, /api/health |
| **状态** | 6 | /api/state, /api/chapter/state, /api/chapter/blueprint, etc. |
| **游戏** | 8 | /api/input, /api/input_stream, /api/character_wiki, etc. |
| **管理** | 6 | /api/admin/* |
| **账户** | 4 | /api/account/* |
| **其他** | 多 | /api/llm/*, /api/monitor/*, etc. |
| **合计** | **30+** | |

依据 v2.10.2 W52 followup
