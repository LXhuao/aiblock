@echo off
echo AI Block 제거 중...

REM 프로세스 종료
taskkill /F /IM ai_block_tray.exe 2>nul

REM 레지스트리 제거
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Run" /v "AI Block" /f 2>nul
reg delete "HKLM\Software\Zyn\AI Block" /f 2>nul
reg delete "HKCU\Software\Zyn\AI Block" /f 2>nul

REM 시작 메뉴 바로가기 제거
rd /s /q "%ProgramData%\Microsoft\Windows\Start Menu\Programs\AI Block" 2>nul
rd /s /q "%AppData%\Microsoft\Windows\Start Menu\Programs\AI Block" 2>nul

REM 프로그램 파일 제거
rd /s /q "%ProgramFiles%\AI Block" 2>nul

REM hosts 파일 정리
powershell -Command "& {$content = Get-Content 'C:\Windows\System32\drivers\etc\hosts' -Raw; $pattern = '# --- AI SITES BLOCK START ---[\s\S]*?# --- AI SITES BLOCK END ---\r?\n?'; $content = $content -replace $pattern, ''; Set-Content 'C:\Windows\System32\drivers\etc\hosts' $content}"

echo AI Block가 성공적으로 제거되었습니다.
pause 