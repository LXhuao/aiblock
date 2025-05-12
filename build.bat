@echo off
echo AI Block 빌드 스크립트 시작

REM Python 가상환경 생성 및 활성화
python -m venv venv
call venv\Scripts\activate

REM 필요한 패키지 설치
pip install -r requirements.txt

REM PyInstaller로 실행 파일 생성
pyinstaller --noconfirm --onedir --windowed --icon=tray_icon.ico --add-data "tray_icon.png;." --add-data "ai_block_config.json;." ai_block_tray.py

REM Inno Setup으로 설치 프로그램 생성
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

echo 빌드 완료! output 폴더에서 설치 프로그램을 확인하세요.
pause 