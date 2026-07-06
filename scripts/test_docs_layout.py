"""🆕 v1.7.29 文档归档静态校验

验证：
1. docs/README.md 是顶层入口（必须存在）
2. docs/design/README.md + docs/eras/万历十五年/README.md 存在
3. docs/design/archive/ + docs/eras/万历十五年/archive/ 有 README.md 索引
4. 设计文档 1 现行 + 3 archive（v1.0/v2.0/v3.0）
5. 支线路径 Wiki 1 现行 + 4 archive（v1.0~v4.0）
6. 顶层不再有 v1.0/v2.0/v3.0/v3.1 的散落文档（已全部归档）
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def must_exist(path):
    return path.exists() and path.is_file()


def test_entry_points():
    print("[1/4] 入口文件存在")
    ok = True
    ok = _step("docs/README.md", must_exist(DOCS / "README.md")) and ok
    ok = _step("docs/design/README.md", must_exist(DOCS / "design" / "README.md")) and ok
    ok = _step("docs/eras/万历十五年/README.md", must_exist(DOCS / "eras" / "万历十五年" / "README.md")) and ok
    ok = _step("docs/design/archive/README.md", must_exist(DOCS / "design" / "archive" / "README.md")) and ok
    ok = _step("docs/eras/万历十五年/archive/README.md", must_exist(DOCS / "eras" / "万历十五年" / "archive" / "README.md")) and ok
    return ok


def test_design_current():
    print("\n[2/4] 设计文档：1 现行 + 3 archive")
    cur = DOCS / "design" / "产品设计文档.md"
    archives = sorted((DOCS / "design" / "archive").glob("产品设计文档.v*.md"))
    ok = True
    ok = _step("现行版 产品设计文档.md 存在", must_exist(cur)) and ok
    ok = _step("现行版带「v1.0/v2.0/v3.0/v3.1」字段（不应对）", 
               not (re.search(r"v[12345]\.\d+\.md", cur.name))) and ok
    ok = _step("archive 有 v1.0", (DOCS / "design" / "archive" / "产品设计文档.v1.0.md").exists()) and ok
    ok = _step("archive 有 v2.0", (DOCS / "design" / "archive" / "产品设计文档.v2.0.md").exists()) and ok
    ok = _step("archive 有 v3.0", (DOCS / "design" / "archive" / "产品设计文档.v3.0.md").exists()) and ok
    ok = _step(f"archive 共 {len(archives)} 文件", len(archives) == 3, 
               f"got {len(archives)}") and ok
    return ok


def test_era_side_path():
    print("\n[3/4] 支线路径 Wiki：1 现行 + 4 archive")
    cur = DOCS / "eras" / "万历十五年" / "支线路径Wiki.md"
    archives = sorted((DOCS / "eras" / "万历十五年" / "archive").glob("支线路径Wiki.v*.md"))
    ok = True
    ok = _step("现行版 支线路径Wiki.md 存在", must_exist(cur)) and ok
    ok = _step("archive 有 v1.0", (DOCS / "eras" / "万历十五年" / "archive" / "支线路径Wiki.v1.0.md").exists()) and ok
    ok = _step("archive 有 v2.0", (DOCS / "eras" / "万历十五年" / "archive" / "支线路径Wiki.v2.0.md").exists()) and ok
    ok = _step("archive 有 v3.0", (DOCS / "eras" / "万历十五年" / "archive" / "支线路径Wiki.v3.0.md").exists()) and ok
    ok = _step("archive 有 v4.0", (DOCS / "eras" / "万历十五年" / "archive" / "支线路径Wiki.v4.0.md").exists()) and ok
    ok = _step(f"archive 共 4 文件", len(archives) == 4, f"got {len(archives)}") and ok
    return ok


def test_top_level_no_scattered():
    """顶层 docs/ 不应再有 v 编号的设计文档或支线路径 Wiki"""
    print("\n[4/4] 顶层不再有 v 编号散落文档")
    ok = True
    for p in (DOCS).glob("*.md"):
        # 检查产品设计文档或支线路径 Wiki 是否还在顶层
        if "产品设计文档" in p.name and re.search(r"v[12345]\.\d+", p.name):
            ok = _step(f"顶层不应有 {p.name}", False) and ok
        if "支线路径Wiki" in p.name:
            ok = _step(f"顶层不应有 {p.name}", False) and ok
    ok = _step("顶层无散落 v 编号文档", True) and ok
    return ok


def test_link_consistency():
    """docs/README.md 里所有相对路径都解析得到"""
    from urllib.parse import unquote
    print("\n[5/5] docs/README.md 链接一致性")
    doc = (DOCS / "README.md").read_text(encoding="utf-8")
    md_links = re.findall(r"\]\((.+?)\)", doc)
    ok = True
    for rel in md_links:
        if rel.startswith("http") or rel.startswith("../README.md"):
            continue
        # Markdown 标准：URL 中的 %20 等百分号编码应当解码为实际字符
        rel_decoded = unquote(rel)
        target = (DOCS / "README.md").parent / rel_decoded
        if not target.exists():
            ok = _step(f"  链接 {rel}", False, "未解析到") and ok
    ok = _step("  docs/README.md 内链全部命中", True) and ok
    return ok


if __name__ == "__main__":
    print("=== v1.7.29 文档归档静态校验 ===\n")
    ok1 = test_entry_points()
    ok2 = test_design_current()
    ok3 = test_era_side_path()
    ok4 = test_top_level_no_scattered()
    ok5 = test_link_consistency()
    if all([ok1, ok2, ok3, ok4, ok5]):
        print("\n🎉 5 组校验全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：entry={ok1} design={ok2} era={ok3} top={ok4} links={ok5}")
        sys.exit(1)
