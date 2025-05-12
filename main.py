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
import base64
import socket
import uuid
import platform
import winreg  # Windows 레지스트리 접근을 위한 모듈

# 설정 파일 경로
CONFIG_FILE = "ai_block_config.json"
LOG_FILE = "ai_block.log"
VERSION = "1.0.2"  # 버전 업데이트
APP_ID = "com.zynesa.aiblock"  # 고유 앱 식별자
DOMAIN_LIST_URL = "https://raw.githubusercontent.com/zynesa/aiblock/main/ai_domains.json"
DOMAIN_CHECK_INTERVAL = 7200  # 2시간마다 도메인 목록 확인
DEBUG_MODE = False  # 개발자 모드 활성화
AUTHORIZED_MACHINES_FILE = "authorized_machines.dat"  # 인증된 기기 목록 파일

# 기본 설정
DEFAULT_CONFIG = {
    "ADMIN_PASSWORD": "nobak",
    "MASTER_PASSWORD": "zynesa",
    "DEVELOPER_MODE": True,
    "DEBUG_MODE": True,
    "LOCK_DURATION": 300,
    "MAX_FAIL": 5,
    "AUTO_BLOCK_INTERVAL": 60,
    "NOTIFICATION_DURATION": 3000,
    "HOSTS_PATH": "C:\\Windows\\System32\\drivers\\etc\\hosts",
    "BLOCK_MARK": "# --- AI SITES BLOCK START ---",
    "UNBLOCK_MARK": "# --- AI SITES BLOCK END ---",
    "ICON_URL": "https://i.ibb.co/jPbBD0Cv/3d3f76385ef27e2663dc15b2162a4a66.jpg",
    "ICON_PATH": "tray_icon.png",
    "DOMAIN_LIST_URL": DOMAIN_LIST_URL,
    "DOMAIN_CHECK_INTERVAL": DOMAIN_CHECK_INTERVAL,
    "LAST_DOMAIN_CHECK": 0,
    "DEV_SERVER": "https://dev.zynesa.com",
    "MACHINE_ID": "",
    "INSTALLED_DATE": 0,
    "AUTOSTART_REGISTERED": False,  # 자동 시작 등록 여부
    "AUTHORIZED_MACHINE": False,    # 현재 기기 인증 여부
    "MACHINE_NAME": "",             # 현재 기기 이름
    "LAST_HEARTBEAT": 0,            # 마지막 하트비트 시간
}

# 로깅 설정
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MachineAuth:
    """기기 인증 관리 클래스"""
    _instance = None
    _authorized_machines = {}  # machine_id: {name, last_seen, added_date}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_authorized_machines()
        return cls._instance
    
    def _load_authorized_machines(self):
        """인증된 기기 목록 로드"""
        try:
            if os.path.exists(AUTHORIZED_MACHINES_FILE):
                with open(AUTHORIZED_MACHINES_FILE, 'rb') as f:
                    encrypted_data = f.read()
                    # 간단한 XOR 암호화 해제 (실제로는 더 강력한 암호화를 사용해야 함)
                    key = b'ZYNESA_KEY'
                    decrypted_data = bytes(a ^ b for a, b in zip(encrypted_data, key * (1 + len(encrypted_data) // len(key))))
                    
                    try:
                        data = json.loads(decrypted_data.decode('utf-8'))
                        if isinstance(data, dict):
                            self._authorized_machines = data
                            logging.info(f"{len(self._authorized_machines)}개의 인증된 기기 로드됨")
                    except json.JSONDecodeError:
                        logging.error("인증 파일 손상됨, 초기화")
                        self._authorized_machines = {}
            else:
                logging.info("인증된 기기 목록 파일이 없음, 새로 생성")
                self._authorized_machines = {}
                self._save_authorized_machines()
        except Exception as e:
            logging.error(f"인증된 기기 목록 로드 실패: {e}")
            self._authorized_machines = {}
    
    def _save_authorized_machines(self):
        """인증된 기기 목록 저장"""
        try:
            data_str = json.dumps(self._authorized_machines)
            data_bytes = data_str.encode('utf-8')
            
            # 간단한 XOR 암호화 (실제로는 더 강력한 암호화를 사용해야 함)
            key = b'ZYNESA_KEY'
            encrypted_data = bytes(a ^ b for a, b in zip(data_bytes, key * (1 + len(data_bytes) // len(key))))
            
            with open(AUTHORIZED_MACHINES_FILE, 'wb') as f:
                f.write(encrypted_data)
            
            # 파일 보호
            if os.name == 'nt':
                try:
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    FILE_ATTRIBUTE_SYSTEM = 0x04
                    FILE_ATTRIBUTE_READONLY = 0x01
                    ctypes.windll.kernel32.SetFileAttributesW(
                        AUTHORIZED_MACHINES_FILE, 
                        FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                    )
                except Exception as e:
                    logging.error(f"인증 파일 보호 실패: {e}")
            
            logging.info(f"{len(self._authorized_machines)}개의 인증된 기기 저장됨")
        except Exception as e:
            logging.error(f"인증된 기기 목록 저장 실패: {e}")
    
    def is_authorized(self, machine_id):
        """특정 기기가 인증되어 있는지 확인"""
        return machine_id in self._authorized_machines
    
    def authorize_machine(self, machine_id, machine_name):
        """기기 인증 등록"""
        if not machine_id or not machine_name:
            return False
            
        now = int(time.time())
        self._authorized_machines[machine_id] = {
            "name": machine_name,
            "last_seen": now,
            "added_date": now
        }
        self._save_authorized_machines()
        logging.info(f"새 기기 인증됨: {machine_name} ({machine_id[:8]}...)")
        return True
    
    def update_last_seen(self, machine_id):
        """기기의 마지막 활동 시간 업데이트"""
        if machine_id in self._authorized_machines:
            self._authorized_machines[machine_id]["last_seen"] = int(time.time())
            self._save_authorized_machines()
            return True
        return False
    
    def revoke_machine(self, machine_id):
        """기기 인증 해제"""
        if machine_id in self._authorized_machines:
            machine_name = self._authorized_machines[machine_id]["name"]
            del self._authorized_machines[machine_id]
            self._save_authorized_machines()
            logging.info(f"기기 인증 해제됨: {machine_name} ({machine_id[:8]}...)")
            return True
        return False
    
    def get_all_machines(self):
        """모든 인증된 기기 목록 반환"""
        return self._authorized_machines.copy()
    
    def get_machine_info(self, machine_id):
        """특정 기기 정보 반환"""
        return self._authorized_machines.get(machine_id, None)

class Config:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
            cls._instance._initialize_config()
        return cls._instance
    
    def _initialize_config(self):
        """설정 초기화 - 처음 실행 시 필요한 값들 설정"""
        # 기기 ID가 비어있으면 생성
        if not self.config.get("MACHINE_ID"):
            try:
                # 기기 고유 ID 생성 (MAC 주소 + 시스템 정보 해시)
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2*6, 8)])
                system_info = f"{os.getenv('COMPUTERNAME')}-{os.getenv('USERNAME')}-{platform.system()}-{platform.machine()}"
                machine_id = hashlib.sha256(f"{mac}-{system_info}".encode()).hexdigest()
                self.config["MACHINE_ID"] = machine_id
                logging.info(f"새 기기 ID 생성됨: {machine_id[:8]}...")
            except Exception as e:
                logging.error(f"기기 ID 생성 실패: {e}")
                self.config["MACHINE_ID"] = hashlib.sha256(str(time.time()).encode()).hexdigest()
        
        # 기기 이름이 비어있으면 설정
        if not self.config.get("MACHINE_NAME"):
            try:
                self.config["MACHINE_NAME"] = os.getenv('COMPUTERNAME') or f"PC-{self.config['MACHINE_ID'][:6]}"
            except Exception:
                self.config["MACHINE_NAME"] = f"PC-{self.config['MACHINE_ID'][:6]}"
        
        # 설치 날짜가 0이면 현재 시간으로 설정
        if self.config.get("INSTALLED_DATE", 0) == 0:
            self.config["INSTALLED_DATE"] = int(time.time())
            logging.info(f"설치 날짜 기록: {datetime.fromtimestamp(self.config['INSTALLED_DATE'])}")
        
        # 자동 시작 프로그램 등록 확인 및 등록
        if not self.config.get("AUTOSTART_REGISTERED", False):
            if register_autostart():
                self.config["AUTOSTART_REGISTERED"] = True
                logging.info("자동 시작 프로그램 등록 완료")
            
        self._save_config()
    
    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 기존 설정에 새로운 기본 설정 항목 추가
                    self.config = DEFAULT_CONFIG.copy()
                    self.config.update(loaded_config)
            else:
                self.config = DEFAULT_CONFIG.copy()
                self._save_config()
        except Exception as e:
            logging.error(f"설정 로드 실패: {e}")
            self.config = DEFAULT_CONFIG.copy()
    
    def _save_config(self):
        try:
            # 설정 파일 디렉토리가 없으면 생성
            config_dir = os.path.dirname(os.path.abspath(CONFIG_FILE))
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
                
            # 설정 파일을 숨김 및 시스템 속성으로 설정
            if os.name == 'nt':  # Windows
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    FILE_ATTRIBUTE_SYSTEM = 0x04
                    FILE_ATTRIBUTE_READONLY = 0x01
                    ctypes.windll.kernel32.SetFileAttributesW(
                        CONFIG_FILE, 
                        FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                    )
                except Exception as e:
                    logging.error(f"설정 파일 속성 설정 실패: {e}")
                    
        except Exception as e:
            logging.error(f"설정 저장 실패: {e}")
    
    def __getattr__(self, name):
        return self.config.get(name, DEFAULT_CONFIG.get(name))
    
    def update_config(self, new_config):
        """설정 업데이트"""
        if not isinstance(new_config, dict):
            return False
            
        try:
            # 보안 관련 설정은 업데이트하지 않음
            secure_keys = ["ADMIN_PASSWORD", "MASTER_PASSWORD"]
            for key, value in new_config.items():
                if key not in secure_keys:
                    self.config[key] = value
            self._save_config()
            return True
        except Exception as e:
            logging.error(f"설정 업데이트 실패: {e}")
            return False

def register_autostart(remove=False):
    """Windows 시작 프로그램에 등록/제거"""
    try:
        # 현재 실행 파일의 경로
        exe_path = os.path.abspath(sys.executable)
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 경우
            exe_path = os.path.abspath(sys.executable)
        else:
            # 스크립트로 실행 중인 경우
            script_path = os.path.abspath(__file__)
            exe_path = f'"{sys.executable}" "{script_path}"'
        
        # 레지스트리에 등록할 경로
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        value_name = "AIBlockTray"
        
        # 레지스트리 키 열기
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if remove:
                # 등록 제거
                try:
                    winreg.DeleteValue(key, value_name)
                    logging.info("자동 시작 등록 제거됨")
                    return True
                except FileNotFoundError:
                    logging.warning("자동 시작 등록이 존재하지 않음")
                    return False
            else:
                # 등록
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, exe_path)
                logging.info(f"자동 시작 등록됨: {exe_path}")
                return True
    except Exception as e:
        logging.error(f"자동 시작 등록/제거 실패: {e}")
        return False

def check_and_restore_autostart():
    """자동 시작 등록 상태를 확인하고 필요시 다시 등록"""
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        value_name = "AIBlockTray"
        
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                # 값이 존재하면 이미 등록됨
                return True
        except FileNotFoundError:
            # 키가 없으면 등록
            register_autostart()
            return True
        except Exception:
            # 값이 없으면 등록
            register_autostart()
            return True
            
    except Exception as e:
        logging.error(f"자동 시작 확인 실패: {e}")
        # 실패시 등록 시도
        register_autostart()
        return False

def protect_autostart_registry():
    """자동 시작 레지스트리 보호"""
    try:
        # 레지스트리 보호 설정
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        value_name = "AIBlockTray"
        
        # 먼저 현재 값을 확인
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            try:
                current_value, _ = winreg.QueryValueEx(key, value_name)
            except FileNotFoundError:
                # 등록이 안되어 있으면 다시 등록
                return register_autostart()
        
        # 값이 존재하면 보호
        return True
    except Exception as e:
        logging.error(f"자동 시작 레지스트리 보호 실패: {e}")
        return False

class DomainManager:
    _instance = None
    _domains = [
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
        "bard.google.com", "anthropic.com", "cohere.ai", "huggingface.co", "replicate.com",
        "deepl.com", "assemblyai.com", "scale.com", "forefront.ai", "deepmind.com"
    ]
    _domains_updated = 0
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_domains()
        return cls._instance
    
    def _load_domains(self):
        """로컬 파일에서 도메인 목록 로드"""
        try:
            domain_file = "ai_domains.json"
            if os.path.exists(domain_file):
                with open(domain_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        self._domains = data
                        logging.info(f"로컬에서 {len(self._domains)}개 도메인 로드됨")
                    if isinstance(data, dict) and "domains" in data and "updated" in data:
                        self._domains = data["domains"]
                        self._domains_updated = data["updated"]
                        logging.info(f"로컬에서 {len(self._domains)}개 도메인 로드됨 (업데이트: {datetime.fromtimestamp(self._domains_updated)})")
        except Exception as e:
            logging.error(f"도메인 목록 로드 실패: {e}")
    
    def _save_domains(self):
        """도메인 목록을 로컬 파일에 저장"""
        try:
            domain_file = "ai_domains.json"
            data = {
                "domains": self._domains,
                "updated": self._domains_updated
            }
            with open(domain_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logging.info(f"{len(self._domains)}개 도메인 저장됨")
            
            # 도메인 파일 보호
            if os.name == 'nt':  # Windows
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    FILE_ATTRIBUTE_SYSTEM = 0x04
                    FILE_ATTRIBUTE_READONLY = 0x01
                    ctypes.windll.kernel32.SetFileAttributesW(
                        domain_file, 
                        FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                    )
                except Exception as e:
                    logging.error(f"도메인 파일 속성 설정 실패: {e}")
                    
        except Exception as e:
            logging.error(f"도메인 목록 저장 실패: {e}")
    
    def update_domains(self, url=None):
        """GitHub 원본에서 도메인 목록 업데이트"""
        config = Config()
        url = url or config.DOMAIN_LIST_URL
        
        # 마지막 업데이트 시간 확인
        now = time.time()
        if now - config.config.get('LAST_DOMAIN_CHECK', 0) < config.DOMAIN_CHECK_INTERVAL and url == config.DOMAIN_LIST_URL:
            return False, "업데이트 간격이 충분하지 않음"
            
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 응답 형식 검사 및 처리
            if isinstance(data, list) and len(data) > 0:
                self._domains = data
                self._domains_updated = int(time.time())
                self._save_domains()
                # 마지막 도메인 확인 시간 업데이트
                config.config['LAST_DOMAIN_CHECK'] = now
                config._save_config()
                return True, f"{len(self._domains)}개 도메인 업데이트 완료"
            elif isinstance(data, dict) and "domains" in data:
                self._domains = data["domains"]
                self._domains_updated = data.get("updated", int(time.time()))
                self._save_domains()
                # 마지막 도메인 확인 시간 업데이트
                config.config['LAST_DOMAIN_CHECK'] = now
                config._save_config()
                return True, f"{len(self._domains)}개 도메인 업데이트 완료"
            else:
                return False, "잘못된 응답 형식"
                
        except Exception as e:
            logging.error(f"도메인 목록 업데이트 실패: {e}")
            return False, f"업데이트 실패: {str(e)}"
    
    def get_domains(self):
        """도메인 목록 반환"""
        return self._domains.copy()
    
    def add_domain(self, domain):
        """도메인 추가"""
        if domain and domain not in self._domains:
            self._domains.append(domain)
            self._domains_updated = int(time.time())
            self._save_domains()
            return True
        return False
    
    def remove_domain(self, domain):
        """도메인 제거"""
        if domain in self._domains:
            self._domains.remove(domain)
            self._domains_updated = int(time.time())
            self._save_domains()
            return True
        return False

# 글로벌 접근을 위한 AI 도메인 목록
AI_DOMAINS = DomainManager().get_domains()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

class AutoStartWatcher(QtCore.QObject):
    """자동 시작 설정을 주기적으로 확인하고 복구하는 클래스"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_registry)
        # 5분마다 체크
        self.timer.start(300000)
        
    def check_registry(self):
        """레지스트리 상태를 확인하고 필요시 복구"""
        try:
            # 자동 시작 레지스트리 확인
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            value_name = "AIBlockTray"
            
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    # 자동 시작이 등록되어 있으면 정상
                    logging.debug("자동 시작 레지스트리 확인 완료")
            except Exception:
                # 레지스트리 값이 없으면 다시 등록
                logging.warning("자동 시작 레지스트리가 손상되었거나 삭제됨, 재등록 중...")
                register_autostart()
                
            # 설정 파일 보호 상태 확인
            if os.path.exists(CONFIG_FILE):
                attrs = ctypes.windll.kernel32.GetFileAttributesW(CONFIG_FILE)
                if attrs != -1:  # INVALID_FILE_ATTRIBUTES
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    FILE_ATTRIBUTE_SYSTEM = 0x04
                    FILE_ATTRIBUTE_READONLY = 0x01
                    required_attrs = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                    
                    if (attrs & required_attrs) != required_attrs:
                        logging.warning("설정 파일 보호 속성이 변경됨, 재설정 중...")
                        ctypes.windll.kernel32.SetFileAttributesW(
                            CONFIG_FILE, 
                            FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                        )
            
            # 도메인 파일 보호 상태 확인
            domain_file = "ai_domains.json"
            if os.path.exists(domain_file):
                attrs = ctypes.windll.kernel32.GetFileAttributesW(domain_file)
                if attrs != -1:  # INVALID_FILE_ATTRIBUTES
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    FILE_ATTRIBUTE_SYSTEM = 0x04
                    FILE_ATTRIBUTE_READONLY = 0x01
                    required_attrs = FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                    
                    if (attrs & required_attrs) != required_attrs:
                        logging.warning("도메인 파일 보호 속성이 변경됨, 재설정 중...")
                        ctypes.windll.kernel32.SetFileAttributesW(
                            domain_file, 
                            FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                        )
                
        except Exception as e:
            logging.error(f"자동 시작 감시 오류: {e}")

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

class TrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)
        self.config = Config()
        self.setToolTip("AI 사이트 차단 프로그램")
        self.last_block_time = 0
        
        # 기기 인증 관리자 및 자동 시작 감시자 초기화
        self.machine_auth = MachineAuth()
        self.autostart_watcher = AutoStartWatcher(self)
        
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
        
        update_action = menu.addAction("도메인 목록 업데이트")
        update_action.triggered.connect(self.update_domains)
        
        # 기기 인증 메뉴 (마스터 비밀번호로 보호)
        auth_action = menu.addAction("기기 인증 관리")
        auth_action.triggered.connect(self.show_auth_menu)
        
        # 개발자 메뉴 (마스터 비밀번호로 보호)
        developer_action = menu.addAction("개발자 도구")
        developer_action.triggered.connect(self.show_developer_menu)
        
        menu.addSeparator()
        
        exit_action = menu.addAction("종료")
        exit_action.triggered.connect(self.show_exit_dialog)
        
        self.setContextMenu(menu)
        
        # 자동 차단 타이머 설정
        self.block_timer = QtCore.QTimer()
        self.block_timer.timeout.connect(self.check_and_block)
        self.block_timer.start(self.config.AUTO_BLOCK_INTERVAL * 1000)
        
        # 도메인 업데이트 타이머 설정
        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_domains)
        self.update_timer.start(self.config.DOMAIN_CHECK_INTERVAL * 1000)
        
        # 하트비트 타이머 설정 (기기 활성 상태 유지)
        self.heartbeat_timer = QtCore.QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)
        self.heartbeat_timer.start(600000)  # 10분마다 하트비트
        
        # 초기 차단, 도메인 업데이트, 자동 시작 및 기기 인증 체크
        QtCore.QTimer.singleShot(100, self.block_sites)
        QtCore.QTimer.singleShot(1000, self.update_domains)
        QtCore.QTimer.singleShot(3000, self.check_autostart_status)
        QtCore.QTimer.singleShot(5000, self.check_machine_auth)

    def show_developer_menu(self):
        """마스터 비밀번호 확인 후 개발자 메뉴 표시"""
        dlg = SecurePasswordDialog("개발자 도구 - 마스터 비밀번호 입력")
        if dlg.exec_with_password(self.config.MASTER_PASSWORD):
            self.display_developer_menu()
        else:
            logging.warning("개발자 도구 접근 실패 - 마스터 비밀번호 불일치")
    
    def display_developer_menu(self):
        """개발자 메뉴 표시"""
        dev_menu = QtWidgets.QMenu()
        dev_menu.setStyleSheet("""
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
        
        debug_action = dev_menu.addAction("디버그 모드 토글")
        debug_action.setCheckable(True)
        debug_action.setChecked(self.config.DEBUG_MODE)
        debug_action.triggered.connect(self.toggle_debug_mode)
        
        reload_config_action = dev_menu.addAction("설정 새로고침")
        reload_config_action.triggered.connect(self.reload_config)
        
        clear_logs_action = dev_menu.addAction("로그 초기화")
        clear_logs_action.triggered.connect(self.clear_logs)
        
        test_update_action = dev_menu.addAction("도메인 업데이트 테스트")
        test_update_action.triggered.connect(self.test_update)
        
        check_autostart_action = dev_menu.addAction("자동 시작 상태 확인")
        check_autostart_action.triggered.connect(self.check_autostart_status)
        
        view_machine_id_action = dev_menu.addAction("기기 ID 확인")
        view_machine_id_action.triggered.connect(self.view_machine_id)
        
        # 메뉴 표시
        dev_menu.exec_(QtGui.QCursor.pos())
    
    def show_auth_menu(self):
        """마스터 비밀번호 확인 후 기기 인증 메뉴 표시"""
        dlg = SecurePasswordDialog("기기 인증 관리 - 마스터 비밀번호 입력")
        if dlg.exec_with_password(self.config.MASTER_PASSWORD):
            self.display_auth_menu()
        else:
            logging.warning("기기 인증 관리 접근 실패 - 마스터 비밀번호 불일치")
    
    def display_auth_menu(self):
        """기기 인증 메뉴 표시"""
        auth_menu = QtWidgets.QMenu()
        auth_menu.setStyleSheet("""
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
        
        # 현재 기기 인증 상태
        current_machine_id = self.config.MACHINE_ID
        is_authorized = self.machine_auth.is_authorized(current_machine_id)
        
        if is_authorized:
            status_action = auth_menu.addAction("✓ 현재 기기 인증됨")
            status_action.setEnabled(False)
            
            revoke_action = auth_menu.addAction("현재 기기 인증 해제")
            revoke_action.triggered.connect(self.revoke_current_machine)
        else:
            status_action = auth_menu.addAction("✗ 현재 기기 인증 안됨")
            status_action.setEnabled(False)
            
            auth_action = auth_menu.addAction("현재 기기 인증하기")
            auth_action.triggered.connect(self.authorize_current_machine)
        
        auth_menu.addSeparator()
        
        view_machines_action = auth_menu.addAction("인증된 기기 목록 보기")
        view_machines_action.triggered.connect(self.view_authorized_machines)
        
        # 메뉴 표시
        auth_menu.exec_(QtGui.QCursor.pos())
    
    def authorize_current_machine(self):
        """현재 기기 인증"""
        machine_id = self.config.MACHINE_ID
        machine_name = self.config.MACHINE_NAME
        
        if self.machine_auth.authorize_machine(machine_id, machine_name):
            self.config.config["AUTHORIZED_MACHINE"] = True
            self.config._save_config()
            show_message("기기 인증", f"현재 기기가 인증되었습니다.\n\n기기명: {machine_name}")
            logging.info(f"현재 기기 인증됨: {machine_name} ({machine_id[:8]}...)")
            return True
        else:
            show_message("기기 인증 실패", "현재 기기 인증에 실패했습니다.", QtWidgets.QMessageBox.Warning)
            logging.error(f"현재 기기 인증 실패: {machine_name} ({machine_id[:8]}...)")
            return False
    
    def revoke_current_machine(self):
        """현재 기기 인증 해제"""
        machine_id = self.config.MACHINE_ID
        machine_name = self.config.MACHINE_NAME
        
        if self.machine_auth.revoke_machine(machine_id):
            self.config.config["AUTHORIZED_MACHINE"] = False
            self.config._save_config()
            show_message("기기 인증 해제", f"현재 기기의 인증이 해제되었습니다.\n\n기기명: {machine_name}")
            logging.info(f"현재 기기 인증 해제됨: {machine_name} ({machine_id[:8]}...)")
            return True
        else:
            show_message("기기 인증 해제 실패", "현재 기기의 인증 해제에 실패했습니다.", QtWidgets.QMessageBox.Warning)
            logging.error(f"현재 기기 인증 해제 실패: {machine_name} ({machine_id[:8]}...)")
            return False
    
    def view_authorized_machines(self):
        """인증된 기기 목록 보기"""
        machines = self.machine_auth.get_all_machines()
        if not machines:
            show_message("인증된 기기 없음", "인증된 기기가 없습니다.")
            return
        
        # 목록 표시를 위한 다이얼로그 생성
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("인증된 기기 목록")
        dialog.setFixedSize(500, 400)
        dialog.setWindowIcon(QtGui.QIcon(self.config.ICON_PATH))
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # 테이블 생성
        table = QtWidgets.QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["기기명", "기기 ID", "마지막 활동", "인증 날짜"])
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setColumnWidth(0, 120)
        table.setColumnWidth(1, 80)
        table.setColumnWidth(2, 140)
        table.setColumnWidth(3, 140)
        
        # 데이터 추가
        table.setRowCount(len(machines))
        row = 0
        current_machine_id = self.config.MACHINE_ID
        
        for machine_id, info in machines.items():
            name_item = QtWidgets.QTableWidgetItem(info["name"])
            id_item = QtWidgets.QTableWidgetItem(machine_id[:8] + "...")
            
            last_seen = datetime.fromtimestamp(info["last_seen"]).strftime("%Y-%m-%d %H:%M")
            last_seen_item = QtWidgets.QTableWidgetItem(last_seen)
            
            added_date = datetime.fromtimestamp(info["added_date"]).strftime("%Y-%m-%d %H:%M")
            added_date_item = QtWidgets.QTableWidgetItem(added_date)
            
            # 현재 기기 강조
            if machine_id == current_machine_id:
                name_item.setBackground(QtGui.QColor(200, 230, 250))
                id_item.setBackground(QtGui.QColor(200, 230, 250))
                last_seen_item.setBackground(QtGui.QColor(200, 230, 250))
                added_date_item.setBackground(QtGui.QColor(200, 230, 250))
                name_item.setText(name_item.text() + " (현재)")
            
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, id_item)
            table.setItem(row, 2, last_seen_item)
            table.setItem(row, 3, added_date_item)
            row += 1
        
        layout.addWidget(table)
        
        # 버튼 영역
        button_layout = QtWidgets.QHBoxLayout()
        
        revoke_button = QtWidgets.QPushButton("선택 기기 인증 해제")
        revoke_button.clicked.connect(lambda: self.revoke_selected_machine(table))
        button_layout.addWidget(revoke_button)
        
        refresh_button = QtWidgets.QPushButton("새로고침")
        refresh_button.clicked.connect(lambda: self.refresh_machine_list(table))
        button_layout.addWidget(refresh_button)
        
        close_button = QtWidgets.QPushButton("닫기")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        dialog.exec_()
    
    def revoke_selected_machine(self, table):
        """선택된 기기 인증 해제"""
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            show_message("선택 오류", "기기를 선택해주세요.", QtWidgets.QMessageBox.Warning)
            return
        
        # 기기 목록 가져오기
        machines = self.machine_auth.get_all_machines()
        machine_ids = list(machines.keys())
        
        for index in selected_rows:
            row = index.row()
            if row < len(machine_ids):
                machine_id = machine_ids[row]
                machine_name = machines[machine_id]["name"]
                
                # 현재 기기인지 확인
                is_current = machine_id == self.config.MACHINE_ID
                
                if self.machine_auth.revoke_machine(machine_id):
                    if is_current:
                        self.config.config["AUTHORIZED_MACHINE"] = False
                        self.config._save_config()
                    
                    show_message("인증 해제 완료", f"기기명: {machine_name}\n인증이 해제되었습니다.")
                    logging.info(f"기기 인증 해제됨: {machine_name} ({machine_id[:8]}...)")
                    
                    # 테이블에서 해당 행 제거
                    table.removeRow(row)
                else:
                    show_message("인증 해제 실패", f"기기명: {machine_name}\n인증 해제에 실패했습니다.", QtWidgets.QMessageBox.Warning)
    
    def refresh_machine_list(self, table):
        """기기 목록 새로고침"""
        machines = self.machine_auth.get_all_machines()
        
        # 테이블 초기화
        table.setRowCount(0)
        table.setRowCount(len(machines))
        
        # 데이터 추가
        row = 0
        current_machine_id = self.config.MACHINE_ID
        
        for machine_id, info in machines.items():
            name_item = QtWidgets.QTableWidgetItem(info["name"])
            id_item = QtWidgets.QTableWidgetItem(machine_id[:8] + "...")
            
            last_seen = datetime.fromtimestamp(info["last_seen"]).strftime("%Y-%m-%d %H:%M")
            last_seen_item = QtWidgets.QTableWidgetItem(last_seen)
            
            added_date = datetime.fromtimestamp(info["added_date"]).strftime("%Y-%m-%d %H:%M")
            added_date_item = QtWidgets.QTableWidgetItem(added_date)
            
            # 현재 기기 강조
            if machine_id == current_machine_id:
                name_item.setBackground(QtGui.QColor(200, 230, 250))
                id_item.setBackground(QtGui.QColor(200, 230, 250))
                last_seen_item.setBackground(QtGui.QColor(200, 230, 250))
                added_date_item.setBackground(QtGui.QColor(200, 230, 250))
                name_item.setText(name_item.text() + " (현재)")
            
            table.setItem(row, 0, name_item)
            table.setItem(row, 1, id_item)
            table.setItem(row, 2, last_seen_item)
            table.setItem(row, 3, added_date_item)
            row += 1
    
    def send_heartbeat(self):
        """주기적인 기기 상태 업데이트 (하트비트)"""
        machine_id = self.config.MACHINE_ID
        if self.machine_auth.is_authorized(machine_id):
            self.machine_auth.update_last_seen(machine_id)
            self.config.config["LAST_HEARTBEAT"] = int(time.time())
            self.config._save_config()
            logging.debug(f"하트비트 전송: {machine_id[:8]}...")
    
    def check_machine_auth(self):
        """기기 인증 상태 확인"""
        machine_id = self.config.MACHINE_ID
        is_authorized = self.machine_auth.is_authorized(machine_id)
        
        # 설정과 실제 인증 상태 동기화
        if is_authorized != self.config.AUTHORIZED_MACHINE:
            self.config.config["AUTHORIZED_MACHINE"] = is_authorized
            self.config._save_config()
            logging.info(f"기기 인증 상태 동기화: {is_authorized}")
        
        if is_authorized:
            # 하트비트 업데이트
            self.machine_auth.update_last_seen(machine_id)
            self.config.config["LAST_HEARTBEAT"] = int(time.time())
            self.config._save_config()
        else:
            # 첫 실행이면 자동 인증 (편의를 위해)
            if not os.path.exists("first_run.marker"):
                self.authorize_current_machine()
        
        return is_authorized

    def update_domains(self):
        domain_manager = DomainManager()
        success, message = domain_manager.update_domains()
        if success:
            logging.info(message)
            global AI_DOMAINS
            AI_DOMAINS = domain_manager.get_domains()
            if self.config.DEBUG_MODE:
                self.showMessage(
                    "도메인 업데이트",
                    message,
                    QtWidgets.QSystemTrayIcon.Information,
                    self.config.NOTIFICATION_DURATION
                )
        else:
            logging.error(f"도메인 업데이트 실패: {message}")
            if self.config.DEBUG_MODE:
                self.showMessage(
                    "도메인 업데이트 실패",
                    message,
                    QtWidgets.QSystemTrayIcon.Warning,
                    self.config.NOTIFICATION_DURATION
                )
        # 도메인 업데이트 후 재차단
        if self.check_is_blocked():
            self.block_sites()

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
        if not self.check_is_blocked():
            self.block_sites()

    def check_is_blocked(self):
        try:
            with open(self.config.HOSTS_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            return self.config.BLOCK_MARK in content and self.config.UNBLOCK_MARK in content
        except Exception as e:
            logging.error(f"차단 상태 확인 실패: {e}")
            return False

    def check_block_status(self):
        if self.check_is_blocked():
            show_message("차단 상태", "AI 사이트가 현재 차단되어 있습니다.")
        else:
            show_message("차단 상태", "AI 사이트가 차단되어 있지 않습니다.", QtWidgets.QMessageBox.Warning)

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
        domain_manager = DomainManager()
        success, message = domain_manager.update_domains(self.config.DEV_SERVER + "/test-domains.json")
        show_message("도메인 업데이트 테스트", message)
        
    def view_machine_id(self):
        """기기 ID 확인"""
        machine_id = self.config.MACHINE_ID
        machine_name = self.config.MACHINE_NAME
        installed_date = datetime.fromtimestamp(self.config.INSTALLED_DATE).strftime("%Y-%m-%d %H:%M:%S")
        auth_status = "인증됨" if self.machine_auth.is_authorized(machine_id) else "인증되지 않음"
        message = f"기기명: {machine_name}\n\n기기 ID: {machine_id}\n\n설치 날짜: {installed_date}\n\n인증 상태: {auth_status}"
        show_message("기기 정보", message)

    def check_autostart_status(self):
        """자동 시작 등록 상태 확인"""
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            value_name = "AIBlockTray"
            
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    # 값이 존재하면 이미 등록됨
                    if self.config.DEBUG_MODE:
                        show_message("자동 시작 상태", f"자동 시작이 등록되어 있습니다.\n\n경로: {value}")
                    logging.info(f"자동 시작 상태 확인: 등록됨 ({value})")
                    return True
            except FileNotFoundError:
                # 키가 없으면 등록
                if register_autostart():
                    if self.config.DEBUG_MODE:
                        show_message("자동 시작 상태", "자동 시작이 새로 등록되었습니다.")
                    logging.info("자동 시작 상태 확인: 새로 등록됨")
                    return True
                else:
                    if self.config.DEBUG_MODE:
                        show_message("자동 시작 상태", "자동 시작 등록에 실패했습니다.", QtWidgets.QMessageBox.Warning)
                    logging.error("자동 시작 상태 확인: 등록 실패")
                    return False
            except Exception:
                # 값이 없으면 등록
                if register_autostart():
                    if self.config.DEBUG_MODE:
                        show_message("자동 시작 상태", "자동 시작이 새로 등록되었습니다.")
                    logging.info("자동 시작 상태 확인: 새로 등록됨")
                    return True
                else:
                    if self.config.DEBUG_MODE:
                        show_message("자동 시작 상태", "자동 시작 등록에 실패했습니다.", QtWidgets.QMessageBox.Warning)
                    logging.error("자동 시작 상태 확인: 등록 실패")
                    return False
                
        except Exception as e:
            logging.error(f"자동 시작 상태 확인 실패: {e}")
            if self.config.DEBUG_MODE:
                show_message("오류", f"자동 시작 상태 확인에 실패했습니다.\n{str(e)}", QtWidgets.QMessageBox.Critical)
            return False

def main():
    if os.name == "nt" and not is_admin():
        QtWidgets.QMessageBox.critical(None, "권한 오류", "이 프로그램은 반드시 '관리자 권한으로 실행'해야 합니다.")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        sys.exit(0)
    
    try:
        # 단일 인스턴스 보장 (중복 실행 방지)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # 이미 실행 중인지 확인
            sock.bind(('localhost', 45678))
        except socket.error:
            # 이미 실행 중이면 경고 후 종료
            QtWidgets.QMessageBox.warning(None, "중복 실행", "프로그램이 이미 실행 중입니다.")
            sys.exit(0)
        
        # 설정 파일과 도메인 목록 초기화
        config = Config()
        download_icon()
        
        # 자동 시작 프로그램 확인 및 복구
        check_and_restore_autostart()
        
        # 기기 인증 상태 확인
        machine_auth = MachineAuth()
        if not os.path.exists(AUTHORIZED_MACHINES_FILE):
            # 첫 실행이면 기본 인증 설정
            machine_auth.authorize_machine(config.MACHINE_ID, config.MACHINE_NAME)
            config.config["AUTHORIZED_MACHINE"] = True
            config._save_config()
        
        # 도메인 매니저 초기화 - 프로그램 시작 시 도메인 목록 로드
        domain_manager = DomainManager()
        global AI_DOMAINS
        AI_DOMAINS = domain_manager.get_domains()
        
        # Qt 애플리케이션 초기화
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # 트레이 아이콘 생성
        icon = QtGui.QIcon(config.ICON_PATH)
        tray = TrayApp(icon)
        tray.show()
        
        # 설정 파일과 도메인 목록 파일 보호
        if os.path.exists(CONFIG_FILE):
            try:
                FILE_ATTRIBUTE_HIDDEN = 0x02
                FILE_ATTRIBUTE_SYSTEM = 0x04
                FILE_ATTRIBUTE_READONLY = 0x01
                ctypes.windll.kernel32.SetFileAttributesW(
                    CONFIG_FILE, 
                    FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                )
            except Exception as e:
                logging.error(f"설정 파일 보호 실패: {e}")
                
        domain_file = "ai_domains.json"
        if os.path.exists(domain_file):
            try:
                FILE_ATTRIBUTE_HIDDEN = 0x02
                FILE_ATTRIBUTE_SYSTEM = 0x04
                FILE_ATTRIBUTE_READONLY = 0x01
                ctypes.windll.kernel32.SetFileAttributesW(
                    domain_file, 
                    FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                )
            except Exception as e:
                logging.error(f"도메인 파일 보호 실패: {e}")
                
        # 인증 파일 보호
        if os.path.exists(AUTHORIZED_MACHINES_FILE):
            try:
                FILE_ATTRIBUTE_HIDDEN = 0x02
                FILE_ATTRIBUTE_SYSTEM = 0x04
                FILE_ATTRIBUTE_READONLY = 0x01
                ctypes.windll.kernel32.SetFileAttributesW(
                    AUTHORIZED_MACHINES_FILE, 
                    FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_READONLY
                )
            except Exception as e:
                logging.error(f"인증 파일 보호 실패: {e}")
        
        app.setQuitOnLastWindowClosed(False)
        logging.info("프로그램 시작")
        
        # 초기 차단 확인
        if not os.path.exists("first_run.marker"):
            # 첫 실행이면 안내 메시지 표시
            show_message(
                "AI 사이트 차단 프로그램", 
                "AI 사이트 차단 프로그램이 자동으로 시작됩니다.\n이 프로그램은 Windows 시작 시 자동으로 실행됩니다."
            )
            try:
                with open("first_run.marker", "w") as f:
                    f.write(str(time.time()))
                # 마커 파일도 숨김 처리
                ctypes.windll.kernel32.SetFileAttributesW(
                    "first_run.marker", 
                    FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
                )
            except Exception as e:
                logging.error(f"첫 실행 마커 생성 실패: {e}")
        
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"프로그램 실행 중 치명적 오류 발생: {e}")
        show_message("치명적 오류", f"프로그램 실행 중 오류가 발생했습니다.\n{str(e)}", QtWidgets.QMessageBox.Critical)
        sys.exit(1)

if __name__ == "__main__":
    main()
