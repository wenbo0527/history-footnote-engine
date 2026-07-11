"""验证 3 张场景图 webp 的 alpha 通道"""
from PIL import Image
import os

base = 'src/frontend/static/scenes'
for name in ['shengze', 'suzhou', 'beijing']:
  path = f'{base}/{name}.webp'
  if not os.path.exists(path):
    print(f'  {name}: 文件不存在')
    continue
  img = Image.open(path)
  print(f'  {name}.webp: size={img.size}, mode={img.mode}')
  if img.mode == 'RGBA':
    w, h = img.size
    alphas = [
      img.getpixel((1, 1))[3],
      img.getpixel((w-2, 1))[3],
      img.getpixel((1, h-2))[3],
      img.getpixel((w-2, h-2))[3],
    ]
    ca = img.getpixel((w//2, h//2))[3]
    print(f'    4 角 alpha: {alphas}  (0=透明, 255=不透明)')
    print(f'    中心 alpha: {ca}')
    # 统计透明像素
    if alphas == [0, 0, 0, 0]:
      print(f'    ✅ 4 角全透明 (50px 边距)')
    else:
      print(f'    ⚠️  4 角不全透明')
