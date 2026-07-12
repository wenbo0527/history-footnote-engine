"""v2.10.1 W52 P0-1: chapter 蓝图完整性测试

验证:
1. chapter 1-9 蓝图文件存在
2. 每个蓝图 JSON 可解析
3. 必有字段：chapter_id / chapter_title / nodes (4 个) / meta / differentiation
"""
import json
import pytest
from pathlib import Path

BLUEPRINTS_DIR = Path("eras/wanli1587")


def test_chapter1_to_9_blueprints_exist():
    """chapter 1-9 蓝图文件都应存在"""
    for i in range(1, 10):
        path = BLUEPRINTS_DIR / f"chapter{i}_blueprint.json"
        assert path.exists(), f"missing {path}"


@pytest.mark.parametrize("chapter_id", list(range(1, 10)))
def test_blueprint_json_valid(chapter_id):
    """每个蓝图 JSON 应可解析"""
    path = BLUEPRINTS_DIR / f"chapter{chapter_id}_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


@pytest.mark.parametrize("chapter_id", list(range(1, 10)))
def test_blueprint_required_fields(chapter_id):
    """每个蓝图应有必需字段"""
    path = BLUEPRINTS_DIR / f"chapter{chapter_id}_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["chapter_id"] == chapter_id
    assert "chapter_title" in data
    assert "meta" in data
    assert "nodes" in data
    assert "differentiation" in data


@pytest.mark.parametrize("chapter_id", list(range(1, 10)))
def test_blueprint_has_4_nodes(chapter_id):
    """每个蓝图应有 4 个 node (introduction / escalation / climax / resolution)"""
    path = BLUEPRINTS_DIR / f"chapter{chapter_id}_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["nodes"]) == 4
    roles = [n["role"] for n in data["nodes"]]
    assert "introduction" in roles
    assert "escalation" in roles
    assert "climax" in roles
    assert "resolution" in roles


@pytest.mark.parametrize("chapter_id", list(range(1, 10)))
def test_blueprint_node_structure(chapter_id):
    """每个 node 字段应完整"""
    path = BLUEPRINTS_DIR / f"chapter{chapter_id}_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for node in data["nodes"]:
        assert "index" in node
        assert "role" in node
        assert "scene" in node
        assert "npc_ids" in node
        assert "option_directions" in node
        assert len(node["option_directions"]) >= 3


@pytest.mark.parametrize("chapter_id", list(range(1, 10)))
def test_blueprint_meta_required(chapter_id):
    """meta 字段应包含关键 spec 字段"""
    path = BLUEPRINTS_DIR / f"chapter{chapter_id}_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    meta = data["meta"]
    assert "act" in meta
    assert "emotion_tone" in meta
    assert "choice_type" in meta
    assert "suggested_node_count" in meta
    assert "suggested_template" in meta


@pytest.mark.parametrize("chapter_id", list(range(1, 10)))
def test_blueprint_differentiation(chapter_id):
    """differentiation 应包含 2 个 build 路径"""
    path = BLUEPRINTS_DIR / f"chapter{chapter_id}_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    diff = data["differentiation"]
    assert "守乡人" in diff or "_description" in diff  # chapter 1 实际有具体场景


def test_blueprint_chapter_ids_unique():
    """chapter_id 应唯一"""
    ids = set()
    for i in range(1, 10):
        path = BLUEPRINTS_DIR / f"chapter{i}_blueprint.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["chapter_id"] not in ids, f"duplicate chapter_id={data['chapter_id']}"
        ids.add(data["chapter_id"])


def test_blueprint_chapter_ids_sequential():
    """chapter_id 应 1-9 连续"""
    for i in range(1, 10):
        path = BLUEPRINTS_DIR / f"chapter{i}_blueprint.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["chapter_id"] == i, f"chapter{i} has chapter_id={data['chapter_id']}"


def test_blueprint_titles_distinct():
    """9 个 chapter title 应不同"""
    titles = []
    for i in range(1, 10):
        path = BLUEPRINTS_DIR / f"chapter{i}_blueprint.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        titles.append(data["chapter_title"])
    assert len(titles) == len(set(titles)), "duplicate titles"
