# AI Block

AI 서비스 접속을 차단하는 Windows용 프로그램입니다.

## 주요 기능

- 100개 이상의 주요 AI 서비스 도메인 자동 차단 (ChatGPT, Claude, Bard 등)
- 시스템 트레이에서 편리하게 실행 (백그라운드)
- 10초마다 자동으로 차단 상태 유지
- 관리자 권한으로 실행하여 완벽한 차단 보장
- 비밀번호 보호 기능으로 무단 해제 방지
- 자동 업데이트 기능
- 개발자 모드 지원

## 다운로드

[최신 버전 다운로드](https://github.com/zynesa/aiblock/releases/latest)

## 설치 방법

### 방법 1: 설치 프로그램 (권장)

1. 최신 릴리스에서 설치 파일을 다운로드합니다.
2. 설치 프로그램을 실행하고 지시를 따릅니다.
3. 프로그램이 자동으로 시작됩니다.

### 방법 2: 소스에서 실행

1. 저장소를 클론합니다:
   ```bash
   git clone https://github.com/zynesa/aiblock.git
   cd aiblock
   ```

2. 필요한 패키지를 설치합니다:
   ```bash
   pip install -r requirements.txt
   ```

3. 프로그램을 실행합니다:
   ```bash
   python ai_block_tray.py
   ```

## 사용 방법

- 프로그램이 실행되면 시스템 트레이에 빨간색 AI 아이콘이 표시됩니다.
- 아이콘을 우클릭하여 차단 해제, 관리 옵션 또는 종료 등의 기능을 이용할 수 있습니다.
- 차단 해제를 위해서는 설정된 비밀번호가 필요합니다.

## 기술 스택

- Python 3.9+
- PyQt5 (UI 프레임워크)
- Windows API (호스트 파일 및 관리자 권한 관리)

## 기여하기

프로젝트에 기여하고 싶다면 다음 단계를 따라주세요:

1. 이 저장소를 포크합니다.
2. 새 기능 브랜치를 만듭니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다.

## 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요. 