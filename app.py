from urllib.parse import parse_qs, urlparse
import os
import socket
import threading
import qrcode
import ssl
import trustme
import shutil
import mimetypes
import time
import pyotp
import uuid
from urllib.parse import parse_qs
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

PORT = 8555

class HTTPSQRFileSenderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Secure HTTPS QR Share")
        self.geometry("450x850") 
        self.resizable(False, False)
        
        self.server_thread = None
        self.httpd = None
        self.selected_file_path = None
        
        # Security State
        self.totp_secret = pyotp.random_base32()
        self.totp = pyotp.TOTP(self.totp_secret)
        self.valid_sessions = set()
        
        empty_pil = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        self.empty_image = ctk.CTkImage(light_image=empty_pil, dark_image=empty_pil, size=(1, 1))
        self.current_qr_image = self.empty_image

        # --- UI ELEMENTS ---
        self.title_label = ctk.CTkLabel(self, text="🔒 Secure QR Share", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(20, 10))
        
        self.msg_label = ctk.CTkLabel(self, text="Custom Message (Optional):", font=ctk.CTkFont(weight="bold"))
        self.msg_label.pack()
        self.msg_box = ctk.CTkTextbox(self, width=300, height=70, border_width=2)
        self.msg_box.pack(pady=(0, 10))
        
        self.select_btn = ctk.CTkButton(self, text="Choose File (Optional)", command=self.select_file, fg_color="#454545", hover_color="#2b2b2b")
        self.select_btn.pack(pady=5)
        self.file_label = ctk.CTkLabel(self, text="No file selected", text_color="gray")
        self.file_label.pack(pady=(0, 10))
        
        # PIN DISPLAY
        self.pin_label = ctk.CTkLabel(self, text="🔑 PIN: ---", font=ctk.CTkFont(size=18, weight="bold"), text_color="#d4a017")
        self.pin_label.pack(pady=10)
        
        self.start_btn = ctk.CTkButton(self, text="▶ Start Sharing", command=self.start_server_pipeline, height=40, fg_color="#228B22", hover_color="#186118")
        self.start_btn.pack(pady=5)
        
        self.qr_frame = ctk.CTkLabel(self, text="Add a file/message and start sharing!", width=250, height=250, fg_color=("lightgray", "#2b2b2b"), corner_radius=10)
        self.qr_frame.pack(pady=10)
        
        self.status_label = ctk.CTkLabel(self, text="Status: Idle", text_color="#1f538d", font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(pady=5)

        self.stop_btn = ctk.CTkButton(self, text="Stop Sharing", fg_color="#A30000", hover_color="#7A0000", command=self.stop_server)
        
        # Live Activity Log
        self.log_label = ctk.CTkLabel(self, text="Live Activity Log:", font=ctk.CTkFont(weight="bold"))
        self.log_label.pack(pady=(5,0))
        self.log_box = ctk.CTkTextbox(self, width=400, height=100, border_width=2, state="disabled", fg_color="#1a1a1a", text_color="#00ff00")
        self.log_box.pack(pady=(0, 10))
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start the UI loop for the TOTP timer
        self.update_totp_ui()

    def update_totp_ui(self):
        if self.httpd:
            current_pin = self.totp.now()
            remaining_seconds = 30 - (int(time.time()) % 30)
            self.pin_label.configure(text=f"🔑 PIN: {current_pin} ({remaining_seconds}s)", text_color="#d4a017")
        else:
            self.pin_label.configure(text="🔑 PIN: ---", text_color="gray")
            
        self.after(1000, self.update_totp_ui)

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def select_file(self):
        file_path = filedialog.askopenfilename(title="Select File to Share")
        if file_path:
            self.selected_file_path = file_path
            file_name = os.path.basename(self.selected_file_path)
            self.file_label.configure(text=f"Ready to share: {file_name}", text_color=("black", "white"))

    def generate_qr_image(self, url):
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        raw_pil_img = qr.make_image(fill_color="black", back_color="white").get_image()
        return ctk.CTkImage(light_image=raw_pil_img, dark_image=raw_pil_img, size=(250, 250))

    def add_log(self, message):
        self.after(0, self._safe_add_log, message)
        
    def _safe_add_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end") 
        self.log_box.configure(state="disabled")

    def get_login_html(self, error_msg=""):
        return f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, sans-serif; padding: 20px; text-align: center; background: #1a1a1a; color: white; }}
                .container {{ max-width: 400px; margin: 10vh auto; background: #2b2b2b; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
                input[type="text"] {{ width: 100%; padding: 12px; margin: 15px 0; border-radius: 8px; border: none; font-size: 20px; text-align: center; letter-spacing: 5px; }}
                input[type="submit"] {{ background: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 8px; font-size: 18px; cursor: pointer; width: 100%; }}
                .error {{ color: #ff4d4d; font-weight: bold; margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🔒 Security Check</h2>
                <p>Please enter the 6-digit PIN displayed on the host machine.</p>
                {f'<div class="error">{error_msg}</div>' if error_msg else ''}
                <form action="/auth" method="POST">
                    <input type="text" name="pin" maxlength="6" autocomplete="off" placeholder="------" required autofocus>
                    <input type="submit" value="Unlock Content">
                </form>
            </div>
        </body>
        </html>
        """

    def start_server_pipeline(self):
        self.stop_server()
        
        current_msg = self.msg_box.get("1.0", "end-1c").strip()
        current_file = self.selected_file_path
        
        if not current_msg and not current_file:
            self.status_label.configure(text="Please add a message or file first!", text_color="#A30000")
            return

        # Generate a fresh secret and clear old sessions every time the server starts
        self.totp_secret = pyotp.random_base32()
        self.totp = pyotp.TOTP(self.totp_secret)
        self.valid_sessions.clear()

        local_ip = self.get_local_ip()
        download_url = f"https://{local_ip}:{PORT}/"
        
        self.status_label.configure(text="⏳ Generating secure certificate...", text_color="#d4a017")
        self.current_qr_image = self.generate_qr_image(download_url)
        self.qr_frame.configure(image=self.current_qr_image, text="")
        self.add_log("--- Server Started ---")
        self.update() 
        
        gui_app = self 

        class CustomHandler(BaseHTTPRequestHandler):
            def check_auth(self):
                cookie_header = self.headers.get('Cookie')
                if cookie_header:
                    c = cookies.SimpleCookie(cookie_header)
                    if 'session' in c and c['session'].value in gui_app.valid_sessions:
                        return True
                return False

            def log_visit(self, action):
                client_ip = self.client_address[0] 
                user_agent = self.headers.get('User-Agent', 'Unknown Device')
                device = "Unknown"
                if "iPhone" in user_agent: device = "iPhone"
                elif "Android" in user_agent: device = "Android"
                elif "Windows" in user_agent: device = "Windows PC"
                elif "Macintosh" in user_agent: device = "Mac"
                gui_app.add_log(f"🌐 IP: {client_ip} | 📱 {device} | ⚡ {action}")

            def do_POST(self):
                if self.path == '/auth':
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length).decode('utf-8')
                    parsed_data = parse_qs(post_data)
                    submitted_pin = parsed_data.get('pin', [''])[0]

                    if gui_app.totp.verify(submitted_pin):
                        # Generate a secure session ID
                        session_id = str(uuid.uuid4())
                        gui_app.valid_sessions.add(session_id)
                        
                        gui_app.add_log(f"✅ Auth Success: {self.client_address[0]}")
                        
                        # Redirect back to home with the session cookie
                        self.send_response(303)
                        self.send_header('Location', '/')
                        cookie = cookies.SimpleCookie()
                        cookie['session'] = session_id
                        cookie['session']['path'] = '/'
                        self.send_header('Set-Cookie', cookie.output(header='', sep=''))
                        self.end_headers()
                    else:
                        gui_app.add_log(f"❌ Auth Failed: {self.client_address[0]}")
                        
                        # Send back the login page with an error
                        self.send_response(200)
                        self.send_header("Content-type", "text/html; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(gui_app.get_login_html(error_msg="Invalid or expired PIN!").encode('utf-8'))
                else:
                    self.send_error(404, "Not Found")

            def do_GET(self):
                is_auth = self.check_auth()

                if self.path == '/':
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    
                    if not is_auth:
                        self.log_visit("Visited Login Page")
                        self.wfile.write(gui_app.get_login_html().encode('utf-8'))
                        return
                    
                    self.log_visit("Viewed Secure Content")
                    
                    # Generate a timestamp to bust aggressive browser caching
                    cache_buster = int(time.time())
                    
                    embed_html = ""
                    if current_file:
                        mime_type, _ = mimetypes.guess_type(current_file)
                        if current_file.lower().endswith('.pdf'):
                            mime_type = 'application/pdf'
                        mime_type = mime_type or ""
                        
                        view_url = f"/view?cb={cache_buster}"
                        
                        if mime_type.startswith("image/"):
                            embed_html = f'<img src="{view_url}" style="max-width: 100%; border-radius: 8px;">'
                        elif mime_type.startswith("video/"):
                            embed_html = f'<video controls style="max-width: 100%; border-radius: 8px;"><source src="{view_url}" type="{mime_type}">Browser unsupported.</video>'
                        elif mime_type.startswith("audio/"):
                            embed_html = f'<audio controls style="width: 100%;"><source src="{view_url}" type="{mime_type}">Browser unsupported.</audio>'
                        elif mime_type == "application/pdf":
                            # Iframes are generally better supported for native PDF viewing than <object> tags across mobile/desktop
                            embed_html = f'<iframe src="{view_url}" style="width: 100%; height: 75vh; border: 2px solid #555; border-radius: 8px; background: white;"></iframe>'
                        else:
                            embed_html = f'<iframe src="{view_url}" style="width: 100%; height: 60vh; border: 2px solid #555; border-radius: 8px; background: white;"></iframe>'
                    
                    html = f"""
                    <html>
                    <head>
                        <meta name="viewport" content="width=device-width, initial-scale=1">
                        <style>
                            body {{ font-family: -apple-system, sans-serif; padding: 20px; text-align: center; background: #1a1a1a; color: white; margin: 0; }}
                            .container {{ max-width: 600px; margin: auto; padding-bottom: 30px; }}
                            .card {{ background: #2b2b2b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin-bottom: 20px; }}
                            h3 {{ color: #ffffff; margin-top: 0; border-bottom: 1px solid #444; padding-bottom: 10px; }}
                            .msg-text {{ font-size: 18px; word-wrap: break-word; text-align: left; background: #222; padding: 15px; border-radius: 8px; border-left: 4px solid #228B22; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h2>🔒 Secure Share</h2>
                            {f'<div class="card"><h3>💬 Message</h3><div class="msg-text">{current_msg}</div></div>' if current_msg else ''}
                            {f'<div class="card"><h3>📄 Document Viewer</h3>{embed_html}<br><br><a href="/view" download style="color: #228B22; text-decoration: none; font-weight: bold;">[ Force Download File ]</a></div>' if current_file else ''}
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode('utf-8'))
                    
                elif urlparse(self.path).path == '/view' and current_file:
                    if not is_auth:
                        self.send_error(403, "Forbidden - Unauthorized Access")
                        return

                    self.log_visit(f"Loaded File: {os.path.basename(current_file)}")
                    try:
                        with open(current_file, 'rb') as f:
                            self.send_response(200)
                            
                            mime_type, _ = mimetypes.guess_type(current_file)
                            if current_file.lower().endswith('.pdf'):
                                mime_type = 'application/pdf'
                            if mime_type is None:
                                mime_type = 'application/octet-stream'
                                
                            self.send_header("Content-type", mime_type)
                            
                            # Strictly enforce inline rendering without a filename prompt
                            self.send_header("Content-Disposition", "inline")
                            
                            # Force the browser NOT to cache this file stream
                            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                            self.send_header("Pragma", "no-cache")
                            self.send_header("Expires", "0")
                            
                            fs = os.fstat(f.fileno())
                            self.send_header("Content-Length", str(fs.st_size))
                            self.end_headers()
                            
                            shutil.copyfileobj(f, self.wfile)
                    except ConnectionError:
                        pass
                    except Exception:
                        try:
                            self.send_error(404, "File not found")
                        except ConnectionError:
                            pass
                else:
                    self.send_error(404, "Not found")

            def log_message(self, format, *args):
                pass 

        def run_server():
            try:
                with ThreadingHTTPServer(("", PORT), CustomHandler) as self.httpd:
                    ca = trustme.CA()
                    server_cert = ca.issue_cert(local_ip)
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    with server_cert.private_key_and_cert_chain_pem.tempfile() as cert_path:
                        ssl_context.load_cert_chain(cert_path)
                    
                    self.httpd.socket = ssl_context.wrap_socket(self.httpd.socket, server_side=True)
                    
                    self.status_label.configure(text="🔒 HTTPS Server Online", text_color="#228B22")
                    self.start_btn.pack_forget() 
                    self.stop_btn.pack(pady=5)
                    self.httpd.serve_forever() 
            except (OSError, ValueError):
                pass
            except Exception as e:
                print(f"Server Error: {e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop_server(self):
        if self.httpd:
            server_to_kill = self.httpd
            self.httpd = None 
            self.valid_sessions.clear()
            
            def kill_task():
                try:
                    server_to_kill.shutdown()
                    server_to_kill.server_close()
                except Exception:
                    pass
            
            threading.Thread(target=kill_task, daemon=True).start()
            self.add_log("--- Server Stopped ---")
            
        self.status_label.configure(text="Status: Idle", text_color="#1f538d")
        self.qr_frame.configure(image=self.empty_image, text="Add a file/message and start sharing!")
        self.current_qr_image = self.empty_image
        self.stop_btn.pack_forget()
        self.start_btn.pack(pady=5)

    def on_closing(self):
        self.stop_server()
        self.destroy()

if __name__ == "__main__":
    app = HTTPSQRFileSenderApp()
    app.mainloop()