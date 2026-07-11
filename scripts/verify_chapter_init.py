"""验证 chapter.__init__.py 公共 API 全部可导入"""
import sys
sys.path.insert(0, '/Users/mac/Documents/trae_projects/history_footnote/src')
import history_footnote.chapter as ch
print(f"chapter version: {ch.__version__}")
print(f"chapter public API: {len(ch.__all__)} items")
for name in ch.__all__:
    obj = getattr(ch, name, None)
    if obj is None and name != 'make_chapter_dm_tools':
        print(f"  ❌ {name}: NOT FOUND")
    else:
        if callable(obj):
            print(f"  ✅ {name}: {type(obj).__name__}")
        elif hasattr(obj, '__class__'):
            print(f"  📦 {name}: {type(obj).__name__ if not isinstance(obj, type) else 'class ' + obj.__name__}")
        else:
            print(f"  📌 {name}: {type(obj).__name__}")
print(f"\n_HAS_LC_TOOLS: {ch._HAS_LC_TOOLS}")
