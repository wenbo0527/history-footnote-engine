"""Run W33 tests"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/tests')
import test_v33_json_robust as t
tests = [
    t.test_V33_001_nested_brackets,
    t.test_V33_002_trailing_json_no_markdown,
    t.test_V33_003_strip_control_chars_newline_in_string,
    t.test_V33_004_strip_control_chars_tab,
    t.test_V33_005_strip_keeps_escaped_newline,
    t.test_V33_006_fix_truncated_brackets,
    t.test_V33_007_fix_truncated_doesnt_lose_data,
    t.test_V33_008_combined_markdown_and_brackets_and_control,
    t.test_V33_009_realistic_llm_50line_json,
    t.test_V33_010_no_valid_json_returns_none,
]
passed = 0
for t in tests:
    try:
        t()
        print(f'  ✅ {t.__name__}')
        passed += 1
    except Exception as e:
        print(f'  ❌ {t.__name__}: {e}')
        import traceback
        traceback.print_exc()
print(f'\n{passed}/{len(tests)} PASSED')
