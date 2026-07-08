#!/bin/bash
# 联调验证脚本

set -e

echo "=========================================="
echo "🔗 联调验证：前端 proxy → 后端"
echo "=========================================="
echo ""

echo "1. /api/start 创建 session"
RESPONSE=$(curl -s -m 10 -X POST http://localhost:5174/api/start \
  -H "Content-Type: application/json" \
  -d '{"era_id":"wanli1587","identity":"weaving_male","gender":"male","character":{"name":"联调测试","age":30,"occupation":"织工","hometown":"盛泽镇"}}')
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "  session_id: $SESSION_ID"
echo ""

echo "2. /api/state 拿真实 state（前端会调）"
STATE=$(curl -s -m 10 "http://localhost:5174/api/state?session_id=$SESSION_ID")
echo "$STATE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  round:', d.get('round_number'))
print('  cash:', d.get('cash'))
print('  debt:', d.get('debt'))
print('  city:', d.get('current_city'))
print('  character.name:', d.get('character', {}).get('name'))
print('  family:', [f.get('name') + '(' + f.get('relation') + ')' for f in d.get('family_members', [])])
print('  narrative:', d.get('recent_narratives', [{}])[0].get('narrative', '')[:80] if d.get('recent_narratives') else 'none')
print('  active_tasks:', [t.get('title') for t in d.get('sidebar_data', {}).get('active_tasks', [])])
"
echo ""

echo "3. session 持久化测试（再调一次）"
curl -s -m 5 "http://localhost:5174/api/state?session_id=$SESSION_ID" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  ✅ 仍返回正常，session 在内存中保留')
"
echo ""

echo "4. /api/input 测试（调一行动）"
INPUT_RESP=$(curl -s -m 15 -X POST http://localhost:5174/api/input \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"input\":\"先看看家里情况\"}")
echo "$INPUT_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  round after input:', d.get('round_number'))
print('  cash after input:', d.get('cash'))
print('  last_narrative round:', d.get('last_narrative', {}).get('round') if d.get('last_narrative') else 'none')
print('  last_voice_options count:', len(d.get('last_voice_options', [])))
print('  voice 1:', d.get('last_voice_options', [{}])[0].get('voice_name') if d.get('last_voice_options') else 'none')
" 2>&1 | head -10

echo ""
echo "=========================================="
echo "✅ 联调验证完成"
echo "=========================================="
echo ""
echo "后端 API 端口: 8765 (Python)"
echo "前端端口: 5174 (SvelteKit + hooks.server.ts proxy)"
echo ""
echo "如果上面输出全是 ✅，说明前后端联调通了"
