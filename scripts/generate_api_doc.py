"""🆕 v1.7.23 自动生成 OpenAPI 文档

扫描 web_server.py 的端点 + 端点注释 + Response 字段
输出 docs/api/openapi.yaml
"""
import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src" / "history_footnote" / "web_server.py"
OUT_DIR = ROOT / "docs" / "api"
OUT_FILE = OUT_DIR / "openapi.yaml"


def extract_endpoints(source: str) -> list[dict]:
    """从 web_server.py AST 提取所有 API 端点信息"""
    tree = ast.parse(source)

    endpoints = []
    # 找 do_POST / do_GET / do_DELETE
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("do_POST", "do_GET", "do_DELETE", "do_PUT"):
            method = node.name.split("_")[1]
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    # 找 path == "/api/xxx" 比较
                    if isinstance(sub.test, ast.Compare):
                        for comp in sub.test.comparators:
                            if isinstance(comp, ast.Constant) and isinstance(comp.value, str) and comp.value.startswith("/api/"):
                                path = comp.value
                                # 提取该 if 块的注释
                                try:
                                    doc = ast.get_docstring(sub) or ""
                                except TypeError:
                                    doc = ""
                                # 提取 200 / 400 / 404 响应信息
                                responses = extract_responses(sub)
                                # 提取 description
                                description = extract_block_comment(sub)
                                endpoints.append({
                                    "path": path,
                                    "method": method,
                                    "doc": doc,
                                    "description": description,
                                    "responses": responses,
                                })
    return endpoints


def extract_responses(if_node) -> list[dict]:
    """提取 self._json(status, {...}) 调用的状态码"""
    responses = []
    seen = set()
    for sub in ast.walk(if_node):
        if isinstance(sub, ast.Call):
            # self._json(200, {...}) 或 self._json(404, {...})
            if (isinstance(sub.func, ast.Attribute) and
                isinstance(sub.func.value, ast.Name) and
                sub.func.value.id == "self" and
                sub.func.attr == "_json"):
                if sub.args and isinstance(sub.args[0], ast.Constant):
                    status = sub.args[0].value
                    if status not in seen:
                        seen.add(status)
                        # 尝试解析 body
                        body_desc = ""
                        if len(sub.args) > 1:
                            body_desc = ast.unparse(sub.args[1])[:100]
                        responses.append({
                            "status": status,
                            "body_hint": body_desc,
                        })
    return responses


def extract_block_comment(if_node) -> str:
    """提取 if 块上方的注释作为 description"""
    # 通过源码字符串提取（ast 不直接支持 comments）
    return ""  # 简化：跳过


def generate_yaml(endpoints: list[dict]) -> str:
    """生成 OpenAPI 3.0 YAML"""
    lines = [
        "openapi: 3.0.0",
        "info:",
        "  title: 历史脚注引擎 API",
        "  description: |",
        "    明代万历年间沉浸式剧情游戏 HTTP API",
        "    v1.7.23 - 短期改进版",
        "  version: 1.7.23",
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
        "    description: 工具/统计/反馈",
        "",
        "paths:",
    ]

    # 按 path 分组
    paths = {}
    for ep in endpoints:
        path = ep["path"]
        if path not in paths:
            paths[path] = []
        paths[path].append(ep)

    # 路径 → tag 分类
    def get_tag(path: str) -> str:
        if path in ("/api/start", "/api/input", "/api/input_stream", "/api/state", "/api/recap"):
            return "game"
        if "stream" in path:
            return "stream"
        if "archive" in path or "save" in path:
            return "archive"
        return "meta"

    for path, eps in sorted(paths.items()):
        lines.append(f"  {path}:")
        for ep in eps:
            method = ep["method"].lower()
            lines.append(f"    {method}:")
            lines.append(f"      tags: [{get_tag(path)}]")
            # summary: 用 path 末段
            summary = path.split("/")[-1].replace("_", " ").title() or path
            lines.append(f"      summary: {summary}")
            if ep["doc"]:
                lines.append(f"      description: |")
                for doc_line in ep["doc"].split("\n")[:5]:
                    lines.append(f"        {doc_line}")
            # requestBody
            if method in ("post", "put", "patch"):
                lines.append("      requestBody:")
                lines.append("        required: true")
                lines.append("        content:")
                lines.append("          application/json:")
                lines.append("            schema:")
                lines.append("              type: object")
            # responses
            lines.append("      responses:")
            for resp in ep["responses"]:
                status = resp["status"]
                status_text = {
                    200: "成功", 201: "已创建", 400: "请求错误",
                    401: "未授权", 403: "禁止", 404: "未找到",
                    429: "限流", 500: "服务器错误",
                }.get(status, "响应")
                lines.append(f"        '{status}':")
                lines.append(f"          description: {status_text}")
                if "application/json" in str(resp.get("body_hint", "")) or status == 200:
                    lines.append("          content:")
                    lines.append("            application/json:")
                    lines.append("              schema:")
                    lines.append("                type: object")
            # 默认 500 响应
            lines.append("        '500':")
            lines.append("          description: 服务器内部错误")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    if not SRC.exists():
        print(f"错误：{SRC} 不存在", file=sys.stderr)
        sys.exit(1)

    print(f"扫描 {SRC} ...")
    source = SRC.read_text(encoding="utf-8")
    endpoints = extract_endpoints(source)
    print(f"找到 {len(endpoints)} 个端点")

    # 按 path 去重
    seen_paths = set()
    unique = []
    for ep in endpoints:
        key = (ep["path"], ep["method"])
        if key not in seen_paths:
            seen_paths.add(key)
            unique.append(ep)
    print(f"去重后 {len(unique)} 个端点")

    # 生成 YAML
    yaml_content = generate_yaml(unique)

    # 写文件
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(yaml_content, encoding="utf-8")
    print(f"✅ 已生成 {OUT_FILE} ({len(yaml_content)} 字符)")

    # 列出所有端点
    print("\n发现的端点：")
    for ep in sorted(unique, key=lambda x: (x["path"], x["method"])):
        print(f"  {ep['method']:6s} {ep['path']}")


if __name__ == "__main__":
    main()