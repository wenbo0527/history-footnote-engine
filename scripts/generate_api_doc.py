"""🆕 v1.7.29 自动生成 OpenAPI 文档

v1.7.29 适配：
- web_server.py 已拆分为 web_server/ 子包与 router_registry.py
- 本脚本从 router_registry.GET_ROUTES / POST_ROUTES 提取端点
- 每个端点的 docstring 取其 handler 函数的 docstring
- 输出 docs/api/openapi.yaml

保留：
- 自 v1.7.23 起的工作模式：路径列在 OpenAPI，路径对应的描述从 router function
  的 docstring 一行总览生成
"""
import ast
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC_DIR = ROOT / "src"
OUT_DIR = ROOT / "docs" / "api"
OUT_FILE = OUT_DIR / "openapi.yaml"

# 项目内 import 准备
sys.path.insert(0, str(SRC_DIR))


def extract_endpoints() -> list[dict]:
    """从 router_registry 提取所有 API 端点信息

    Returns:
        [{path, method, doc, description, responses}, ...]

    priority:
    1. handler.__doc__ 第一行
    2. 否则按 path 推断（heuristic map）
    """
    from history_footnote.web_server.router_registry import GET_ROUTES, POST_ROUTES

    # 兜底：路径友好的中文说明
    FALLBACK_SUMMARY = {
        "/api/start": "启动新游戏会话",
        "/api/input": "玩家输入一行动（DM 调度）",
        "/api/input_stream": "玩家输入流式（SSE）",
        "/api/state": "获取当前 session 完整 state",
        "/api/load": "从存档加载 session 到内存",
        "/api/recap": "获取近期剧情回顾",
        "/api/archives": "列出存档",
        "/api/archive/delete": "删除一个存档",
        "/api/archives/clear": "清空某 era 的所有存档（需 confirm）",
        "/api/eras": "列出所有可用时代包",
        "/api/identities": "列出某时代的可玩身份",
        "/api/character_wiki": "获取本存档的角色 Wiki",
        "/api/character_wiki_update": "手动编辑某条 wiki entry",
        "/api/lore": "在 lore 知识库查一条历史知识点",
        "/api/glossary": "查询明朝名词解释",
        "/api/extract_terms": "从文本提取名词并标记已读",
        "/api/mark_term_seen": "标记一个名词为已读",
        "/api/sanitize": "清洗 narrative 文本",
        "/api/sanitize_patterns": "取 sanitizer 的正则模式",
        "/api/dilemma": "从 narrative 提取当前困境引导词",
        "/api/merge_voice_options": "合并结构化选项与内嵌选项",
        "/api/render_narrative": "渲染 narrative（Markdown → HTML 片段）",
        "/api/task/complete": "标记一个任务完成",
        "/api/task/add": "添加一个手动任务",
        "/api/version": "查询服务端版本信息",
        "/api/feedback": "提交一条用户反馈",
        "/api/feedback_categories": "列出反馈分类",
        "/api/generate_character": "LLM 生成自定义角色人设",
        "/api/generate_world_dwell": "LLM 生成世界画卷",
        "/api/llm/stats": "LLM token 用量统计",
        "/api/llm/reset_stats": "重置 LLM 统计（开发）",
        "/api/monitor/health": "详细健康检查",
        "/api/monitor/stats": "监控端点调用统计",
        "/metrics": "性能指标（全局 metrics snapshot）",
        "/health": "健康检查（基础）",
    }

    def _summary_for(path: str, handler) -> str:
        doc = (handler.__doc__ or "").strip().split("\n", 1)[0]
        if doc:
            return doc
        return FALLBACK_SUMMARY.get(path, path)

    endpoints = []
    for path, handler in GET_ROUTES.items():
        endpoints.append({
            "path": path,
            "method": "get",
            "doc": _summary_for(path, handler),
            "description": "",
            "responses": _responses_for(handler),
        })
    for path, handler in POST_ROUTES.items():
        endpoints.append({
            "path": path,
            "method": "post",
            "doc": _summary_for(path, handler),
            "description": "",
            "responses": _responses_for(handler),
        })
    # 按 path 排序
    endpoints.sort(key=lambda e: (e["path"], e["method"]))
    return endpoints


def _responses_for(handler) -> list:
    """从 docstring 推断常见响应码。默认 200/400。"""
    doc = (handler.__doc__ or "").lower()
    codes = {200}
    if "404" in doc or "not found" in doc:
        codes.add(404)
    if "429" in doc or "rate limit" in doc:
        codes.add(429)
    if "500" in doc:
        codes.add(500)
    return [{"status": c} for c in sorted(codes)]


def generate_yaml(endpoints: list[dict]) -> str:
    """生成 OpenAPI 3.0 YAML"""
    lines = [
        "openapi: 3.0.0",
        "info:",
        "  title: 历史脚注引擎 API",
        "  description: |",
        "    明代万历年间沉浸式剧情游戏 HTTP API",
        "    v1.7.29 - 自动从 router_registry 生成",
        "  version: 1.7.29",
        "  contact:",
        "    name: wenbo0527",
        "    url: https://github.com/wenbo0527/history-footnote-engine",
        "",
        "servers:",
        "  - url: http://localhost:8765",
        "    description: 本地开发服务器",
        "",
        "tags:",
        "  - name: game",
        "    description: 游戏核心 API（开局/输入/状态）",
        "  - name: stream",
        "    description: SSE 流式 API",
        "  - name: archive",
        "    description: 存档/读档/列表",
        "  - name: meta",
        "    description: 元数据/版本/反馈",
        "  - name: tools",
        "    description: 工具/校验/监控",
        "",
        "paths:",
    ]
    # 按 path 聚合
    by_path: dict = {}
    for ep in endpoints:
        by_path.setdefault(ep["path"], []).append(ep)
    for path in sorted(by_path.keys()):
        lines.append(f"  {path}:")
        for ep in by_path[path]:
            lines.append(f"    {ep['method']}:")
            lines.append(f"      summary: \"{ep['doc']}\"")
            if ep['method'] == "post":
                lines.append("      requestBody:")
                lines.append("        content:")
                lines.append("          application/json:")
                lines.append("            schema:")
                lines.append("              type: object")
            lines.append("      responses:")
            for r in ep["responses"]:
                status = r["status"]
                lines.append(f"        '{status}':")
                lines.append("          description: OK")
                if status == 200:
                    lines.append("          content:")
                    lines.append("            application/json:")
                    lines.append("              schema:")
                    lines.append("                type: object")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    if not OUT_DIR.exists():
        OUT_DIR.mkdir(parents=True)
    endpoints = extract_endpoints()
    yaml = generate_yaml(endpoints)
    OUT_FILE.write_text(yaml, encoding="utf-8")
    print(f"✅ 写入 {OUT_FILE.relative_to(ROOT)}")
    print(f"   共 {len(endpoints)} 端点：GET={sum(1 for e in endpoints if e['method']=='get')} / "
          f"POST={sum(1 for e in endpoints if e['method']=='post')}")


if __name__ == "__main__":
    main()
