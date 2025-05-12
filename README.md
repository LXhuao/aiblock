# AI Block

AI 사이트 차단 프로그램

## 기능

- AI 사이트 자동 차단
- 시스템 트레이 상주
- 관리자 비밀번호 보호
- 자동 업데이트
- 개발자 모드
- MSI 설치 프로그램
- 완전 제거 지원

## 설치

1. [최신 릴리즈](https://github.com/YOUR_USERNAME/aiblock/releases/latest)에서 `AI_Block_Setup.msi` 다운로드
2. MSI 설치 프로그램 실행 (관리자 권한 필요)

## 제거

1. Windows 설정 > 앱 > 앱 및 기능에서 "AI Block" 제거
2. 또는 설치 폴더의 `uninstall.bat` 실행 (관리자 권한 필요)

## 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
python ai_block_tray.py

# 빌드
pyinstaller --noconfirm --onefile --windowed --icon=tray_icon.png --add-data "tray_icon.png;." ai_block_tray.py

# MSI 빌드 (WiX Toolset 필요)
candle.exe installer/config.wxs -ext WixUIExtension -arch x64
light.exe config.wixobj -ext WixUIExtension -out AI_Block_Setup.msi
```

## 기본 설정

- 관리자 비밀번호: nobak
- 마스터 비밀번호: zynesa

## 라이선스

MIT License 