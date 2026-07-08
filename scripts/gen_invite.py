"""生成邀请码"""
import sys
from pathlib import Path

sys.path.insert(0, 'src')
from history_footnote.account_system import AccountSystem

storage = Path('saves')
sys_inst = AccountSystem(storage)
code = sys_inst.create_invite_code(label='v1.7.30测试', max_uses=100)
print(f'邀请码: {code.code if hasattr(code, "code") else code}')
print(f'label: {code.label if hasattr(code, "label") else "?"}')
print(f'max_uses: {code.max_uses if hasattr(code, "max_uses") else "?"}')
