"""统计测试数量和覆盖"""
import ast
import pathlib
from collections import defaultdict

total = 0
modules = {}
for pattern in ['test_v28_*.py', 'test_v30_*.py', 'test_v32_*.py', 'test_v33_*.py']:
    for p in pathlib.Path('/Users/mac/Documents/trae_projects/history_footnote/tests').glob(pattern):
        src = p.read_text()
        tree = ast.parse(src)
        fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
        modules[p.name] = len(fns)
        total += len(fns)
for k, v in sorted(modules.items()):
    print(f'  {k:40s} {v} tests')
print(f'  TOTAL: {total} tests')

# 统计代码模块覆盖
src_modules = {
    'coordinator.py': 0,
    'sub_facades.py': 0,
    'closure.py': 0,
    'settlement.py': 0,
    'meta_resolver.py': 0,
    'paths.py': 0,
    'plates.py': 0,
    'plate_engine.py': 0,
    'path_switcher.py': 0,
    'fallback.py': 0,
    'validator.py': 0,
    'schema_converter.py': 0,
    'prompt_builder.py': 0,
    'dm_tool.py': 0,
    'dm_tools_lc.py': 0,
    'types.py': 0,
    'narrative_sanitizer.py': 0,
    'llm_wrapper.py': 0,
    'game_loop.py': 0,
    'game_state.py': 0,
}
print('\n=== 源码模块 ===')
for k, v in src_modules.items():
    print(f'  {k:30s}')
