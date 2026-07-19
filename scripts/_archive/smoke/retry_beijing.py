#!/usr/bin/env python3
"""重试 beijing 场景图（避开敏感词）"""
import os
import json
import subprocess
import sys
import time

api_key = os.environ['MINIMAX_API_KEY']
out_dir = 'src/frontend/static/scenes/_tmp'

# 重试多次（每次稍微改 prompt）
prompts = [
  'Wide panorama of 16th-century Ming dynasty Beijing royal city, showing traditional Chinese imperial palace complex with red walls and yellow tile roofs, stone gate with guardian statues, wide ceremonial avenues, misty northern mountains in distance, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting',
  'Wide panorama of 16th-century Ming dynasty northern capital Beijing, showing ancient Chinese palace architecture with red walls and tiled roofs, ceremonial street with stone guardians, distant misty mountains, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting',
  'Wide panorama of 16th-century Chinese capital city in the north, showing traditional Chinese royal palace complex with red walls, stone lion statues, ceremonial boulevard, misty mountain backdrop, white background, isolated landscape, no decoration, no watermark, no text, no signature, no seal, no border, panoramic wide view, soft natural lighting',
]

for i, prompt in enumerate(prompts):
  print(f'=== 尝试 {i+1}/{len(prompts)} ===')
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
        with open(f'{out_dir}/beijing.url', 'w') as f:
          f.write(urls[0])
        subprocess.run(['curl', '-sS', '-L', '-o', f'{out_dir}/beijing.png', urls[0]], check=True)
        size = os.path.getsize(f'{out_dir}/beijing.png')
        print(f'  OK! {size} bytes')
        sys.exit(0)
      else:
        meta = d.get('metadata', {})
        print(f'  Failed: success={meta.get("success_count")} failed={meta.get("failed_count")}')
  except Exception as e:
    print(f'  ERROR: {e}')
  time.sleep(2)

sys.exit(1)
