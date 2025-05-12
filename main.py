import os
import sys
import time
import threading
import pystray
from PIL import Image
import psutil
import win32con
import win32api
import win32security
import win32process

BLOCK_MARK = "# === AI BLOCK START ==="
UNBLOCK_MARK = "# === AI BLOCK END ==="

AI_DOMAINS = [
    "chat.openai.com",
    "platform.openai.com",
    "claude.ai",
    "bard.google.com",
    "copilot.microsoft.com",
    "github.copilot.com",
    "midjourney.com",
    "labs.openai.com",
    "beta.openai.com",
    "anthropic.com",
    "notion.ai",
    "synthesia.io",
    "heygen.com",
    "stability.ai",
    "replicate.com",
    "huggingface.co",
    "cohere.ai",
    "deepl.com",
    "jasper.ai",
    "copy.ai",
    "writesonic.com",
    "grammarly.com",
    "perplexity.ai",
    "poe.com",
    "phind.com",
    "you.com",
    "codeium.com",
    "tabnine.com",
    "khanmigo.com",
    "blackbox.ai",
    "deepmind.com",
    "runwayml.com",
    "leonardo.ai",
    "dreamstudio.ai",
    "firefly.adobe.com",
]

def is_admin():
    try:
        return win32security.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        params = ' '.join(sys.argv[1:])
        win32api.ShellExecute(0, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit()

def get_hosts_path():
    return os.path.join(os.environ['WINDIR'], 'System32', 'drivers', 'etc', 'hosts')

def is_blocked():
    try:
        with open(get_hosts_path(), 'r') as f:
            content = f.read()
            return BLOCK_MARK in content
    except:
        return False

def block_ai():
    hosts_path = get_hosts_path()
    
    try:
        with open(hosts_path, 'r') as f:
            content = f.read()
            
        if BLOCK_MARK in content:
            return
            
        block_content = [f"\n{BLOCK_MARK}"]
        for domain in AI_DOMAINS:
            block_content.append(f"127.0.0.1 {domain}")
            block_content.append(f"127.0.0.1 www.{domain}")
        block_content.append(UNBLOCK_MARK)
        
        with open(hosts_path, 'a') as f:
            f.write('\n'.join(block_content))
            
        flush_dns()
    except Exception as e:
        print(f"Error blocking AI: {e}")

def flush_dns():
    os.system('ipconfig /flushdns')

def create_tray_icon():
    icon_data = Image.new('RGB', (64, 64), 'red')
    icon = pystray.Icon("AI Blocker", icon_data, "AI Blocker")
    
    def stop_blocking(icon, item):
        icon.stop()
        sys.exit()
        
    icon.menu = pystray.Menu(
        pystray.MenuItem("Exit", stop_blocking)
    )
    return icon

def main():
    run_as_admin()
    
    icon = create_tray_icon()
    
    def blocking_thread():
        while True:
            block_ai()
            time.sleep(10)
    
    thread = threading.Thread(target=blocking_thread, daemon=True)
    thread.start()
    
    icon.run()

if __name__ == "__main__":
    main() 