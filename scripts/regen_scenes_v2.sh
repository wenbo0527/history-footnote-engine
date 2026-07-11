#!/bin/bash
# 🆕 v2.7.1 TODO 任务 3: 重做 3 个场景图（米黄背景 → 透明）
# 端点：https://api.minimaxi.com/v1/image_generation

set -e

MINIMAX_API_KEY="${MINIMAX_API_KEY}"
OUT_DIR="src/frontend/static/scenes/_tmp"
mkdir -p "$OUT_DIR"

# 用 python dict 替代 bash associative array
PROMPTS_PY=$(cat <<'PYEOF'
{
  "shengze": "Wide panorama of 16th-century Ming dynasty Jiangnan silk town 盛泽镇 in Chinese ink painting landscape style (山水画), showing canal with small wooden boats, silk dyeing workshops with colorful cloth hanging to dry, traditional tile-roof houses, misty mountains in distance, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting",
  "suzhou": "Wide panorama of 16th-century Ming dynasty Suzhou prefecture city 苏州府 in Chinese ink painting landscape style, showing classical Chinese garden with rockeries, arched bridges over water canals, pagoda in background, traditional shops with silk banners, misty river, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting",
  "beijing": "Wide panorama of 16th-century Ming dynasty Beijing imperial city 北京城 in Chinese ink painting landscape style, showing Forbidden City red walls and yellow tile roofs, imperial gate with stone lions, wide ceremonial avenues, misty northern mountains in distance, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting"
}
PYEOF
)

for name in shengze suzhou beijing; do
  echo "=== 生成 $name ==="

  prompt=$(echo "$PROMPTS_PY" | python3 -c "import json,sys; print(json.load(sys.stdin)['$name'])")
  python3 -c "
import os
import json
import urllib.request
import sys

api_key = os.environ['MINIMAX_API_KEY']
prompt = sys.argv[1]
name = sys.argv[2]
out_dir = sys.argv[3]

payload = {
  'model': 'image-01',
  'prompt': prompt,
  'aspect_ratio': '16:9',
  'response_format': 'url',
  'n': 1,
  'prompt_optimizer': True,
}

req = urllib.request.Request(
  'https://api.minimaxi.com/v1/image_generation',
  data=json.dumps(payload).encode('utf-8'),
  headers={
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
  },
)

try:
  with urllib.request.urlopen(req, timeout=120) as resp:
    d = json.loads(resp.read().decode('utf-8'))
    urls = d.get('data', {}).get('image_urls', [])
    if urls:
      with open(f'{out_dir}/{name}.url', 'w') as f:
        f.write(urls[0])
      print('OK')
    else:
      print('NO_URL', json.dumps(d)[:300], file=sys.stderr)
      sys.exit(1)
except Exception as e:
  print(f'ERROR: {e}', file=sys.stderr)
  sys.exit(1)
" "$prompt" "$name" "$OUT_DIR"

  if [ $? -ne 0 ]; then
    echo "FAILED: $name — 跳过"
    continue
  fi

  url=$(cat "$OUT_DIR/$name.url")
  echo "  URL: $url"
  curl -sS -L -o "$OUT_DIR/$name.png" "$url"
  size=$(ls -lh "$OUT_DIR/$name.png" 2>/dev/null | awk '{print $5}')
  echo "  → $OUT_DIR/$name.png ($size)"
done

echo ""
echo "=== 全部生成完成 ==="
ls -lh "$OUT_DIR/" | tail -10
