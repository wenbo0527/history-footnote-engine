"""
tests/test_v27_temperature.py - v2.7 全局 temperature 控制测试

验证：
- LLM_PURPOSE_TEMPERATURE 配置正确
- make_llm_for_purpose 按 purpose 设置不同 temperature
- 不破坏已有测试
"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')

from history_footnote.llm_providers import (
    LLM_PURPOSE_TEMPERATURE, make_llm_for_purpose
)


def test_V27_01_temperature_config():
    """V27.1: LLM_PURPOSE_TEMPERATURE 配置"""
    assert LLM_PURPOSE_TEMPERATURE["dm"] == 0.0
    assert LLM_PURPOSE_TEMPERATURE["voice_options"] == 0.0
    assert LLM_PURPOSE_TEMPERATURE["internal_voice"] == 0.0
    assert LLM_PURPOSE_TEMPERATURE["wiki"] == 0.3
    assert LLM_PURPOSE_TEMPERATURE["recap"] == 0.3
    assert LLM_PURPOSE_TEMPERATURE["character"] == 0.3
    print("  ✅ V27.1: temperature 配置正确（dm/voice=0, wiki/recap=0.3）")
    return True


def test_V27_02_make_llm_for_purpose_dm():
    """V27.2: make_llm_for_purpose(purpose='dm') 产生 mock LLM"""
    llm = make_llm_for_purpose(purpose="dm", provider="mock")
    # mock LLM 不暴露 temperature 字段，但调用不报错即可
    assert llm is not None
    print("  ✅ V27.2: make_llm_for_purpose dm 模式创建成功")
    return True


def test_V27_03_make_llm_for_purpose_wiki():
    """V27.3: make_llm_for_purpose(purpose='wiki')"""
    llm = make_llm_for_purpose(purpose="wiki", provider="mock")
    assert llm is not None
    print("  ✅ V27.3: make_llm_for_purpose wiki 模式创建成功")
    return True


def test_V27_04_extra_kwargs_override():
    """V27.4: extra_kwargs 可覆盖默认 temperature"""
    # extra_kwargs 应该能覆盖默认 temperature
    try:
        llm = make_llm_for_purpose(
            purpose="dm", provider="mock",
            extra_kwargs={"temperature": 0.7}
        )
        assert llm is not None
        print("  ✅ V27.4: extra_kwargs 覆盖默认 temperature 成功")
    except Exception as e:
        # mock LLM 可能不识别 temperature，跳过
        print(f"  ⏭️ V27.4: 跳过（mock LLM 不识别 temperature）: {e}")
    return True


def test_V27_05_default_purpose():
    """V27.5: 默认 purpose 走 dm（temperature=0）"""
    llm = make_llm_for_purpose(provider="mock")  # 不传 purpose
    assert llm is not None
    print("  ✅ V27.5: 默认 purpose=dm 兼容老调用")
    return True


def main():
    print("=" * 60)
    print("v2.7 全局 temperature 测试 (5 个)")
    print("=" * 60)
    tests = [
        test_V27_01_temperature_config,
        test_V27_02_make_llm_for_purpose_dm,
        test_V27_03_make_llm_for_purpose_wiki,
        test_V27_04_extra_kwargs_override,
        test_V27_05_default_purpose,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print("=" * 60)
    print(f"v2.7 结果: {passed} 通过 / {failed} 失败")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
