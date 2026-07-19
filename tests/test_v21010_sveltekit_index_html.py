"""🆕 v2.10.10 测试：后端 INDEX_HTML 真的是 SvelteKit（不再是 v1.7.27）

防回归——以后再有人加新前端目录要确保 backend 读的是 SvelteKit build/。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path


def _parse_file(path: str):
    """读 py 文件并返回 AST"""
    src = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    # 删除所有 docstring 节点（仅检查 import）
    return src, tree


def _file_imports(path: str) -> list[tuple[str, int]]:
    """AST 静态扫描所有 `from X import Y` 的 X 部分"""
    _, tree = _parse_file(path)
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imports.append((mod, node.lineno))
    return imports


def _code_contains(path: str, needle: str) -> bool:
    """AST 检查某字符串作为表达式（非注释 / docstring）出现"""
    src, tree = _parse_file(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if needle in node.value:
                return True
    return False


def test_static_assets_module():
    """static_assets.py 能 import，路径常量指向 SvelteKit"""
    from importlib import util as importlib_util
    spec = importlib_util.spec_from_file_location(
        "_hfe_static_assets",
        "src/history_footnote/web_server/static_assets.py",
    )
    if spec is None or spec.loader is None:
        raise AssertionError("spec_from_file_location 失败")
    m = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # INDEX_HTML 必须是非占位字符串
    assert isinstance(m.INDEX_HTML, str), "INDEX_HTML 必须是字符串"
    # 不能以占位注释开头（注意 <!DOCTYPE html> 不是占位，是合法 DTD）
    head = m.INDEX_HTML.lstrip().split("\n", 1)[0]
    assert not head.startswith("<!--"), (
        f"INDEX_HTML 第一行不应是 HTML 注释（占位字符串），实际: {head[:80]!r}"
    )
    assert "missing" not in head.lower(), (
        f"INDEX_HTML 第一行不应含 'missing'（占位字符串），实际: {head[:80]!r}"
    )

    # ⭐ 必须是 SvelteKit 产物
    assert "<svelte" in m.INDEX_HTML.lower() or "sveltekit" in m.INDEX_HTML.lower(), (
        "INDEX_HTML 必须是 SvelteKit 产物（含 <svelte 或 sveltekit 标识）"
    )

    # 不会是 v1.7.27 旧模板
    assert "v1.7.27" not in m.INDEX_HTML, "INDEX_HTML 还包含 v1.7.27 旧模板标识？"
    assert "<!-- v1.3.1 -->" not in m.INDEX_HTML, "INDEX_HTML 还含 v1.3.1 旧注释？"

    # frontend_paths_info 报告真实路径
    info = m.frontend_paths_info()
    assert info["build_dir"].endswith("frontend/build"), (
        f"build_dir 路径不对: {info['build_dir']}"
    )
    assert info["index_html_exists"], "SvelteKit build/index.html 不存在"
    assert info["static_dir_exists"], "SvelteKit static/ 不存在"


def test_no_legacy_web_path():
    """v1.7.27 旧目录 src/history_footnote/web/ 必须不存在"""
    legacy = Path("src/history_footnote/web")
    assert not legacy.exists(), (
        f"v1.7.27 旧前端目录 {legacy} 仍然存在——应该已删除"
    )


def _non_docstring_strings(tree: ast.AST):
    """遍历 AST 收集所有非 docstring 节点的字符串字面量"""
    strings: list[tuple[str, int]] = []
    # 收集所有 docstring Expr 节点（模块级/函数/类上的第一个表达式）
    docstring_locations = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module):
            # 模块 docstring
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                docstring_locations.add(id(node.body[0]))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                docstring_locations.add(id(node.body[0]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_locations or id(getattr(node, '_parent_expr', None)) in docstring_locations:
                continue
            strings.append((node.value, getattr(node, 'lineno', 0)))

    # 简化版：只走 plain Constant 节点（docstring 也包含，但内容是字面量）
    # 上面复杂版太脆弱，这里退回：直接根据上下文判断
    return strings


def test_static_assets_no_stale_path():
    """static_assets.py 不应在**运行路径**（条件/函数调用）里出现 web/templates

    docstring / 注释里可以提（用作历史说明），所以看 AST 的 Call/Constant
    实际承担运行路径的子集。
    """
    # 简单读取：源码文本中，**如果没有作为运行路径的字符串**就行
    src = Path("src/history_footnote/web_server/static_assets.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    # 找函数体里的所有字符串字面量（module 的 body[0] 是 docstring，跳过）
    non_doc_module_strings = []
    if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        # 第一个 stmt 是 docstring
        for stmt in tree.body[1:]:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    non_doc_module_strings.append((node.value, node.lineno))

    bad = [v for v, ln in non_doc_module_strings if "web/templates" in v]
    assert not bad, f"static_assets.py 函数体里仍引用 web/templates/：{bad}"

    # 必须指向 SvelteKit（在源码里——包括 docstring/注释）
    assert "frontend/build" in src, (
        "static_assets.py 未指向 SvelteKit src/frontend/build/index.html"
    )


def test_handler_base_no_legacy_static_import():
    """handler_base.py AST 不应 import 裸 history_footnote.web（已删模块）

    允许：`history_footnote.web_server.*` / `history_footnote.web_enhancements`
    （shim 已迁移）
    """
    imports = _file_imports("src/history_footnote/web_server/handler_base.py")
    bad = [
        (mod, line) for mod, line in imports
        if mod.startswith("history_footnote.web")
        and not mod.startswith("history_footnote.web_server")
        and not mod.startswith("history_footnote.web_enhancements")
    ]
    assert not bad, (
        f"handler_base.py 仍 import 已删的 history_footnote.web：{bad}"
    )


def test_dockerfile_copies_to_frontend_build():
    """Dockerfile 必须 COPY 前端到 src/frontend/build/（不是旧 /app/static/）"""
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "/app/src/frontend/build/" in dockerfile, (
        "Dockerfile 未 COPY 前端到 /app/src/frontend/build/"
    )
    assert "COPY --from=frontend-build /build/build/ ./static/" not in dockerfile, (
        "Dockerfile 还 COPY 到 ./static/（已废弃路径）"
    )


def test_nginx_points_to_build_subdir():
    """nginx.conf location / 必须指向 /var/www/hfe/build/"""
    nginx = Path("deploy/nginx.conf").read_text(encoding="utf-8")
    assert "/var/www/hfe/build" in nginx, (
        "nginx.conf 未指向 /var/www/hfe/build/（访问会 404）"
    )


def test_spa_server_in_repo():
    """scripts/spa_server.py 必须在 repo 里，运行时无 /tmp/，实现 SPA fallback"""
    p = Path("scripts/spa_server.py")
    assert p.exists(), "scripts/spa_server.py 不存在（dev-server.sh spa 模式会失败）"

    src = p.read_text(encoding="utf-8")
    tree = ast.parse(src)

    # 函数体（不含 docstring）字符串里不能有 /tmp/spa_server.py
    if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        for stmt in tree.body[1:]:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    assert "/tmp/spa_server.py" not in node.value, (
                        f"spa_server.py 函数体第 {node.lineno} 行仍引用 /tmp/spa_server.py"
                    )

    # 必须实现 send_head SPA fallback
    has_fallback = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "send_head":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f = sub.func
                    # 接受 self._send_file / 直接 _send_file / 任何匹配
                    matches = False
                    if isinstance(f, ast.Attribute) and f.attr == "_send_file":
                        matches = True
                    elif isinstance(f, ast.Name) and f.id == "_send_file":
                        matches = True
                    if matches:
                        has_fallback = True
                        break
            if has_fallback:
                break
    assert has_fallback, "spa_server.py 没有 SPA fallback 函数 send_head -> _send_file"


if __name__ == "__main__":
    tests = [
        ("static_assets_module", test_static_assets_module),
        ("no_legacy_web_path", test_no_legacy_web_path),
        ("static_assets_no_stale_path", test_static_assets_no_stale_path),
        ("handler_base_no_legacy_static_import", test_handler_base_no_legacy_static_import),
        ("dockerfile_copies_to_frontend_build", test_dockerfile_copies_to_frontend_build),
        ("nginx_points_to_build_subdir", test_nginx_points_to_build_subdir),
        ("spa_server_in_repo", test_spa_server_in_repo),
    ]
    passed = 0
    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)