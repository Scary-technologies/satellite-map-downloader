import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import os
import tkintermapview
from map_downloader import download_map, calculate_tiles_info

class MapDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ORBITAL MAP EXTRACTOR v2.0")
        self.root.geometry("1200x800")
        self.root.minsize(1100, 750)
        
        # پالت تیره و مدرن کاملاً یکپارچه و بومی
        self.bg_main = '#0f0f16'
        self.bg_card = '#171724'
        self.bg_input = '#232335'
        self.accent = '#bb86fc'
        self.accent_neon = '#03dac6'
        self.fg_light = '#e1e1e6'
        self.fg_dim = '#a1a1b3'
        
        self.root.configure(bg=self.bg_main)
        
        # متغیرهای کنترل برنامه
        self.lat_var = tk.StringVar(value="36.2972")
        self.lon_var = tk.StringVar(value="59.6061")
        self.radius_var = tk.StringVar(value="1.5")
        self.zoom_var = tk.IntVar(value=17)
        self.engine_var = tk.StringVar(value="Google Satellite")
        self.format_var = tk.StringVar(value="webp")
        self.quality_var = tk.IntVar(value=90)
        self.width_var = tk.IntVar(value=2500)
        self.output_file = tk.StringVar(value=os.path.abspath("orbital_map.webp"))
        
        self.is_downloading = False
        self.current_marker = None
        self.cancel_event = threading.Event()
        
        self._build_futuristic_ui()
        
        # رندر اولیه موقعیت نقشه
        self.map_widget.set_position(float(self.lat_var.get()), float(self.lon_var.get()))
        self.map_widget.set_zoom(13)
        self._update_map_marker()
        self._recalc_matrix_metrics()

    def _build_futuristic_ui(self):
        # هدر بالایی برنامه
        top_bar = tk.Frame(self.root, bg=self.bg_card, height=60)
        top_bar.pack(fill='x', side='top')
        top_bar.pack_propagate(False)
        
        tk.Label(top_bar, text="🛰️ ORBITAL MAP EXTRACTOR", font=('Segoe UI', 15, 'bold'), bg=self.bg_card, fg=self.accent).pack(side='left', padx=20, pady=12)
        self.global_status = tk.Label(top_bar, text="SYSTEM STATUS: IDLE", font=('Segoe UI', 9, 'bold'), bg=self.bg_card, fg=self.accent_neon)
        self.global_status.pack(side='right', padx=20, pady=15)

        workspace = tk.Frame(self.root, bg=self.bg_main)
        workspace.pack(fill='both', expand=True, padx=15, pady=15)
        
        # سمت چپ: نقشه تعاملی ماهواره‌ای
        left_panel = tk.Frame(workspace, bg=self.bg_main)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        map_container = tk.Frame(left_panel, bg=self.bg_card, bd=0)
        map_container.pack(fill='both', expand=True)
        
        self.map_widget = tkintermapview.TkinterMapView(map_container, corner_radius=12, bg_color=self.bg_card)
        self.map_widget.pack(fill='both', expand=True, padx=2, pady=2)
        self.map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", max_zoom=22)
        self.map_widget.add_left_click_map_command(self._on_map_interaction)
        
        # سمت راست: کنترلر ابزارها و پنل پیشرفته
        right_panel = tk.Frame(workspace, width=380, bg=self.bg_card)
        right_panel.pack(side='right', fill='both', padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # بخش هدر کنترلرها
        ctrl_label = tk.Label(right_panel, text="TARGET SETTINGS", font=('Segoe UI', 11, 'bold'), bg=self.bg_card, fg=self.accent)
        ctrl_label.pack(anchor='w', padx=15, pady=(15, 5))
        
        self._build_primary_inputs(right_panel)
        self._build_advanced_inputs(right_panel)
        self._build_action_gate(right_panel)

    def _build_primary_inputs(self, parent):
        container = tk.Frame(parent, bg=self.bg_card, padx=15)
        container.pack(fill='x', pady=5)
        
        # فیلد Latitude
        f_lat = tk.Frame(container, bg=self.bg_card)
        f_lat.pack(fill='x', pady=4)
        tk.Label(f_lat, text="Latitude:", bg=self.bg_card, fg=self.fg_light, width=12, anchor='w').pack(side='left')
        e_lat = tk.Entry(f_lat, textvariable=self.lat_var, bg=self.bg_input, fg=self.fg_light, insertbackground=self.fg_light, bd=0, relief='flat')
        e_lat.pack(side='right', fill='x', expand=True, ipady=4)
        e_lat.bind("<FocusOut>", lambda e: self._sync_manual_inputs())
        
        # فیلد Longitude
        f_lon = tk.Frame(container, bg=self.bg_card)
        f_lon.pack(fill='x', pady=4)
        tk.Label(f_lon, text="Longitude:", bg=self.bg_card, fg=self.fg_light, width=12, anchor='w').pack(side='left')
        e_lon = tk.Entry(f_lon, textvariable=self.lon_var, bg=self.bg_input, fg=self.fg_light, insertbackground=self.fg_light, bd=0, relief='flat')
        e_lon.pack(side='right', fill='x', expand=True, ipady=4)
        e_lon.bind("<FocusOut>", lambda e: self._sync_manual_inputs())

        # فیلد Radius
        f_rad = tk.Frame(container, bg=self.bg_card)
        f_rad.pack(fill='x', pady=4)
        tk.Label(f_rad, text="Radius (KM):", bg=self.bg_card, fg=self.fg_light, width=12, anchor='w').pack(side='left')
        e_rad = tk.Entry(f_rad, textvariable=self.radius_var, bg=self.bg_input, fg=self.fg_light, insertbackground=self.fg_light, bd=0, relief='flat')
        e_rad.pack(side='right', fill='x', expand=True, ipady=4)
        e_rad.bind("<KeyRelease>", lambda e: self._recalc_matrix_metrics())
        
        # فیلد Zoom Level
        f_zoom = tk.Frame(container, bg=self.bg_card)
        f_zoom.pack(fill='x', pady=4)
        tk.Label(f_zoom, text="Zoom Level:", bg=self.bg_card, fg=self.fg_light, width=12, anchor='w').pack(side='left')
        e_zoom = tk.Entry(f_zoom, textvariable=self.zoom_var, bg=self.bg_input, fg=self.fg_light, insertbackground=self.fg_light, bd=0, relief='flat')
        e_zoom.pack(side='right', fill='x', expand=True, ipady=4)
        e_zoom.bind("<KeyRelease>", lambda e: self._recalc_matrix_metrics())

    def _build_advanced_inputs(self, parent):
        container = tk.Frame(parent, bg=self.bg_card, padx=15)
        container.pack(fill='x', pady=5)
        
        # فیلد موتور نقشه (Engine)
        f_eng = tk.Frame(container, bg=self.bg_card)
        f_eng.pack(fill='x', pady=4)
        tk.Label(f_eng, text="Engine:", bg=self.bg_card, fg=self.fg_light, width=12, anchor='w').pack(side='left')
        
        # از OptionMenu استاندارد استفاده شده تا از کرش تولکیت جلوگیری شود
        opt_eng = tk.OptionMenu(f_eng, self.engine_var, "Google Satellite", "Esri Satellite", "OpenStreetMap", command=self._change_preview_map_layer)
        opt_eng.config(bg=self.bg_input, fg=self.fg_light, activebackground=self.bg_input, activeforeground=self.fg_light, bd=0, highlightthickness=0)
        opt_eng["menu"].config(bg=self.bg_input, fg=self.fg_light, activebackground=self.accent, bd=0)
        opt_eng.pack(side='right', fill='x', expand=True)
        
        # فرمت تصویر خروجی
        f_fmt = tk.Frame(container, bg=self.bg_card)
        f_fmt.pack(fill='x', pady=4)
        tk.Label(f_fmt, text="Format:", bg=self.bg_card, fg=self.fg_light, width=12, anchor='w').pack(side='left')
        opt_fmt = tk.OptionMenu(f_fmt, self.format_var, "webp", "png", "jpg", command=self._adjust_extension)
        opt_fmt.config(bg=self.bg_input, fg=self.fg_light, activebackground=self.bg_input, activeforeground=self.fg_light, bd=0, highlightthickness=0)
        opt_fmt["menu"].config(bg=self.bg_input, fg=self.fg_light, activebackground=self.accent, bd=0)
        opt_fmt.pack(side='right', fill='x', expand=True)

        # رزولوشن هدف
        f_wd = tk.Frame(container, bg=self.bg_card)
        f_wd.pack(fill='x', pady=4)
        tk.Label(f_wd, text="Width (px):", bg=self.bg_card, fg=self.fg_light, width=12, anchor='w').pack(side='left')
        e_wd = tk.Entry(f_wd, textvariable=self.width_var, bg=self.bg_input, fg=self.fg_light, insertbackground=self.fg_light, bd=0, relief='flat')
        e_wd.pack(side='right', fill='x', expand=True, ipady=4)

        # باکس مانیتور تلمتری اطلاعات
        self.telemetry_box = tk.Label(container, text="Analyzing coordinates...", bg='#1e1e2f', fg=self.accent_neon, 
                                      font=('Consolas', 9), justify='left', anchor='w', padx=10, pady=10)
        self.telemetry_box.pack(fill='x', pady=15)

    def _build_action_gate(self, parent):
        gate = tk.Frame(parent, bg=self.bg_card, padx=15)
        gate.pack(fill='x', side='bottom', pady=15)
        
        tk.Label(gate, text="OUTPUT DESTINATION", font=('Segoe UI', 9, 'bold'), bg=self.bg_card, fg=self.accent).pack(anchor='w', pady=2)
        
        f_browse = tk.Frame(gate, bg=self.bg_card)
        f_browse.pack(fill='x', pady=4)
        e_file = tk.Entry(f_browse, textvariable=self.output_file, bg=self.bg_input, fg=self.fg_light, insertbackground=self.fg_light, bd=0, relief='flat')
        e_file.pack(side='left', fill='x', expand=True, ipady=4, padx=(0, 5))
        
        btn_browse = tk.Button(f_browse, text="📂", bg=self.bg_input, fg=self.fg_light, activebackground=self.accent, bd=0, relief='flat', command=self._trigger_file_browser)
        btn_browse.pack(side='right', ipadx=5, ipady=2)
        
        # پروگرس‌بار بومی با استفاده از کانفینگ کامپوننت canvas بدون نیاز به المان آسیب‌پذیر ttk
        self.progress_canvas = tk.Canvas(gate, height=8, bg=self.bg_input, bd=0, highlightthickness=0)
        self.progress_canvas.pack(fill='x', pady=(15, 5))
        self.progress_bar_rect = self.progress_canvas.create_rectangle(0, 0, 0, 8, fill=self.accent_neon, width=0)
        
        self.live_status = tk.Label(gate, text="Ready for deployment", bg=self.bg_card, fg=self.fg_dim, font=('Segoe UI', 9, 'italic'))
        self.live_status.pack(anchor='w', pady=2)
        
        # دکمه اکشن نهایی - پارامتر نامعتبر padding در پایتون ۳.۱۳ با ipadx و ipady بومی جایگزین شد
        self.action_btn = tk.Button(gate, text="INITIALIZE DOWNLOAD", bg=self.accent, fg='#000000', 
                                    font=('Segoe UI', 11, 'bold'), activebackground=self.accent_neon,
                                    borderwidth=0, relief='flat', command=self._orchestrate_download)
        self.action_btn.pack(fill='x', pady=(10, 5), ipadx=10, ipady=8)

    def _on_map_interaction(self, coords):
        self.lat_var.set(f"{coords[0]:.6f}")
        self.lon_var.set(f"{coords[1]:.6f}")
        self._update_map_marker()
        self._recalc_matrix_metrics()

    def _update_map_marker(self):
        try:
            lat, lon = float(self.lat_var.get()), float(self.lon_var.get())
            if self.current_marker:
                self.current_marker.delete()
            self.current_marker = self.map_widget.set_marker(lat, lon, text="🎯 TARGET MATRIX")
        except ValueError: pass

    def _sync_manual_inputs(self):
        try:
            lat, lon = float(self.lat_var.get()), float(self.lon_var.get())
            self.map_widget.set_position(lat, lon)
            self._update_map_marker()
            self._recalc_matrix_metrics()
        except ValueError:
            messagebox.showerror("Error", "Invalid Coordinate Parameters.")

    def _change_preview_map_layer(self, val=None):
        eng = self.engine_var.get()
        if eng == "Google Satellite":
            self.map_widget.set_tile_server("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}")
        elif eng == "OpenStreetMap":
            self.map_widget.set_tile_server("https://tile.openstreetmap.org/{z}/{x}/{y}.png")
        else:
            self.map_widget.set_tile_server("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}")

    def _recalc_matrix_metrics(self, event=None):
        try:
            lat = float(self.lat_var.get())
            lon = float(self.lon_var.get())
            rad = float(self.radius_var.get())
            zoom = int(self.zoom_var.get())
            
            tiles, w, h = calculate_tiles_info(lat, lon, rad, zoom)
            est_size = (tiles * 0.035) if self.format_var.get() == 'webp' else (tiles * 0.06)
            
            metrics = f"📊 Matrix Estimation:\n" \
                      f"  • Total Map Tiles: {tiles}\n" \
                      f"  • Native Stitch Size: {w} × {h} px\n" \
                      f"  • Predicted Payload: ~{est_size:.2f} MB"
            self.telemetry_box.config(text=metrics, fg=self.accent_neon)
        except Exception:
            self.telemetry_box.config(text="Invalid metrics compilation settings.", fg="#ff5555")

    def _adjust_extension(self, val=None):
        fmt = self.format_var.get()
        curr = self.output_file.get()
        base = os.path.splitext(curr)[0]
        self.output_file.set(f"{base}.{fmt}")
        self._recalc_matrix_metrics()

    def _trigger_file_browser(self):
        fmt = self.format_var.get()
        path = filedialog.asksaveasfilename(defaultextension=f".{fmt}", filetypes=[(f"{fmt.upper()} asset", f"*.{fmt}")])
        if path: self.output_file.set(path)

    def _orchestrate_download(self):
        if self.is_downloading:
            self.cancel_event.set()
            self.live_status.config(text="Sending termination code...")
            return
            
        try:
            lat, lon = float(self.lat_var.get()), float(self.lon_var.get())
            rad, zoom = float(self.radius_var.get()), int(self.zoom_var.get())
            qty, wd = self.quality_var.get(), int(self.width_var.get())
        except ValueError:
            messagebox.showerror("Validation Error", "Check your input vectors - numerical breakdown failed.")
            return

        self.is_downloading = True
        self.cancel_event.clear()
        self.action_btn.config(text="ABORT OPERATION", bg="#ff5555", fg="#ffffff")
        self.global_status.config(text="SYSTEM STATUS: ENGAGED", fg="#ff5555")
        
        threading.Thread(
            target=self._execution_thread,
            args=(lat, lon, rad, zoom, self.output_file.get(), wd, qty, self.engine_var.get()),
            daemon=True
        ).start()

    def _execution_thread(self, lat, lon, rad, zoom, path, wd, qty, eng):
        try:
            res = download_map(
                center_lat=lat, center_lon=lon, radius_km=rad, zoom=zoom,
                output_file=path, max_workers=16, target_width=wd, quality=qty,
                engine=eng, progress_callback=self._pipeline_callback, cancel_event=self.cancel_event
            )
            self.root.after(0, self._finalize_operation, res)
        except Exception as e:
            self.root.after(0, self._handle_crash, str(e))

    def _pipeline_callback(self, pct, msg):
        self.root.after(0, lambda: self._update_progress_ui(pct, msg))

    def _update_progress_ui(self, pct, msg):
        self.live_status.config(text=msg)
        width = self.progress_canvas.winfo_width()
        new_w = (pct / 100) * width
        self.progress_canvas.coords(self.progress_bar_rect, 0, 0, new_w, 8)

    def _finalize_operation(self, res):
        self.is_downloading = False
        self.action_btn.config(text="INITIALIZE DOWNLOAD", bg=self.accent, fg='#000000')
        self.global_status.config(text="SYSTEM STATUS: IDLE", fg=self.accent_neon)
        self._update_progress_ui(100, "Extraction successful.")
        
        msg = f"🛰️ Payload Matrix Secured!\n\n" \
              f"• File: {res['file_path']}\n" \
              f"• Scale: {res['size_mb']:.2f} MB\n" \
              f"• Resolution: {res['dimensions'][0]}×{res['dimensions'][1]} px\n" \
              f"• Core Engine: {res['engine']}"
        messagebox.showinfo("Extraction Complete", msg)

    def _handle_crash(self, err_msg):
        self.is_downloading = False
        self.action_btn.config(text="INITIALIZE DOWNLOAD", bg=self.accent, fg='#000000')
        self.global_status.config(text="SYSTEM STATUS: CRIT_ERR", fg="#ff5555")
        self._update_progress_ui(0, "Operation failed.")
        messagebox.showerror("System Interruption", f"Process aborted:\n{err_msg}")