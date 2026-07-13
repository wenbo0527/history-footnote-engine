# docs/operations/

> **目的**：存放项目运营 / 一次性脚本的归档、报告、运维笔记

## 文件清单

| 文件 | 用途 | 状态 |
|---|---|---|
| （暂无） | — | — |

## v2.10.3 + v2.10.4 周期产生的临时脚本

| 脚本 | 用途 | 保留决策 |
|---|---|---|
| `refactor_safe_route.py` | 自动把 `except Exception` 样板改为 `@safe_route` 装饰器 | **不保留**：实验失败（misc.py 被改坏），已被 `git checkout` 回滚 |
| verify_*.py 一次性脚本 | 验证 dm_skills 拆分行为 | **不保留**：13/13 验证结果在总结文档中 |
| /tmp/w52_*.txt | 早期 W52 优化 commit message 模板 | **不保留**：已被实际 commit 取代 |

## 归档原则

- **失败实验**：不保留（避免误导）
- **一次性验证脚本**：不保留（结果在文档中）
- **未来会用到的脚本**：保留（如 `clean_pyc.sh`、`audit_*.py`）
- **运维报告**：保留（如每周运行时 metrics）

## 后续可添加

- `clean_pyc.sh` — 清理 `__pycache__` + `.pyc` 文件（一键操作）
- `audit_dependencies.py` — 扫描未使用的 import / 死代码
- `release_notes_template.md` — 标准 release notes 模板
- `tag_release.sh` — 自动打 tag + 推送 + 生成 release notes