# 🔒 Secure HTTPS QR File Share

A Python desktop application that allows you to securely share files and messages over your local network. Simply select a file, scan the dynamically generated QR code with your phone, and securely view or download the content.

## ✨ Features
* **Zero-Setup Network Sharing:** Automatically detects your local IP and spins up a web server.
* **Dynamic QR Code Generation:** Scan to instantly connect to the server.
* **Time-Based One-Time Password (TOTP):** 30-second rotating PIN required to view or download files, preventing unauthorized access on your network.
* **On-the-fly SSL Certificates:** Generates a temporary HTTPS certificate using `trustme` to encrypt the file transfer.
* **Modern GUI:** Built with `customtkinter` for a sleek, dark-mode ready interface.

## 🛠️ Installation

1. Clone this repository to your local machine:
   ```bash
   git clone [https://github.com/Karna0089/vibe-coded-python-scripts.git](https://github.com/Karna0089/vibe-coded-python-scripts.git)

2. Navigate to the project folder:

   ```bash
   cd vibe-coded-python-scripts
3. Install the required libraries using the requirements file:

   ```bash
   pip install -r requirements.txt
---Usage---
Run the application (in terminal):

      ```bash
      python app.py
(Optional) Type a custom message or click Choose File to select a document to share.

Click ▶ Start Sharing.

A 6-digit PIN and a QR code will appear on your screen.

Scan the QR code with your mobile device, enter the PIN, and securely access your files!
