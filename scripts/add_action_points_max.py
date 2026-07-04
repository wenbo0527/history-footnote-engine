"""给 era.json 的 6 个 identity 加 action_points_max"""
import json
from pathlib import Path

ERA_PATH = Path("eras/wanli1587/era.json")
data = json.loads(ERA_PATH.read_text(encoding="utf-8"))

# 各身份行动点（v1.4.0 设计）：
# - 织户（weaving_*）：3 点（基础）
# - 商人（merchant_*）：4 点（应酬多、跑动多）
# - 读书人（scholar_*）：2 点（读书思考慢，1 回合=长时间）
AP_MAP = {
    "weaving_male": 3,
    "weaving_female": 3,
    "merchant_male": 4,
    "merchant_female": 4,
    "scholar_male": 2,
    "scholar_female": 2,
}

identities = data.get("world", {}).get("player_identities", {})
for id_name, ap in AP_MAP.items():
    if id_name in identities:
        identities[id_name]["action_points_max"] = ap

# 写回
ERA_PATH.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print("✅ action_points_max 写入完成")
for id_name, ap in AP_MAP.items():
    if id_name in identities:
        print(f"  {id_name}: {ap} 点/月")
