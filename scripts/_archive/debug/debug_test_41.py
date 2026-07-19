"""快速跑 test_V28_41 看错误"""
import sys
import traceback
sys.path.insert(0, 'src')
sys.path.insert(0, 'tests')
import test_v28_chapter_s3 as t
try:
    t.test_V28_41_coordinator_full_lifecycle_through_chapter()
    print('PASSED')
except Exception as e:
    traceback.print_exc()
    print('FAILED')
