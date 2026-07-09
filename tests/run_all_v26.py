"""
tests/run_all_v26.py - 跑全部 v2.5-v2.6.2 测试

用法：python tests/run_all_v26.py
"""
import sys
import os
import subprocess
from pathlib import Path

# 加 src 到 path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))


def main():
    test_files = [
        "tests/test_v26_integration.py",    # L1: 12
        "tests/test_v26_edge_cases.py",      # L4: 8
        "tests/test_v26_e2e_mock.py",        # L2: 5
        "tests/test_v26_e2e_real_llm.py",    # L3: 3（需要 DEEPSEEK_API_KEY）
        "tests/test_l9_replay.py",           # L9: 5（重放验证）
        "tests/test_v27_temperature.py",     # v2.7: 5（temperature 控制）
    ]

    print("=" * 60)
    print("v2.5-v2.7 完整测试套件")
    print("=" * 60)
    print(f"测试文件: {len(test_files)}")
    print(f"  - L1 整合: 12")
    print(f"  - L2 E2E (mock): 5")
    print(f"  - L3 E2E (真实 LLM): 3")
    print(f"  - L4 边界: 8")
    print(f"  - L9 重放: 5")
    print(f"  - v2.7 temperature: 5")
    print(f"总计: 38 个测试")
    print()

    cwd = ROOT
    total_pass = 0
    total_fail = 0
    for tf in test_files:
        print(f"--- 运行 {tf} ---")
        result = subprocess.run(
            [sys.executable, tf],
            cwd=cwd, capture_output=True, text=True, timeout=600,
        )
        output = result.stdout + result.stderr
        # 统计通过/失败
        for line in output.split("\n"):
            if "通过" in line and "失败" in line:
                print(f"  {line.strip()}")
                # 提取数字
                import re
                m = re.search(r"(\d+)\s*通过.*?(\d+)\s*失败", line)
                if m:
                    total_pass += int(m.group(1))
                    total_fail += int(m.group(2))
        if result.returncode != 0:
            print(f"  ❌ Exit code: {result.returncode}")
            # 输出最后几行排查
            for line in output.split("\n")[-10:]:
                if line.strip():
                    print(f"    {line}")

    print()
    print("=" * 60)
    print(f"汇总: {total_pass} 通过 / {total_fail} 失败")
    print("=" * 60)
    return total_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
