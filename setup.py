from cx_Freeze import setup, Executable
import sys
import os

# 빌드 옵션 설정
build_exe_options = {
    "packages": ["sys", "os", "requests", "PyQt5", "ctypes", "json", "logging"],
    "include_files": ["ai_block_config.json", "tray_icon.png"],
    "include_msvcr": True,
}

# MSI 설치 프로그램 옵션
shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",          # Directory_
     "AI Block",              # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]ai_block_tray.exe",   # Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     "TARGETDIR"               # WkDir
     ),
    
    ("StartupShortcut",        # Shortcut
     "StartupFolder",          # Directory_
     "AI Block",              # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]ai_block_tray.exe",   # Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     "TARGETDIR"               # WkDir
     )
]

# MSI 옵션 설정
msi_data = {
    "Shortcut": shortcut_table
}

bdist_msi_options = {
    "data": msi_data,
    "initial_target_dir": r"[ProgramFilesFolder]\AI Block",
    "upgrade_code": "{1234567A-1234-1234-1234-123456789ABC}",
    "add_to_path": True
}

# 실행 파일 설정
base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [
    Executable(
        "ai_block_tray.py",
        base=base,
        target_name="ai_block_tray.exe",
        icon="tray_icon.ico",
        shortcut_name="AI Block",
        shortcut_dir="ProgramMenuFolder"
    )
]

# 설치 프로그램 생성
setup(
    name="AI Block",
    version="1.0.0",
    description="AI 사이트 차단 프로그램",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options
    },
    executables=executables
) 