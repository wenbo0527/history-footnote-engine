#!/bin/bash
# 🆕 v2.7.1 TODO 任务 3 完整流水线（v2）
# 步骤：3 prompt → 生成 3 jpeg → 去白底 → 加边距 → cwebp → 覆盖

set -e

cd /Users/mac/Documents/trae_projects/history_footnote

MINIMAX_API_KEY="${MINIMAX_API_KEY}"
TMP_DIR="src/frontend/static/scenes/_tmp_v2"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# === 步骤 1: 调 API 生成 3 张图 ===
echo "=== 步骤 1: 调 minimax image-01 API 生成 3 张场景图 ==="

for name in shengze suzhou beijing; do
  echo "  → $name"
  python3 -c "
import os, json, subprocess, sys
api_key = os.environ['MINIMAX_API_KEY']
name = '$name'
out_dir = '$TMP_DIR'

# 3 个 prompt（beijing 用较中性表述避免审查）
PROMPTS = {
  'shengze': 'Wide panorama of 16th-century Ming dynasty Jiangnan silk town 盛泽镇 in Chinese ink painting landscape style (山水画), showing canal with small wooden boats, silk dyeing workshops with colorful cloth hanging to dry, traditional tile-roof houses, misty mountains in distance, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting',
  'suzhou': 'Wide panorama of 16th-century Ming dynasty Suzhou prefecture city 苏州府 in Chinese ink painting landscape style, showing classical Chinese garden with rockeries, arched bridges over water canals, pagoda in background, traditional shops with silk banners, misty river, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting',
  'beijing': 'Wide panorama of 16th-century Ming dynasty northern capital Beijing, showing ancient Chinese palace architecture with red walls and tiled roofs, ceremonial street with stone guardians, distant misty mountains, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting',
}
prompt = PROMPTS[name]
payload = {
  'model': 'image-01',
  'prompt': prompt,
  'aspect_ratio': '16:9',
  'response_format': 'url',
  'n': 1,
  'prompt_optimizer': True,
}
import urllib.request
req = urllib.request.Request(
  'https://api.minimaxi.com/v1/image_generation',
  data=json.dumps(payload).encode('utf-8'),
  headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
)
try:
  with urllib.request.urlopen(req, timeout=120) as resp:
    d = json.loads(resp.read().decode('utf-8'))
    urls = d.get('data', {}).get('image_urls', [])
    if urls:
      url = urls[0]
      # 写 URL 备份 + 下载
      with open(f'{out_dir}/{name}.url', 'w') as f:
        f.write(url)
      subprocess.run(['curl', '-sS', '-L', '-o', f'{out_dir}/{name}.jpg', url], check=True)
      size = os.path.getsize(f'{out_dir}/{name}.jpg')
      print(f'    OK {size} bytes')
    else:
      meta = d.get('metadata', {})
      print(f'    Failed: {meta}', file=sys.stderr)
      sys.exit(1)
except Exception as e:
  print(f'    ERROR: {e}', file=sys.stderr)
  sys.exit(1)
"
  sleep 2
done

echo ""
echo "=== 步骤 2: 验证 3 张 jpg 已下载 ==="
ls -lh "$TMP_DIR"/*.jpg

# === 步骤 3: 去白底 + 加边距 + cwebp ===
echo ""
echo "=== 步骤 3: 去白底 + 加边距 + cwebp 转 webp ==="
for name in shengze suzhou beijing; do
  if [ ! -f "$TMP_DIR/$name.jpg" ]; then
    echo "  ✗ $name.jpg 不存在，跳过"
    continue
  fi
  echo "  → $name"

  # 步骤 3.1: 去白底（fuzz 30% -transparent "#FEFDF8"）
  magick "$TMP_DIR/$name.jpg" -fuzz 30% -transparent "#FEFDF8" -alpha set PNG32:"$TMP_DIR/${name}_s1.png"

  # 步骤 3.2: 加 50px 透明边距
  magick "$TMP_DIR/${name}_s1.png" -bordercolor none -border 50x50 -background none -alpha set PNG32:"$TMP_DIR/${name}_s2.png"

  # 步骤 3.3: cwebp 转 webp（-q 85 -alpha_q 100）
  cwebp -q 85 -alpha_q 100 "$TMP_DIR/${name}_s2.png" -o "$TMP_DIR/${name}.webp" 2>&1 | tail -1

  ls -lh "$TMP_DIR/${name}.webp" | awk '{print "    " $5, $9}'
done

# === 步骤 4: 覆盖旧文件 ===
echo ""
echo "=== 步骤 4: 覆盖 src/frontend/static/scenes/*.webp ==="
for name in shengze suzhou beijing; do
  if [ -f "$TMP_DIR/$name.webp" ]; then
    cp "$TMP_DIR/$name.webp" "src/frontend/static/scenes/$name.webp"
    echo "  ✓ 覆盖 $name.webp"
  fi
done

# === 步骤 5: 清理 ===
echo ""
echo "=== 步骤 5: 清理中间文件 ==="
rm -rf "$TMP_DIR"
rm -rf src/frontend/static/scenes/_tmp
rm -rf src/frontend/static/scenes/_old
rm -f /tmp/shengze_*.png /tmp/suzhou_*.png /tmp/beijing_*.png /tmp/*_final.webp
rm -f src/frontend/static/scenes/*.url
echo "  ✓ 清理完成"

# === 步骤 6: 最终验证 ===
echo ""
echo "=== 步骤 6: 最终状态 ==="
ls -lh src/frontend/static/scenes/
file src/frontend/static/scenes/*.webp
echo ""
echo "=== ✅ 任务 3 全部完成 ==="
