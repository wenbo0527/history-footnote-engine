# 🆕 v2.10.9 scripts/ 目录结构

## 顶层（生产工具）

| 文件 | 用途 | 触发时机 |
|---|---|---|
| `dev-server.sh` | 一键启停前后端（8 命令：start/stop/restart/status/logs/open/build/dev） | 本地开发 |
| `deploy-pre-start.sh` | 部署前预检（环境变量、端口、依赖） | CI/CD |
| `generate_api_doc.py` | 从代码生成 OpenAPI 文档 | CI/CD |
| `generate_chapter_blueprints.py` | 生成章节蓝图 JSON | era 包初始化 |
| `test_*.py` (100 个) | 单元 / 集成测试 | CI (for-loop 跑全部) |

## scripts/_archive/（历史脚本，不维护）

> **注意**：这些脚本是早期里程碑期的临时调试 / 烟测 / 一次性脚本。
> 已通过 `git mv` 归档（**git 历史保留**），不再维护。
> **如果想恢复**：直接看 git log 或从 archive 找。

### _archive/debug/ (13 文件)
`debug_w35*.py` / `debug_v32_7.py` / `debug_css.py` 等 — 早期迭代期调试用。

### _archive/smoke/ (53 文件)
`smoke_v195_*.py` / `smoke_v280_*.py` / `verify_*.py` / `review_*.py` / `cleanup_*.py` 等 — 一次性烟测 / 验证。

### _archive/oneoff/ (17 文件)
`add_action_points_max.py` / `e2e_*.js` / `ui_*.js` 等 — era.json 迁移、Playwright 手测、UI 调试等一次性脚本。

## 🆕 v2.10.9 拆分原则

1. **保留**：被 CI / 文档 / 生产工具引用的脚本（如 `test_*.py`）
2. **归档**：版本号 / 临时调试 / 一次性脚本 → `_archive/`
3. **新增**：放在顶层并加 README.md 说明
4. **删除**：禁止（git history 即可恢复）

## CI 影响

- ✅ `.github/workflows/ci.yml` 的 `for t in scripts/test_*.py` 不受影响（test_*.py 都保留在顶层）
- ✅ `scripts/test_*.py` 仍可在本地 `python scripts/test_xxx.py` 直接跑
- ⚠️ 归档脚本**不在 CI 中**（`_archive/` 子目录不会被 `*.py` glob 匹配）

## 本地使用

```bash
# 一键开发
bash scripts/dev-server.sh start

# 跑测试
for t in scripts/test_*.py; do
    python "$t"
done

# 归档脚本（仅供回溯，不推荐使用）
python scripts/_archive/smoke/test_v195_voice.py  # 不一定能跑（依赖早期 API）
```