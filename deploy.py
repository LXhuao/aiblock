import os
import sys
import json
import requests
import hashlib
from github import Github
from datetime import datetime

# GitHub 설정
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # GitHub 토큰을 환경 변수로 설정
REPO_NAME = "YOUR_USERNAME/ai_block"  # 본인의 GitHub 저장소로 수정

def get_version():
    with open('ai_block_tray.py', 'r', encoding='utf-8') as f:
        for line in f:
            if 'VERSION = ' in line:
                return line.split('"')[1]
    return None

def create_release_notes():
    version = get_version()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    notes = f"""# AI Block v{version}

배포일: {current_time}

## 업데이트 내용
- 

## 설치 방법
1. 기존 프로그램 종료
2. 다운로드한 설치 파일 실행
3. 관리자 권한으로 설치 진행

## 주의사항
- 관리자 권한이 필요합니다
- 기존 설정은 유지됩니다
"""
    
    with open('release_notes.md', 'w', encoding='utf-8') as f:
        f.write(notes)
    
    print("release_notes.md 파일이 생성되었습니다.")
    print("업데이트 내용을 추가해주세요.")
    input("수정이 완료되면 Enter를 눌러주세요...")

def build_installer():
    # 빌드 스크립트 실행
    os.system('build.bat')
    return os.path.exists('output/ai_block_setup.exe')

def calculate_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def update_version_json(version, installer_path):
    version_info = {
        "version": version,
        "release_date": datetime.now().isoformat(),
        "file_name": "ai_block_setup.exe",
        "sha256": calculate_hash(installer_path)
    }
    
    with open('version.json', 'w', encoding='utf-8') as f:
        json.dump(version_info, f, indent=2, ensure_ascii=False)

def deploy_to_github():
    if not GITHUB_TOKEN:
        print("오류: GITHUB_TOKEN 환경 변수가 설정되지 않았습니다.")
        print("GitHub 개인 액세스 토큰을 환경 변수로 설정해주세요.")
        return False

    try:
        version = get_version()
        installer_path = 'output/ai_block_setup.exe'
        
        if not os.path.exists(installer_path):
            print("오류: 설치 파일을 찾을 수 없습니다.")
            return False
        
        # 버전 정보 업데이트
        update_version_json(version, installer_path)
        
        # GitHub API 연결
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Release Notes 읽기
        with open('release_notes.md', 'r', encoding='utf-8') as f:
            release_notes = f.read()
        
        # 릴리스 생성
        release = repo.create_git_release(
            tag=f"v{version}",
            name=f"AI Block v{version}",
            message=release_notes,
            draft=False,
            prerelease=False
        )
        
        # 파일 업로드
        release.upload_asset(
            installer_path,
            label="AI Block 설치 프로그램",
            content_type="application/octet-stream"
        )
        
        # version.json 업로드
        release.upload_asset(
            'version.json',
            label="버전 정보",
            content_type="application/json"
        )
        
        print(f"v{version} 배포 완료!")
        print(f"릴리스 URL: {release.html_url}")
        return True
        
    except Exception as e:
        print(f"배포 중 오류 발생: {str(e)}")
        return False

def main():
    print("=== AI Block 배포 도구 ===")
    
    # 현재 버전 확인
    version = get_version()
    if not version:
        print("오류: 버전 정보를 찾을 수 없습니다.")
        return
    
    print(f"현재 버전: v{version}")
    
    # Release Notes 생성
    print("\n1. Release Notes 생성 중...")
    create_release_notes()
    
    # 설치 프로그램 빌드
    print("\n2. 설치 프로그램 빌드 중...")
    if not build_installer():
        print("오류: 설치 프로그램 빌드 실패")
        return
    
    # GitHub 배포
    print("\n3. GitHub 배포 중...")
    if deploy_to_github():
        print("\n배포가 성공적으로 완료되었습니다!")
    else:
        print("\n배포 중 오류가 발생했습니다.")

if __name__ == "__main__":
    main() 