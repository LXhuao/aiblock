import os
import sys
import win32api
import win32security

BLOCK_MARK = "# === AI BLOCK START ==="
UNBLOCK_MARK = "# === AI BLOCK END ==="

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

def unblock_ai():
    hosts_path = get_hosts_path()
    
    try:
        with open(hosts_path, 'r') as f:
            lines = f.readlines()
        
        start_idx = -1
        end_idx = -1
        
        for i, line in enumerate(lines):
            if BLOCK_MARK in line:
                start_idx = i
            elif UNBLOCK_MARK in line:
                end_idx = i
                
        if start_idx != -1 and end_idx != -1:
            del lines[start_idx:end_idx + 1]
            
            with open(hosts_path, 'w') as f:
                f.writelines(lines)
            
            os.system('ipconfig /flushdns')
            print("AI sites have been unblocked.")
        else:
            print("No AI blocks found in hosts file.")
            
    except Exception as e:
        print(f"Error unblocking AI: {e}")

def main():
    run_as_admin()
    unblock_ai()

if __name__ == "__main__":
    main() 