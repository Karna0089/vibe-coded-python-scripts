# 🔒 Secure HTTPS QR File Share

A Python desktop application that allows you to securely share files and messages over your local network. Simply select a file, scan the dynamically generated QR code with your phone, and securely download the content.

## ✨ Features
* **Zero-Setup Network Sharing:** Automatically detects your local IP and spins up a web server.
* **Dynamic QR Code Generation:** Scan to instantly connect to the server.
* **Time-Based One-Time Password (TOTP):** 30-second rotating PIN required to view or download files, preventing unauthorized access on your network.
* **On-the-fly SSL Certificates:** Generates a temporary HTTPS certificate using `trustme` to encrypt the file transfer.
* **Anti-Caching PDF Viewer:** Safely embeds PDFs directly into the mobile browser while aggressively busting browser caches to prevent forced downloads.
* **Modern GUI:** Built with `customtkinter` for a sleek, dark-mode ready interface.

## 🛠️ Installation

1. Clone this repository to your local machine:
   ```bash
   git clone [https://github.com/Karna0089/vibe-coded-python-scripts.git](https://github.com/Karna0089/vibe-coded-python-scripts.git)
