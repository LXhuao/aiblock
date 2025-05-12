import sys
import os
import requests
from PyQt5 import QtWidgets, QtGui, QtCore
import ctypes
import time
import json
import logging
from datetime import datetime
import hashlib
import tempfile
import shutil
import subprocess

# 설정 파일 경로
CONFIG_FILE = "ai_block_config.json"
LOG_FILE = "ai_block.log"
VERSION = "1.0.0"
UPDATE_URL = "https://api.github.com/repos/zynesa/aiblock/releases/latest"
UPDATE_CHECK_INTERVAL = 3600  # 1시간마다 업데이트 확인
DEBUG_MODE = False  # 개발자 모드 활성화

# 기본 설정
DEFAULT_CONFIG = {
    "ADMIN_PASSWORD": "nobak",
    "MASTER_PASSWORD": "zynesa",
    "DEVELOPER_MODE": True,  # 개발자 모드 설정
    "DEBUG_MODE": True,      # 디버그 모드 설정
    "LOCK_DURATION": 300,
    "MAX_FAIL": 5,
    "AUTO_BLOCK_INTERVAL": 60,
    "NOTIFICATION_DURATION": 3000,
    "HOSTS_PATH": r"C:\\Windows\\System32\\drivers\\etc\\hosts",
    "BLOCK_MARK": "# --- AI SITES BLOCK START ---",
    "UNBLOCK_MARK": "# --- AI SITES BLOCK END ---",
    "ICON_URL": "https://i.ibb.co/jPbBD0Cv/3d3f76385ef27e2663dc15b2162a4a66.jpg",
    "ICON_PATH": "tray_icon.png",
    "UPDATE_URL": UPDATE_URL,
    "UPDATE_CHECK_INTERVAL": UPDATE_CHECK_INTERVAL,
    "LAST_UPDATE_CHECK": 0,
    "DEV_SERVER": "http://localhost:8000",  # 개발 서버 URL
    "PROD_SERVER": "https://your-production-server.com"  # 프로덕션 서버 URL
}

# 로깅 설정
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = {**DEFAULT_CONFIG, **json.load(f)}
            else:
                self.config = DEFAULT_CONFIG
                self._save_config()
        except Exception as e:
            logging.error(f"설정 로드 실패: {e}")
            self.config = DEFAULT_CONFIG
    
    def _save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"설정 저장 실패: {e}")
    
    def __getattr__(self, name):
        return self.config.get(name, DEFAULT_CONFIG.get(name))

# AI 도메인 목록
AI_DOMAINS = [
    "chat.openai.com", "chatgpt.com", "openai.com", "wrtn.ai", "blackbox.ai", "perplexity.ai", 
    "gemini.google.com", "claude.ai", "x.ai", "chat.mistral.ai", "deepseek.com", "meta.ai", 
    "pi.ai", "character.ai", "poe.com", "midjourney.com", "stability.ai", "adobe.com", 
    "runwayml.com", "heygen.com", "synthesia.io", "lumen5.com", "invideo.io", "picsart.com",
    "craiyon.com", "deepart.io", "kling.kuaishou.com", "elevenlabs.io", "murf.ai", "suno.ai",
    "aiva.ai", "krisp.ai", "voicemod.net", "notta.ai", "notion.so", "gamma.app", "copy.ai",
    "jasper.ai", "writesonic.com", "quillbot.com", "grammarly.com", "reclaim.ai", "fathom.video",
    "rask.ai", "presentations.ai", "clickup.com", "taskade.com", "github.com", "tabnine.com",
    "codium.ai", "replit.com", "mutable.ai", "askcodi.com", "lightning.ai", "firebase.google.com",
    "uizard.io", "hubspot.com", "zendesk.com", "intercom.com", "drift.com", "ada.cx", "yext.com",
    "lately.ai", "buffer.com", "marketmuse.com", "hostinger.com", "10web.io", "elegantthemes.com",
    "tealhq.com", "kickresume.com", "sanebox.com", "shortwave.com", "getguru.com", "textio.com",
    "cvviz.com", "spicychat.ai", "toolify.ai", "theresanaiforthat.com",
    
    # 새로운 AI 도메인 추가
    "bard.google.com",
    "anthropic.com",
    "cohere.ai",
    "huggingface.co",
    "replicate.com",
    "deepl.com",
    "assemblyai.com",
    "scale.com",
    "forefront.ai",
    "deepmind.com"
]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class CustomMessageBox(QtWidgets.QMessageBox):
    def __init__(self, title, message, icon=QtWidgets.QMessageBox.Information):
        super().__init__()
        self.setWindowTitle(title)
        self.setText(message)
        self.setIcon(icon)
        self.setWindowIcon(QtGui.QIcon(Config().ICON_PATH))
        self.setStyleSheet("""
            QMessageBox {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)

def show_message(title, message, icon=QtWidgets.QMessageBox.Information):
    msg = CustomMessageBox(title, message, icon)
    msg.exec_()

def block_ai_sites():
    config = Config()
    if not os.access(config.HOSTS_PATH, os.W_OK):
        show_message("권한 오류", "관리자 권한이 필요합니다.\n'관리자 권한으로 실행'을 선택해 주세요.", QtWidgets.QMessageBox.Critical)
        return False
    
    try:
        with open(config.HOSTS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        if config.BLOCK_MARK in content and config.UNBLOCK_MARK in content:
            return True
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(config.HOSTS_PATH, "a", encoding="utf-8") as hosts_file:
            hosts_file.write(f"\n{config.BLOCK_MARK} - {timestamp}\n")
            for domain in AI_DOMAINS:
                hosts_file.write(f"127.0.0.1 {domain}\n")
                hosts_file.write(f"127.0.0.1 www.{domain}\n")
                hosts_file.write(f"::1 {domain}\n")
                hosts_file.write(f"::1 www.{domain}\n")
            hosts_file.write(f"{config.UNBLOCK_MARK}\n")
        
        logging.info("사이트 차단 완료")
        return True
    except Exception as e:
        logging.error(f"사이트 차단 실패: {e}")
        return False

def unblock_ai_sites():
    config = Config()
    if not os.access(config.HOSTS_PATH, os.W_OK):
        show_message("권한 오류", "관리자 권한이 필요합니다.\n'관리자 권한으로 실행'을 선택해 주세요.", QtWidgets.QMessageBox.Critical)
        return False
    
    try:
        with open(config.HOSTS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        new_lines = []
        skip = False
        found = False
        
        for line in lines:
            if config.BLOCK_MARK in line:
                skip = True
                found = True
                continue
            if config.UNBLOCK_MARK in line:
                skip = False
                continue
            if not skip:
                new_lines.append(line)
        
        with open(config.HOSTS_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        if found:
            show_message("해제 성공", "사이트 차단이 해제되었습니다.")
            logging.info("사이트 차단 해제 완료")
        else:
            show_message("해제 불필요", "차단 구간이 존재하지 않습니다.", QtWidgets.QMessageBox.Warning)
        
        return True
    except Exception as e:
        logging.error(f"사이트 차단 해제 실패: {e}")
        return False

def download_icon():
    config = Config()
    if not os.path.exists(config.ICON_PATH):
        try:
            r = requests.get(config.ICON_URL)
            r.raise_for_status()
            with open(config.ICON_PATH, "wb") as f:
                f.write(r.content)
            logging.info("아이콘 다운로드 완료")
        except Exception as e:
            logging.error(f"아이콘 다운로드 실패: {e}")

class SecurePasswordDialog(QtWidgets.QDialog):
    lock_until = 0

    def __init__(self, prompt, parent=None):
        super().__init__(parent)
        self.setWindowTitle(prompt)
        self.setWindowIcon(QtGui.QIcon(Config().ICON_PATH))
        self.setFixedSize(340, 160)
        self.fail_count = 0
        self.result = False
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #333333;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        self.label = QtWidgets.QLabel(prompt)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.label)
        
        self.caps_label = QtWidgets.QLabel("")
        self.caps_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        layout.addWidget(self.caps_label)
        
        self.pw = QtWidgets.QLineEdit()
        self.pw.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pw.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        self.pw.setInputMethodHints(QtCore.Qt.ImhHiddenText | QtCore.Qt.ImhNoPredictiveText | QtCore.Qt.ImhNoAutoUppercase)
        layout.addWidget(self.pw)
        
        self.pw.textChanged.connect(self.check_capslock)
        
        self.lock_label = QtWidgets.QLabel("")
        self.lock_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        layout.addWidget(self.lock_label)
        
        btn = QtWidgets.QPushButton("확인")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=QtCore.Qt.AlignCenter)
        
        self.pw.returnPressed.connect(self.accept)

    def check_capslock(self):
        caps = QtWidgets.QApplication.queryKeyboardModifiers() & QtCore.Qt.ShiftModifier
        if caps:
            self.caps_label.setText("CapsLock이 켜져 있습니다!")
        else:
            self.caps_label.setText("")

    def exec_with_password(self, password, master_password=None):
        config = Config()
        master_password = master_password or config.MASTER_PASSWORD
        self.fail_count = 0
        
        while True:
            now = time.time()
            if now < self.lock_until:
                remaining = int(self.lock_until - now)
                self.lock_label.setText(f"비밀번호 입력이 잠금되었습니다. {remaining}초 후 재시도 가능.")
                self.pw.setDisabled(True)
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(1000)
                continue
            else:
                self.lock_label.setText("")
                self.pw.setDisabled(False)

            if self.exec_() == QtWidgets.QDialog.Accepted:
                entered_pw = self.pw.text()
                if entered_pw == password:
                    self.result = True
                    logging.info("비밀번호 인증 성공")
                    return True
                elif entered_pw == master_password:
                    self.lock_until = 0
                    self.lock_label.setText("마스터 비밀번호로 잠금 해제됨.")
                    logging.info("마스터 비밀번호로 잠금 해제")
                    QtWidgets.QApplication.processEvents()
                    QtCore.QThread.msleep(1000)
                    self.pw.clear()
                    continue
                else:
                    self.fail_count += 1
                    self.label.setText(f"비밀번호가 올바르지 않습니다. (시도 {self.fail_count}/{config.MAX_FAIL})")
                    logging.warning(f"비밀번호 인증 실패 (시도 {self.fail_count})")
                    self.pw.clear()
                    if self.fail_count >= config.MAX_FAIL:
                        self.lock_until = time.time() + config.LOCK_DURATION
                        self.lock_label.setText(f"비밀번호 입력이 {config.LOCK_DURATION//60}분간 잠금되었습니다.")
                        logging.warning(f"비밀번호 입력 잠금 ({config.LOCK_DURATION//60}분)")
                        self.pw.setDisabled(True)
                        QtWidgets.QApplication.processEvents()
                        QtCore.QThread.msleep(2000)
                        return False
            else:
                break
        return False

class Updater(QtCore.QObject):
    update_available = QtCore.pyqtSignal(str, str)  # version, download_url
    update_progress = QtCore.pyqtSignal(int)  # progress percentage
    update_completed = QtCore.pyqtSignal(bool, str)  # success, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.current_version = VERSION

    def check_for_updates(self):
        try:
            now = time.time()
            if now - self.config.LAST_UPDATE_CHECK < self.config.UPDATE_CHECK_INTERVAL:
                return

            response = requests.get(self.config.UPDATE_URL)
            response.raise_for_status()
            release_info = response.json()
            
            latest_version = release_info['tag_name'].lstrip('v')
            if self._compare_versions(latest_version, self.current_version) > 0:
                download_url = release_info['assets'][0]['browser_download_url']
                self.update_available.emit(latest_version, download_url)
                logging.info(f"새로운 버전 발견: {latest_version}")
            
            # 마지막 업데이트 확인 시간 저장
            self.config.config['LAST_UPDATE_CHECK'] = now
            self.config._save_config()

        except Exception as e:
            logging.error(f"업데이트 확인 실패: {e}")

    def download_and_install_update(self, download_url):
        try:
            # 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, "update.exe")

            # 업데이트 파일 다운로드
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            downloaded = 0

            with open(temp_file, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    progress = int((downloaded / total_size) * 100)
                    self.update_progress.emit(progress)

            # 현재 프로그램 종료 후 업데이트 실행
            update_script = os.path.join(temp_dir, "update.bat")
            with open(update_script, 'w') as f:
                f.write(f'''@echo off
timeout /t 2 /nobreak
"{temp_file}"
del "%~f0"
''')

            subprocess.Popen([update_script], shell=True)
            self.update_completed.emit(True, "업데이트가 다운로드되었습니다. 프로그램을 재시작합니다.")
            QtWidgets.qApp.quit()

        except Exception as e:
            logging.error(f"업데이트 설치 실패: {e}")
            self.update_completed.emit(False, f"업데이트 설치 실패: {str(e)}")
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _compare_versions(self, version1, version2):
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0

class UpdateDialog(QtWidgets.QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.setWindowTitle("업데이트 확인")
        self.setFixedSize(400, 150)
        self.setWindowIcon(QtGui.QIcon(Config().ICON_PATH))

        layout = QtWidgets.QVBoxLayout(self)

        message = QtWidgets.QLabel(f"새로운 버전 {version}이(가) 있습니다.\n지금 업데이트하시겠습니까?")
        message.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(message)

        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        btn_layout = QtWidgets.QHBoxLayout()
        
        self.update_btn = QtWidgets.QPushButton("업데이트")
        self.update_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.update_btn)
        
        cancel_btn = QtWidgets.QPushButton("나중에")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

    def show_progress(self, value):
        self.progress.setVisible(True)
        self.progress.setValue(value)
        self.update_btn.setEnabled(False)

class TrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)
        self.config = Config()
        self.setToolTip("AI 사이트 차단 프로그램")
        self.last_block_time = 0
        
        # 업데이트 관리자 초기화
        self.updater = Updater()
        self.updater.update_available.connect(self.show_update_dialog)
        self.updater.update_progress.connect(self.update_progress)
        self.updater.update_completed.connect(self.update_completed)
        
        # 메뉴 생성
        menu = QtWidgets.QMenu(parent)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        
        block_action = menu.addAction("사이트 차단 (즉시)")
        block_action.triggered.connect(self.block_sites)
        
        unblock_action = menu.addAction("사이트 해제")
        unblock_action.triggered.connect(self.show_password_dialog)
        
        menu.addSeparator()
        
        status_action = menu.addAction("차단 상태 확인")
        status_action.triggered.connect(self.check_block_status)
        
        update_action = menu.addAction("업데이트 확인")
        update_action.triggered.connect(lambda: self.updater.check_for_updates())
        
        # 개발자 메뉴 추가
        if self.config.DEVELOPER_MODE:
            menu.addSeparator()
            dev_menu = menu.addMenu("개발자 도구")
            
            debug_action = dev_menu.addAction("디버그 모드 토글")
            debug_action.setCheckable(True)
            debug_action.setChecked(self.config.DEBUG_MODE)
            debug_action.triggered.connect(self.toggle_debug_mode)
            
            reload_config_action = dev_menu.addAction("설정 새로고침")
            reload_config_action.triggered.connect(self.reload_config)
            
            clear_logs_action = dev_menu.addAction("로그 초기화")
            clear_logs_action.triggered.connect(self.clear_logs)
            
            test_update_action = dev_menu.addAction("업데이트 테스트")
            test_update_action.triggered.connect(self.test_update)
        
        menu.addSeparator()
        
        exit_action = menu.addAction("종료")
        exit_action.triggered.connect(self.show_exit_dialog)
        
        self.setContextMenu(menu)
        
        # 자동 차단 타이머 설정
        self.block_timer = QtCore.QTimer()
        self.block_timer.timeout.connect(self.check_and_block)
        self.block_timer.start(self.config.AUTO_BLOCK_INTERVAL * 1000)
        
        # 업데이트 확인 타이머 설정
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.updater.check_for_updates)
        self.update_timer.start(self.config.UPDATE_CHECK_INTERVAL * 1000)
        
        # 초기 차단 및 업데이트 확인
        QtCore.QTimer.singleShot(100, self.block_sites)
        QtCore.QTimer.singleShot(1000, self.updater.check_for_updates)

    def show_update_dialog(self, version, download_url):
        dialog = UpdateDialog(version, self.parent())
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.updater.download_and_install_update(download_url)
            self.update_dialog = dialog

    def update_progress(self, value):
        if hasattr(self, 'update_dialog'):
            self.update_dialog.show_progress(value)

    def update_completed(self, success, message):
        if success:
            show_message("업데이트", message)
        else:
            show_message("업데이트 실패", message, QtWidgets.QMessageBox.Critical)

    def block_sites(self):
        if block_ai_sites():
            self.showMessage(
                "차단 완료",
                "AI 사이트가 차단되었습니다.",
                QtWidgets.QSystemTrayIcon.Information,
                self.config.NOTIFICATION_DURATION
            )
            self.last_block_time = time.time()
        else:
            self.showMessage(
                "차단 실패",
                "차단에 실패했거나 이미 차단되어 있습니다.",
                QtWidgets.QSystemTrayIcon.Warning,
                self.config.NOTIFICATION_DURATION
            )

    def check_and_block(self):
        try:
            with open(self.config.HOSTS_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            if self.config.BLOCK_MARK not in content or self.config.UNBLOCK_MARK not in content:
                self.block_sites()
        except Exception as e:
            logging.error(f"자동 차단 검사 실패: {e}")

    def check_block_status(self):
        try:
            with open(self.config.HOSTS_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            
            if self.config.BLOCK_MARK in content and self.config.UNBLOCK_MARK in content:
                show_message("차단 상태", "AI 사이트가 현재 차단되어 있습니다.")
            else:
                show_message("차단 상태", "AI 사이트가 차단되어 있지 않습니다.", QtWidgets.QMessageBox.Warning)
        except Exception as e:
            logging.error(f"차단 상태 확인 실패: {e}")
            show_message("오류", "차단 상태를 확인할 수 없습니다.", QtWidgets.QMessageBox.Critical)

    def show_password_dialog(self):
        dlg = SecurePasswordDialog("사이트 해제 - 관리자 비밀번호 입력")
        if dlg.exec_with_password(self.config.ADMIN_PASSWORD):
            unblock_ai_sites()
            QtWidgets.qApp.quit()

    def show_exit_dialog(self):
        dlg = SecurePasswordDialog("프로그램 종료 - 관리자 비밀번호 입력")
        if dlg.exec_with_password(self.config.ADMIN_PASSWORD):
            logging.info("프로그램 종료")
            QtWidgets.qApp.quit()

    def toggle_debug_mode(self):
        self.config.config['DEBUG_MODE'] = not self.config.DEBUG_MODE
        self.config._save_config()
        logging.info(f"디버그 모드: {'켜짐' if self.config.DEBUG_MODE else '꺼짐'}")
        show_message("디버그 모드", f"디버그 모드가 {'켜졌' if self.config.DEBUG_MODE else '꺼졌'}습니다.")

    def reload_config(self):
        self.config._load_config()
        logging.info("설정 새로고침 완료")
        show_message("설정 새로고침", "설정이 새로고침되었습니다.")

    def clear_logs(self):
        try:
            with open(LOG_FILE, 'w') as f:
                f.write('')
            logging.info("로그 초기화 완료")
            show_message("로그 초기화", "로그가 초기화되었습니다.")
        except Exception as e:
            logging.error(f"로그 초기화 실패: {e}")
            show_message("오류", "로그 초기화에 실패했습니다.", QtWidgets.QMessageBox.Critical)

    def test_update(self):
        test_version = f"{VERSION}.test"
        self.show_update_dialog(test_version, self.config.DEV_SERVER + "/test-update")

def main():
    if os.name == "nt" and not is_admin():
        QtWidgets.QMessageBox.critical(None, "권한 오류", "이 프로그램은 반드시 '관리자 권한으로 실행'해야 합니다.")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        sys.exit(0)
    
    try:
        download_icon()
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")
        
        icon = QtGui.QIcon(Config().ICON_PATH)
        tray = TrayApp(icon)
        tray.show()
        
        app.setQuitOnLastWindowClosed(False)
        logging.info("프로그램 시작")
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"프로그램 실행 중 치명적 오류 발생: {e}")
        show_message("치명적 오류", f"프로그램 실행 중 오류가 발생했습니다.\n{str(e)}", QtWidgets.QMessageBox.Critical)
        sys.exit(1)

if __name__ == "__main__":
    main() 