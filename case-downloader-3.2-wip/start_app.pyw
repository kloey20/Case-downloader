#!/usr/bin/env python3
import sys
import subprocess
import importlib

# 1. Define the libraries required for the app to run
REQUIRED_PACKAGES = {
    "flask": "flask",
    "webview": "pywebview",
    "selenium": "selenium"
}

def install_and_verify():
    """Checks for missing packages and silently installs them if needed."""
    missing_packages = []
    
    # Check what is currently missing
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing_packages.append(pip_name)
            
    # If anything is missing, install it silently
    if missing_packages:
        try:
            # CREATE_NO_WINDOW (0x08000000) prevents a black console window from flashing on Windows
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *missing_packages],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags
            )
        except Exception as e:
            # If pip installation fails (e.g., no internet connection), we let the user know
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Setup Error", 
                f"Could not automatically install required packages ({', '.join(missing_packages)}).\n\nError: {e}"
            )
            sys.exit(1)

# Run the installation check BEFORE importing app or webview
install_and_verify()

# 2. Now that we guarantee libraries exist, safely import them and launch
import webview
from app import app

if __name__ == '__main__':
    # Creates a native desktop window displaying your Flask app
    webview.create_window('LawPhil Downloader', app, width=600, height=800)
    webview.start()