#!/usr/bin/env python3
"""
ORBITAL MAP EXTRACTOR - Pro Edition
Next-Gen GIS Matrix downloader engine interface.
"""
import tkinter as tk
from gui import MapDownloaderGUI

def main():
    root = tk.Tk()
    
    # فعال‌سازی هماهنگی شتاب‌دهنده رندرینگ DPI بالا برای جلوگیری از تاری پنجره در ویندوز
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
        
    app = MapDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()