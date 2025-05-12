from PIL import Image, ImageDraw, ImageFont
import os
import sys

try:
    # 64x64 크기의 아이콘 생성
    icon_size = (64, 64)
    icon = Image.new('RGBA', icon_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)

    # 아이콘 디자인 - 빨간색 원에 'AI' 텍스트
    draw.ellipse([(4, 4), (60, 60)], fill=(255, 0, 0))
    
    # 폰트 설정 - 기본 폰트 사용(GitHub Actions에서 폰트 문제 방지)
    try:
        # 시스템에 있는 폰트 사용 시도
        if os.name == 'nt':  # Windows
            font_path = "C:\\Windows\\Fonts\\Arial.ttf"
        else:  # Linux/Unix
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 20)
            draw.text((22, 22), 'AI', fill=(255, 255, 255), font=font)
        else:
            # 폰트 파일이 없으면 기본 폰트 사용
            draw.text((22, 22), 'AI', fill=(255, 255, 255))
    except Exception as e:
        print(f"폰트 설정 오류: {e}")
        # 오류 발생 시 기본 텍스트 그리기 방법 사용
        draw.text((22, 22), 'AI', fill=(255, 255, 255))

    # 파일 저장
    icon.save('tray_icon.png')
    print("트레이 아이콘이 생성되었습니다.")
    
    # 아이콘 확인
    if os.path.exists('tray_icon.png'):
        size = os.path.getsize('tray_icon.png')
        print(f"아이콘 파일 크기: {size} 바이트")
    else:
        print("경고: 아이콘 파일이 생성되지 않았습니다.")
        
except Exception as e:
    print(f"아이콘 생성 중 오류 발생: {e}")
    
    # 오류 발생 시 단순한 방법으로 다시 시도
    try:
        simple_icon = Image.new('RGBA', (64, 64), (255, 0, 0, 255))
        simple_draw = ImageDraw.Draw(simple_icon)
        simple_draw.text((22, 22), 'AI', fill=(255, 255, 255))
        simple_icon.save('tray_icon.png')
        print("단순 아이콘으로 대체 생성 완료")
    except Exception as backup_error:
        print(f"백업 아이콘 생성도 실패: {backup_error}")
        sys.exit(1) 