"""🆕 v1.7.30 4 类信息结构化静态测试

覆盖：
1. GameState 5 个新字段（cash/rice/debt/monthly_burn/financial_log/family_members/genealogy/city_properties/inventory）
2. apply_financial_change() 校验（100 / -50 边界）
3. add_family_member() 校验（id 唯一 + 必填字段）
4. update_family_member() / get_family_member() / get_family_by_location()
5. add_genealogy_entry() / get_genealogy_by_relation() / get_known_ancestors()
6. add_property() / get_properties_in_city() / get_total_property_value()
7. add_inventory_item() / transfer_inventory() / get_inventory_summary()
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
GS = ROOT / "src/history_footnote/game_state.py"


def _step(label, ok, detail=""):
    icon = "  ✅" if ok else "  ❌"
    print(f"{icon} {label}{(' — ' + detail) if detail else ''}")
    return ok


def test_fields_exist():
    print("[1/7] GameState 9 个新字段")
    src = GS.read_text(encoding="utf-8")
    fields = [
        ("cash: float", "cash: float = 0.0"),
        ("rice: float", "rice: float = 0.0"),
        ("debt: float", "debt: float = 0.0"),
        ("monthly_burn: float", "monthly_burn: float = 0.0"),
        ("financial_log: list[dict]", "financial_log: list[dict] = field(default_factory=list)"),
        ("family_members: list[dict]", "family_members: list[dict] = field(default_factory=list)"),
        ("genealogy: list[dict]", "genealogy: list[dict] = field(default_factory=list)"),
        ("city_properties: dict", "city_properties: dict = field(default_factory=dict)"),
        ("inventory: dict", "inventory: dict = field(default_factory=dict)"),
    ]
    all_ok = True
    for name, needle in fields:
        all_ok = _step(f"  {name}", needle in src) and all_ok
    return all_ok


def test_apply_financial_change():
    print("\n[2/7] apply_financial_change() 方法 + 校验")
    src = GS.read_text(encoding="utf-8")
    has_method = "def apply_financial_change" in src
    has_max_check = "MAX_TRANSACTION" in src and "100.0" in src
    has_min_check = "MIN_TRANSACTION" in src and "-50.0" in src
    has_borrow_logic = "self.debt += abs(amount)" in src
    has_repay_logic = "self.debt = max(0.0, self.debt - abs(amount))" in src
    has_log = "self.financial_log.append(entry)" in src
    ok = True
    ok = _step("  方法定义", has_method) and ok
    ok = _step("  上限 100 两校验", has_max_check) and ok
    ok = _step("  下限 -50 两校验", has_min_check) and ok
    ok = _step("  borrow → debt 增加", has_borrow_logic) and ok
    ok = _step("  repay → debt 减少（≥0）", has_repay_logic) and ok
    ok = _step("  写入 financial_log", has_log) and ok
    return ok


def test_family_crud():
    print("\n[3/7] family_members CRUD")
    src = GS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  add_family_member 定义", "def add_family_member" in src) and ok
    ok = _step("  update_family_member 定义", "def update_family_member" in src) and ok
    ok = _step("  get_family_member 定义", "def get_family_member" in src) and ok
    ok = _step("  get_family_by_location 定义", "def get_family_by_location" in src) and ok
    ok = _step("  id 重复校验", "id 重复" in src) and ok
    ok = _step("  必填字段校验（id/name/relation）", 'required = {"id", "name", "relation"}' in src) and ok
    return ok


def test_genealogy_crud():
    print("\n[4/7] genealogy CRUD")
    src = GS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  add_genealogy_entry 定义", "def add_genealogy_entry" in src) and ok
    ok = _step("  get_genealogy_by_relation 定义", "def get_genealogy_by_relation" in src) and ok
    ok = _step("  get_known_ancestors 定义", "def get_known_ancestors" in src) and ok
    ok = _step("  必填字段校验（id/relation/name）", 'required = {"id", "relation", "name"}' in src) and ok
    return ok


def test_property_crud():
    print("\n[5/7] city_properties CRUD")
    src = GS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  add_property 定义", "def add_property" in src) and ok
    ok = _step("  get_properties_in_city 定义", "def get_properties_in_city" in src) and ok
    ok = _step("  get_total_property_value 定义", "def get_total_property_value" in src) and ok
    ok = _step("  必填字段校验（id/type/name）", 'required = {"id", "type", "name"}' in src) and ok
    return ok


def test_inventory_crud():
    print("\n[6/7] inventory CRUD")
    src = GS.read_text(encoding="utf-8")
    ok = True
    ok = _step("  add_inventory_item 定义", "def add_inventory_item" in src) and ok
    ok = _step("  transfer_inventory 定义", "def transfer_inventory" in src) and ok
    ok = _step("  get_inventory_summary 定义", "def get_inventory_summary" in src) and ok
    ok = _step("  必填字段校验（id/type/name/qty）", 'required = {"id", "type", "name", "qty"}' in src) and ok
    ok = _step("  qty < 0 校验", 'item["qty"] < 0' in src) and ok
    return ok


def test_snapshot_helpers():
    print("\n[7/7] snapshot_financial 摘要")
    src = GS.read_text(encoding="utf-8")
    return _step(
        "  snapshot_financial 包含 net_worth / rice_days_estimate",
        "def snapshot_financial" in src
        and "net_worth" in src
        and "rice_days_estimate" in src,
    )


if __name__ == "__main__":
    print("=== v1.7.30 4 类信息结构化静态测试 ===\n")
    ok1 = test_fields_exist()
    ok2 = test_apply_financial_change()
    ok3 = test_family_crud()
    ok4 = test_genealogy_crud()
    ok5 = test_property_crud()
    ok6 = test_inventory_crud()
    ok7 = test_snapshot_helpers()
    if all([ok1, ok2, ok3, ok4, ok5, ok6, ok7]):
        print("\n🎉 7 组测试全部通过")
        sys.exit(0)
    else:
        print(f"\n❌ 失败：{ok1=} {ok2=} {ok3=} {ok4=} {ok5=} {ok6=} {ok7=}")
        sys.exit(1)
