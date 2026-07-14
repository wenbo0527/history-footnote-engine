"""🆕 v1.6.8 Issue Reporter + Version Info

统一管理版本信息和用户反馈上报。

职责：
- 版本号 / git commit hash / 构建时间
- Issue 接收、格式化、保存
- 自动收集游戏上下文（无需玩家复制粘贴）

存储：
- /tmp/issues/feedback_*.jsonl（开发环境）
- 生产环境可扩展到 Sentry / Slack / Email
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

# 🆕 v1.7.10 版本信息
# 单一权威：所有版本号都从这里读
# 🆕 v2.10.4 同步：与 config.APP_VERSION 保持一致
VERSION = "2.10.6"
VERSION_NAME = "v2.10.6 - 开局剧情带入（4 段模板 + 氛围文案）"  # 显示给用户
BUILD_DATE = "2026-07-13"
IS_BETA = True  # 内测标识


def get_git_commit() -> str:
    """获取当前 git commit hash（前 7 位）"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=Path(__file__).parent.parent.parent,  # 项目根
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_git_branch() -> str:
    """获取当前 git 分支名"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=Path(__file__).parent.parent.parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


# 缓存（启动时计算一次）
GIT_COMMIT = get_git_commit()
GIT_BRANCH = get_git_branch()


def get_version_info() -> dict:
    """返回给前端的版本信息"""
    return {
        "version": VERSION,
        "name": VERSION_NAME,
        "build_date": BUILD_DATE,
        "git_commit": GIT_COMMIT,
        "git_branch": GIT_BRANCH,
        "is_beta": IS_BETA,
        "full_label": f"{VERSION_NAME} ({GIT_COMMIT})" if GIT_COMMIT != "unknown" else VERSION_NAME,
    }


# ============================================================
# Issue Reporter
# ============================================================

# 反馈分类（限制玩家用预设分类，避免乱填）
ISSUE_CATEGORIES = [
    {"key": "bug", "label": "🐛 Bug 报告", "placeholder": "描述你遇到的问题：什么时候发生、看到什么、期望什么"},
    {"key": "narrative", "label": "📖 剧情问题", "placeholder": "上下文断裂？NPC 混淆？描述具体场景"},
    {"key": "ui", "label": "🎨 界面问题", "placeholder": "样式错乱？操作困难？移动端？"},
    {"key": "feature", "label": "✨ 功能建议", "placeholder": "你想要什么功能？为什么需要？"},
    {"key": "data", "label": "📚 词条/数值", "placeholder": "名词解释错误？变量显示不对？"},
    {"key": "other", "label": "💬 其他", "placeholder": "其他想法..."},
]


def validate_feedback(category: str, description: str) -> Optional[str]:
    """校验反馈数据。返回错误消息（如果有）"""
    valid_keys = [c["key"] for c in ISSUE_CATEGORIES]
    if category not in valid_keys:
        return f"未知分类: {category}"
    if not description or not description.strip():
        return "描述不能为空"
    if len(description) > 5000:
        return "描述过长（>5000 字符）"
    if len(description) < 5:
        return "描述过短（<5 字符）"
    return None


def save_feedback(
    session_id: str,
    category: str,
    description: str,
    context: dict | None = None,
) -> dict:
    """保存玩家反馈

    Args:
        session_id: 玩家 session id
        category: 反馈分类（必须是 ISSUE_CATEGORIES 之一）
        description: 反馈描述
        context: 自动收集的游戏上下文（前端传）

    Returns:
        {"id": "fb-uuid", "saved_at": timestamp}
    """
    feedback_id = f"fb-{uuid.uuid4().hex[:8]}"
    saved_at = int(time.time() * 1000)

    feedback = {
        "id": feedback_id,
        "session_id": session_id or "anonymous",
        "category": category,
        "description": description.strip(),
        "context": context or {},
        "client": {
            "user_agent": context.get("user_agent", "unknown") if context else "unknown",
            "screen": context.get("screen", "unknown") if context else "unknown",
        },
        "version": {
            "app": VERSION,
            "git_commit": GIT_COMMIT,
            "git_branch": GIT_BRANCH,
        },
        "saved_at": saved_at,
    }

    # 保存到 /tmp/issues/feedback_YYYYMMDD.jsonl
    save_dir = Path("/tmp/issues")
    try:
        save_dir.mkdir(parents=True, exist_ok=True)
        date_str = time.strftime("%Y%m%d", time.localtime(saved_at / 1000))
        file_path = save_dir / f"feedback_{date_str}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback, ensure_ascii=False) + "\n")
        feedback["saved_to"] = str(file_path)
    except OSError as e:
        feedback["save_error"] = str(e)

    return feedback


def list_recent_feedback(limit: int = 20) -> list[dict]:
    """列出最近的反馈（开发用）"""
    save_dir = Path("/tmp/issues")
    if not save_dir.exists():
        return []
    files = sorted(save_dir.glob("feedback_*.jsonl"), reverse=True)
    recent = []
    for f in files[:3]:  # 最多看 3 个文件
        try:
            with open(f, "r", encoding="utf-8") as fp:
                lines = fp.readlines()
                for line in reversed(lines):
                    if line.strip():
                        recent.append(json.loads(line))
                    if len(recent) >= limit:
                        break
            if len(recent) >= limit:
                break
        except Exception:
            continue
    return recent[:limit]


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print(f"Version Info Test (v{VERSION})")
    print("=" * 50)
    info = get_version_info()
    for k, v in info.items():
        print(f"  {k}: {v}")
    print()
    print("=" * 50)
    print("Issue Reporter Test")
    print("=" * 50)

    # 测试 1：保存
    result = save_feedback(
        session_id="test-123",
        category="bug",
        description='玩家点了"提交"按钮，叙事里出现 SKILL 元数据',
        context={
            "round": 5,
            "user_agent": "Mozilla/5.0...",
            "screen": "375x812",
        },
    )
    print(f"✅ save_feedback: id={result['id']}, saved_to={result.get('saved_to', 'ERROR')}")

    # 测试 2：校验
    assert validate_feedback("bug", "valid description") is None
    assert validate_feedback("invalid", "x") is not None
    assert validate_feedback("bug", "") is not None
    assert validate_feedback("bug", "x" * 6000) is not None
    print(f"✅ validate_feedback: 4 个边界条件")

    # 测试 3：列出
    recent = list_recent_feedback(limit=5)
    print(f"✅ list_recent_feedback: {len(recent)} 条记录")
    for fb in recent[:3]:
        print(f"    - {fb['id']}: [{fb['category']}] {fb['description'][:30]}...")

    print(f"\n✅ 所有测试通过 (version {VERSION} {GIT_COMMIT})")