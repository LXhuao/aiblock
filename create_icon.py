from PIL import Image, ImageDraw
import os

# 64x64 크기의 아이콘 생성
icon_size = (64, 64)
icon = Image.new('RGBA', icon_size, (0, 0, 0, 0))
draw = ImageDraw.Draw(icon)

# 아이콘 디자인 - 빨간색 원에 'AI' 텍스트
draw.ellipse([(4, 4), (60, 60)], fill=(255, 0, 0))
draw.text((22, 22), 'AI', fill=(255, 255, 255))

# 파일 저장
icon.save('tray_icon.png')
print("트레이 아이콘이 생성되었습니다.") 