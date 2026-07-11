# 🆕 v2.8.0 GitHub Release 创建说明

## 现状

| 步骤 | 状态 |
|---|---|
| 代码 commit | ✅ 18 个 commits 全部 push origin/main |
| Git tag | ✅ `v2.8.0` annotated tag 已 push origin |
| Release notes | ✅ `RELEASE_NOTES_v2.8.0.md` 200+ 行准备就绪 |
| **GitHub Release** | ❌ **未自动创建**（需 GitHub Token） |

## 为什么 gh CLI 没工作

```
$ gh release list
To get started with GitHub CLI, please run:  gh auth login
Alternatively, populate the GH_TOKEN environment variable with a GitHub API authentication token.
```

**gh CLI 未登录**（无 GH_TOKEN 环境变量），无法直接发布。

## 3 种创建 release 的方法

### 方法 1：浏览器（最简单，推荐）

1. 访问：https://github.com/wenbo0527/history-footnote-engine/releases
2. 点击 `Draft a new release` 按钮
3. 选择 tag: `v2.8.0`
4. Release title: `v2.8.0 章节制叙事体系`
5. 复制粘贴 `RELEASE_NOTES_v2.8.0.md` 的内容到 description
6. 点击 `Publish release`

### 方法 2：gh auth login（需要交互）

```bash
gh auth login
# 选 GitHub.com → SSH → 拷贝公钥 → 完成
gh release create v2.8.0 \
  --title "v2.8.0 章节制叙事体系" \
  --notes-file RELEASE_NOTES_v2.8.0.md
```

### 方法 3：GitHub API（需要 PAT token）

```bash
export GH_TOKEN=ghp_xxxxxxxxxxxx
gh release create v2.8.0 \
  --repo wenbo0527/history-footnote-engine \
  --title "v2.8.0 章节制叙事体系" \
  --notes-file RELEASE_NOTES_v2.8.0.md
```

## tag 信息

```
$ git show v2.8.0 --stat --no-patch
tag v2.8.0
Tagger: wenbo0527
Date:   2026-07-11

v2.8.0 章节制叙事体系
- 6 段（章节骨架+LLM自由生成+路径三态+Build分化+板块格局+DM Agent Tool）
- 后续小迭代 W20-W30（UI接入+vitest+e2e+场景图+板块UI+10章端到端+Tool注入）
- 240 后端 + 30 前端 + 1 smoke = 271 测试全过
- 10/10 章真 LLM 端到端 169.8 秒跑通
```

## Release 简介（标题 + 内容前 200 字）

**Title**:
```
v2.8.0 章节制叙事体系
```

**Body（粘贴 RELEASE_NOTES_v2.8.0.md 完整内容）**：

```markdown
# 🎉 Release Notes: v2.8.0 「章节制叙事体系」

> **日期**: 2026-07-11
> **范围**: 章节制叙事体系（v2.8.0 全栈完整交付）
> **测试**: 260 个测试 0 回归（240 后端 + 20 前端）
> **Git**: 14 个 commit 推送到 origin/main
> **真 LLM 端到端**: 30 秒跑 2 章（4 LLM 调用 minimax-anthropic）

## 概述
v2.8.0 是"章节制叙事体系"——把游戏从"事件流"升级为"章节化叙事"...

[完整 200+ 行在 RELEASE_NOTES_v2.8.0.md]
```

## 链接

- **Repo**: https://github.com/wenbo0527/history-footnote-engine
- **Tag**: https://github.com/wenbo0527/history-footnote-engine/releases/tag/v2.8.0
- **Source**: https://github.com/wenbo0527/history-footnote-engine/tree/v2.8.0
- **CHANGELOG**: `CHANGELOG.md`（同仓内）
- **Release notes 源文件**: `RELEASE_NOTES_v2.8.0.md`
