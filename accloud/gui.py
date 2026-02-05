import os
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from io import BytesIO
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Optional

import json
import httpx
from PIL import Image, ImageTk

from .api import delete_files, get_download_url, get_gcode_info, get_quota, list_files, upload_file, list_printers, get_printer_info_v2, get_projects, send_print_order, send_video_order
from .client import CloudClient
from .image_cache import fetch_image_bytes
from .session_store import (
    DEFAULT_SESSION_PATH,
    load_session,
    load_session_from_har,
    save_session,
)
from .utils import format_bytes


def _format_ts(ts: int) -> str:
    if not ts:
        return "-"
    # Heuristic: ms vs seconds
    if ts > 10_000_000_000:
        ts = int(ts / 1000)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _format_date_short(ts: int) -> str:
    if not ts:
        return "-"
    if ts > 10_000_000_000:
        ts = int(ts / 1000)
    return datetime.fromtimestamp(ts).strftime("%d-%m-%y")


def _format_gb(num: int) -> str:
    if num <= 0:
        return "0.00Go"
    return f"{num / (1024 ** 3):.2f}Go"


def _format_mo_go(num: int) -> str:
    if num <= 0:
        return "0.00Mo"
    gb = num / (1024 ** 3)
    if gb >= 1.0:
        return f"{gb:.2f}Go"
    mb = num / (1024 ** 2)
    return f"{mb:.2f}Mo"


def _strip_pwmb(name: str) -> str:
    if name.lower().endswith(".pwmb"):
        return name[:-5]
    return name


def _format_mb(num: int) -> str:
    if num <= 0:
        return "-"
    mb = num / (1024 ** 2)
    return f"{mb:.2f} MB"


def _format_seconds_hms(seconds: Optional[float]) -> str:
    if not seconds and seconds != 0:
        return "-"
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return "-"
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_num(val: Optional[float], unit: str = "", decimals: int = 2) -> str:
    if val is None:
        return "-"
    try:
        num = float(val)
    except (TypeError, ValueError):
        return "-"
    return f"{num:.{decimals}f}{unit}"


def _format_minutes_hm(minutes_val) -> str:
    if minutes_val in (None, ""):
        return "-"
    try:
        total = int(float(minutes_val))
    except (TypeError, ValueError):
        return "-"
    if total < 0:
        return "-"
    if total >= 60:
        h = total // 60
        m = total % 60
        return f"{h}h {m:02d}m"
    return f"{total}m"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Anycubic Cloud - Simple GUI")
        self.root.geometry("980x760")

        self.session_path: Optional[str] = None
        self.client: Optional[CloudClient] = None
        self.items_by_id = {}
        self._thumb_cache = {}
        self._tree_id_map = {}
        self._printers_cache = []
        self._last_printer_info = None
        self._last_job_item = None
        self._last_video_response = None
        self._has_active_print = False
        self._printer_poll_interval_idle_ms = 15000
        self._printer_poll_interval_active_ms = 5000
        self._printer_poll_after_id = None
        self._build_ui()
        self._auto_load()
        # MQTT tab removed in Qt; keep Tk UI minimal.
        self._start_printer_poll()

    def _build_ui(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        menu_conn = tk.Menu(menubar, tearoff=0)
        menu_conn.add_command(label="Import HAR", command=self.import_har_dialog)
        menubar.add_cascade(label="Import HAR", menu=menu_conn)

        menu_help = tk.Menu(menubar, tearoff=0)
        menu_help.add_command(label="Aide", command=self.show_help)
        menubar.add_cascade(label="Aide", menu=menu_help)

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        # Session path line removed (not needed for GUI)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, padding=10).pack(fill="x")

        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", maximum=4)
        self.progress.pack(fill="x", padx=10)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        files_tab = ttk.Frame(notebook)
        printer_tab = ttk.Frame(notebook)
        print_tab = ttk.Frame(notebook)
        log_tab = ttk.Frame(notebook)
        notebook.add(files_tab, text="Fichiers")
        notebook.add(printer_tab, text="Printer")
        notebook.add(print_tab, text="Print")
        notebook.add(log_tab, text="LOG")

        header = ttk.Frame(files_tab, padding=10)
        header.pack(fill="x")
        header_left = ttk.Frame(header)
        header_left.pack(side="left")
        ttk.Button(header_left, text="Upload file", command=self.upload_dialog).pack(side="left")
        header_center = ttk.Frame(header)
        header_center.pack(side="left", fill="x", expand=True)
        self.quota_var = tk.StringVar(value="Space use: -/-")
        ttk.Label(header_center, textvariable=self.quota_var, foreground="#666666").pack(anchor="center")
        header_right = ttk.Frame(header)
        header_right.pack(side="right")
        ttk.Button(header_right, text="Quick import", command=self.upload_dialog).pack(side="right")

        self.tree = ttk.Treeview(
            files_tab,
            columns=("name", "size", "created", "details", "actions"),
            show="tree headings",
            selectmode="extended",
        )
        style = ttk.Style(self.root)
        style.configure("Treeview", rowheight=110)
        self.tree.heading("#0", text="Image")
        self.tree.heading("name", text="Name")
        self.tree.heading("size", text="Size")
        self.tree.heading("created", text="Add time")
        self.tree.heading("details", text="Details")
        self.tree.heading("actions", text="Actions")
        self.tree.column("#0", width=150, anchor="center")
        self.tree.column("name", width=380, anchor="w")
        self.tree.column("size", width=150, anchor="w")
        self.tree.column("created", width=190, anchor="w")
        self.tree.column("details", width=90, anchor="center")
        self.tree.column("actions", width=150, anchor="center")
        tree_scroll = ttk.Scrollbar(files_tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        tree_scroll.pack(side="left", fill="y", pady=10)

        printer_frame = ttk.Frame(printer_tab, padding=10)
        printer_frame.pack(fill="x")
        ttk.Label(printer_frame, text="Printers").pack(anchor="w")
        row = ttk.Frame(printer_frame)
        row.pack(fill="x", pady=6)
        self.printer_var = tk.StringVar(value="")
        self.printer_combo = ttk.Combobox(row, textvariable=self.printer_var, state="readonly")
        self.printer_combo.pack(side="left", fill="x", expand=True)
        self.printer_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_printer_selected())
        ttk.Button(row, text="Refresh", command=self.refresh_printers).pack(side="left", padx=6)
        ttk.Button(row, text="Info", command=self.show_printer_info).pack(side="left", padx=6)
        ttk.Button(row, text="Task", command=self.show_projects_from_tab).pack(side="left", padx=6)
        ttk.Button(row, text="Video", command=self.open_video_stream).pack(side="left", padx=6)

        jobs_frame = ttk.Frame(printer_tab, padding=10)
        jobs_frame.pack(fill="x")

        left_panel = ttk.LabelFrame(jobs_frame, text="Printer info", padding=8)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        center_panel = ttk.LabelFrame(jobs_frame, text="Job viewer", padding=8)
        center_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right_panel = ttk.LabelFrame(jobs_frame, text="Job metrics", padding=8)
        right_panel.pack(side="left", fill="both", expand=True)

        self.job_printer_name = tk.StringVar(value="-")
        self.job_printer_status = tk.StringVar(value="-")
        self.job_printer_type = tk.StringVar(value="-")

        self._kv_row(left_panel, "Name", self.job_printer_name)
        self._kv_row(left_panel, "Status", self.job_printer_status)
        self._kv_row(left_panel, "Resin", self.job_printer_type)

        self.job_filename = tk.StringVar(value="-")
        self.job_progress = tk.StringVar(value="-")
        self.job_layers = tk.StringVar(value="-")
        self.job_state = tk.StringVar(value="-")

        self._kv_row(center_panel, "File", self.job_filename)
        self._kv_row(center_panel, "State", self.job_state)
        self._kv_row(center_panel, "Progress", self.job_progress)
        self._kv_row(center_panel, "Layers", self.job_layers)
        self.job_progress_bar = ttk.Progressbar(center_panel, orient="horizontal", length=200, mode="determinate")
        self.job_progress_bar.pack(fill="x", pady=(6, 0))
        self.job_preview_label = tk.Label(center_panel)
        self.job_preview_label.pack(fill="both", expand=True, pady=(8, 0))

        self.job_elapsed = tk.StringVar(value="-")
        self.job_remaining = tk.StringVar(value="-")
        self.job_resin = tk.StringVar(value="-")
        self.job_model_size = tk.StringVar(value="-")
        self.job_layer_thick = tk.StringVar(value="-")
        self.job_exposure = tk.StringVar(value="-")
        self.job_off_time = tk.StringVar(value="-")
        self.job_bottom_time = tk.StringVar(value="-")
        self.job_bottom_layers = tk.StringVar(value="-")

        self._kv_row(right_panel, "Elapsed Time", self.job_elapsed)
        self._kv_row(right_panel, "Remaining Time", self.job_remaining)
        self._kv_row(right_panel, "Estimated Resin", self.job_resin)
        self._kv_row(right_panel, "Model Size", self.job_model_size)
        ttk.Separator(right_panel, orient="horizontal").pack(fill="x", pady=6)
        self._kv_row(right_panel, "Layer Thickness (mm)", self.job_layer_thick)
        self._kv_row(right_panel, "Normal Exposure Time (s)", self.job_exposure)
        self._kv_row(right_panel, "Off Time (s)", self.job_off_time)
        self._kv_row(right_panel, "Bottom Exposure Time (s)", self.job_bottom_time)
        self._kv_row(right_panel, "Bottom Layers", self.job_bottom_layers)

        printer_output = ttk.Frame(printer_tab, padding=10)
        printer_output.pack(fill="both", expand=True)
        ttk.Label(printer_output, text="Task list").pack(anchor="w")
        self.printer_box = ScrolledText(printer_output, height=20, state="disabled")
        self.printer_box.pack(fill="both", expand=True)


        print_frame = ttk.Frame(print_tab, padding=10)
        print_frame.pack(fill="both", expand=True)
        ttk.Label(print_frame, text="Send print order").pack(anchor="w")

        form = ttk.Frame(print_frame)
        form.pack(fill="x", pady=6)

        ttk.Label(form, text="Printer ID").grid(row=0, column=0, sticky="w")
        self.print_printer_var = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.print_printer_var, width=24).grid(row=0, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="File ID").grid(row=1, column=0, sticky="w")
        self.print_file_var = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.print_file_var, width=24).grid(row=1, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="Project ID").grid(row=2, column=0, sticky="w")
        self.print_project_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.print_project_var, width=24).grid(row=2, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="Order ID").grid(row=3, column=0, sticky="w")
        self.print_order_var = tk.StringVar(value="1")
        ttk.Entry(form, textvariable=self.print_order_var, width=24).grid(row=3, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="Delete file (0/1)").grid(row=4, column=0, sticky="w")
        self.print_delete_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.print_delete_var, width=8).grid(row=4, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="Project type").grid(row=5, column=0, sticky="w")
        self.print_project_type_var = tk.StringVar(value="1")
        ttk.Entry(form, textvariable=self.print_project_type_var, width=8).grid(row=5, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="File type").grid(row=6, column=0, sticky="w")
        self.print_filetype_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.print_filetype_var, width=8).grid(row=6, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="Template ID").grid(row=7, column=0, sticky="w")
        self.print_template_var = tk.StringVar(value="-2074360784")
        ttk.Entry(form, textvariable=self.print_template_var, width=24).grid(row=7, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(form, text="Matrix").grid(row=8, column=0, sticky="w")
        self.print_matrix_var = tk.StringVar(value="")
        ttk.Entry(form, textvariable=self.print_matrix_var, width=40).grid(row=8, column=1, sticky="w", padx=6, pady=2)

        btns = ttk.Frame(print_frame)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Send print", command=self.send_print).pack(side="left")
        ttk.Button(btns, text="Clear log", command=self._clear_print_log).pack(side="left", padx=6)

        self.print_box = ScrolledText(print_frame, height=16, state="disabled")
        self.print_box.pack(fill="both", expand=True)

        log_frame = ttk.Frame(log_tab, padding=10)
        log_frame.pack(fill="both", expand=True)
        ttk.Label(log_frame, text="Logs").pack(anchor="w")
        self.log_box = ScrolledText(log_frame, height=20, state="disabled")
        self.log_box.pack(fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click_release)
    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _kv_row(self, parent: tk.Widget, label: str, var: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=f"{label}:").pack(side="left")
        ttk.Label(row, textvariable=var).pack(side="left", padx=(6, 0))

    def _log(self, msg: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _print_log(self, msg: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}\n"
        self.print_box.configure(state="normal")
        self.print_box.insert("1.0", line)
        self.print_box.see("1.0")
        self.print_box.configure(state="disabled")

    def _print_info(self, box: ScrolledText, title: str, data: dict) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", f"{title}\n\n")
        box.insert("end", json.dumps(data, indent=2, ensure_ascii=True))
        box.see("1.0")
        box.configure(state="disabled")

    def _clear_print_log(self) -> None:
        self.print_box.configure(state="normal")
        self.print_box.delete("1.0", "end")
        self.print_box.configure(state="disabled")

    def _start_printer_poll(self) -> None:
        self._schedule_printer_poll(1500)

    def _schedule_printer_poll(self, delay_ms: int) -> None:
        if self._printer_poll_after_id is not None:
            try:
                self.root.after_cancel(self._printer_poll_after_id)
            except tk.TclError:
                pass
        self._printer_poll_after_id = self.root.after(delay_ms, self._poll_printer_status)

    def _poll_printer_status(self) -> None:
        pid = self._print_tab_printer_id()
        if self.client and pid:
            self.refresh_print_projects()
            self.refresh_task_list()
        next_delay = self._printer_poll_interval_active_ms if self._has_active_print else self._printer_poll_interval_idle_ms
        self._schedule_printer_poll(next_delay)

    def _load_thumbnail(self, item_id: str, url: str) -> None:
        def worker() -> None:
            try:
                data = fetch_image_bytes(url, timeout=20.0)
                img = Image.open(BytesIO(data)).convert("RGB")
                img = img.resize((150, 150))
                tk_img = ImageTk.PhotoImage(img)
            except Exception as exc:
                self.root.after(0, lambda exc=exc: self._log(f"Thumbnail load failed: {exc}"))
                return

            def apply() -> None:
                self._thumb_cache[item_id] = tk_img
                if self.tree.exists(item_id):
                    self.tree.item(item_id, image=tk_img)

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _resolve_file_id(self, row_id: str) -> Optional[str]:
        if row_id in self.items_by_id:
            return row_id
        return self._tree_id_map.get(row_id)

    def _on_tree_click_release(self, event) -> None:
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if not row:
            return
        if col == "#4":  # Details column
            file_id = self._resolve_file_id(row)
            if file_id:
                self._open_info_for_id(file_id)
        elif col == "#5":  # Actions column
            file_id = self._resolve_file_id(row)
            if file_id:
                self._open_actions_menu(event, file_id)

    def _on_tree_select(self, _event=None) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        file_id = self._resolve_file_id(ids[0])
        if file_id:
            self._prefill_print_from_file(file_id)

    def _open_actions_menu(self, event, file_id: str) -> None:
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Download", command=lambda fid=file_id: self._download_file_id(fid))
        menu.add_command(label="Delete", command=lambda fid=file_id: self._delete_file_id(fid))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _open_info_for_id(self, file_id: str) -> None:
        item = self.items_by_id.get(file_id)
        if not item:
            self._log(f"Info: item not found for id={file_id}")
            return
        self._log(f"Info: open for id={file_id} gcode_id={item.gcode_id}")
        base_info = {
            "id": file_id,
            "name": item.name,
            "size": _format_mo_go(item.size_bytes),
            "size_bytes": item.size_bytes,
            "created_at": _format_date_short(item.created_at),
            "created_ts": item.created_at,
            "type": item.file_type,
            "md5": item.md5,
            "thumbnail": item.thumbnail,
            "url": item.url,
            "gcode_id": item.gcode_id,
        }

        def work():
            client = self._require_client()
            if item.gcode_id:
                return get_gcode_info(client, item.gcode_id)
            return {}

        def done(info):
            self._show_details_window(base_info, info)
            self._set_status("Info loaded")

        def on_err(exc: Exception) -> None:
            self._log(f"Info API failed for id={file_id}: {exc}")
            self._show_details_window(base_info, {}, note="GCode info unavailable for this file.")
            self._set_status("Info loaded (fallback)")

        self._set_status("Get info ...")
        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _prefill_print_from_file(self, file_id: str) -> None:
        item = self.items_by_id.get(file_id)
        if not item:
            return
        pid = self._selected_printer_id()
        if pid:
            self.print_printer_var.set(pid)
        self.print_file_var.set(str(item.id))
        self.print_project_var.set("0")
        self.print_order_var.set("1")
        self.print_delete_var.set("0")
        self.print_project_type_var.set("1")
        self.print_filetype_var.set("0")
        self.print_template_var.set("-2074360784")
        self.print_matrix_var.set("")

    def show_printers(self) -> None:
        def work():
            client = self._require_client()
            return list_printers(client)

        def done(data):
            self._show_json_window("Printers", data)
            self._set_status("Printers loaded")

        def on_err(exc: Exception) -> None:
            self._log(f"Printers API failed: {exc}")
            messagebox.showerror("Printers", f"Failed to load printers:\n{exc}")
            self._set_status("Printers failed")

        self._set_status("Printers ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_printers(self) -> None:
        def work():
            client = self._require_client()
            return list_printers(client)

        def done(data):
            printers = data if isinstance(data, list) else data.get("data") or data.get("list") or data
            if isinstance(printers, dict):
                printers = printers.get("list") or printers.get("data") or []
            self._printers_cache = printers if isinstance(printers, list) else []
            names = []
            for p in self._printers_cache:
                name = p.get("name") or p.get("printer_name") or f"Printer {p.get('id', '')}"
                pid = p.get("id") or p.get("printer_id")
                names.append(f"{name} [{pid}]")
            self.printer_combo["values"] = names
            if names:
                self.printer_combo.current(0)
                pid = self._selected_printer_id()
                if pid:
                    self.print_printer_var.set(pid)
            self._on_printer_selected()
            self._set_status(f"Printers loaded ({len(names)})")

        def on_err(exc: Exception) -> None:
            self._log(f"Printers API failed: {exc}")
            messagebox.showerror("Printers", f"Failed to load printers:\n{exc}")
            self._set_status("Printers failed")

        self._set_status("Printers ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _selected_printer_id(self) -> Optional[str]:
        sel = self.printer_var.get().strip()
        if sel and "[" in sel and sel.endswith("]"):
            return sel.split("[")[-1].rstrip("]")
        return None

    def _selected_printer_entry(self) -> Optional[dict]:
        pid = self._selected_printer_id()
        if not pid:
            return None
        for printer in self._printers_cache:
            value = printer.get("id") or printer.get("printer_id")
            if value is not None and str(value) == str(pid):
                return printer
        return None

    def _looks_like_video_url(self, key: str, value: str) -> bool:
        key_l = (key or "").lower()
        value_l = value.lower()
        if value_l.startswith(("rtsp://", "rtmp://")):
            return True
        if "m3u8" in value_l:
            return True
        if value_l.startswith("http") and any(
            token in key_l for token in ("video", "stream", "camera", "live", "hls", "webrtc")
        ):
            return True
        return False

    def _extract_video_url(self, payload) -> Optional[str]:
        if not payload:
            return None
        visited = set()

        def walk(obj) -> Optional[str]:
            oid = id(obj)
            if oid in visited:
                return None
            visited.add(oid)
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str) and self._looks_like_video_url(k, v):
                        return v
                    found = walk(v)
                    if found:
                        return found
            elif isinstance(obj, list):
                for item in obj:
                    found = walk(item)
                    if found:
                        return found
            return None

        return walk(payload)

    def _resolve_video_url(self) -> Optional[str]:
        for source in (
            self._last_video_response,
            self._last_printer_info,
            self._last_job_item,
            self._selected_printer_entry(),
        ):
            url = self._extract_video_url(source)
            if url:
                return url
        return None

    def _redact_secrets(self, payload):
        if not isinstance(payload, (dict, list)):
            return payload
        secret_keys = {
            "accesskey",
            "secretkey",
            "sessiontoken",
            "token",
            "authorization",
            "awsaccesskey",
            "awssecretkey",
            "agora_token",
            "shengwang",
        }
        if isinstance(payload, list):
            return [self._redact_secrets(item) for item in payload]
        redacted = {}
        for key, value in payload.items():
            key_l = str(key).lower()
            if any(k in key_l for k in secret_keys):
                redacted[key] = "***"
            else:
                redacted[key] = self._redact_secrets(value)
        return redacted

    def open_video_stream(self) -> None:
        pid = self._selected_printer_id()
        if not pid:
            messagebox.showinfo("Video", "Select a printer first.")
            return

        def work():
            client = self._require_client()
            return send_video_order(client, pid)

        def done(data):
            self._last_video_response = data
            url = self._resolve_video_url()
            if url:
                opened = webbrowser.open_new(url)
                if not opened:
                    messagebox.showerror("Video", "Ouverture du flux video impossible.")
                    return
                self._set_status("Video stream opened")
                return
            sanitized = self._redact_secrets(data)
            self._show_json_window("Video response", sanitized)
            messagebox.showinfo(
                "Video",
                "Commande envoyée. Le flux est déclenché via MQTT + PeerVideoService.",
            )
            self._set_status("Video command sent")

        def on_err(exc: Exception) -> None:
            messagebox.showerror("Video", f"Video command failed:\n{exc}")
            self._set_status("Video command failed")

        self._set_status("Video ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def show_printer_info(self) -> None:
        pid = self._selected_printer_id()
        if not pid:
            messagebox.showinfo("Printer", "Select a printer first.")
            return

        def work():
            client = self._require_client()
            return get_printer_info_v2(client, pid)

        def done(data):
            self._last_printer_info = data
            self._show_json_window("Printer info", data)
            self._set_status("Printer info loaded")

        def on_err(exc: Exception) -> None:
            self._log(f"Printer v2 API failed: {exc}")
            messagebox.showerror("Printer", f"Failed to load printer info:\n{exc}")
            self._set_status("Printer info failed")

        self._set_status("Printer info ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def send_print(self) -> None:
        pid = self.print_printer_var.get().strip()
        fid = self.print_file_var.get().strip()
        if not pid or not fid:
            messagebox.showinfo("Print", "Printer ID and File ID are required.")
            return
        project_id = self.print_project_var.get().strip() or "0"
        order_id = self.print_order_var.get().strip() or "1"
        is_delete = self.print_delete_var.get().strip() or "0"
        project_type = self.print_project_type_var.get().strip() or "1"
        filetype = self.print_filetype_var.get().strip() or "0"
        template_id = self.print_template_var.get().strip() or "-2074360784"
        matrix = self.print_matrix_var.get().strip()

        def work():
            client = self._require_client()
            return send_print_order(
                client,
                file_id=fid,
                printer_id=pid,
                project_id=project_id,
                order_id=order_id,
                is_delete_file=is_delete,
                data_payload={
                    "file_id": str(fid),
                    "matrix": matrix,
                    "filetype": int(filetype),
                    "project_type": int(project_type),
                    "template_id": int(template_id),
                },
            )

        def done(data):
            self._print_log("Send print: OK")
            self._print_log(json.dumps(data, indent=2, ensure_ascii=True))
            self._set_status("Print order sent")
            self.refresh_print_projects()
            self.refresh_task_list()
            self._schedule_printer_poll(2000)

        def on_err(exc: Exception) -> None:
            self._print_log(f"Send print failed: {exc}")
            self._set_status("Print order failed")

        self._set_status("Send print ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _send_print_for_file(self, file_id: str, parent: Optional[tk.Toplevel] = None) -> None:
        pid = self._print_tab_printer_id()
        if not pid:
            messagebox.showinfo("Print", "Printer ID is required.")
            return
        parent_win = parent.winfo_toplevel() if parent else self.root
        try:
            parent_win.lift()
            parent_win.attributes("-topmost", True)
        except tk.TclError:
            parent_win = self.root
        if not messagebox.askyesno("Print", f"Lancer l'impression du fichier {file_id} ?", parent=parent_win):
            try:
                parent_win.attributes("-topmost", False)
            except tk.TclError:
                pass
            return
        try:
            parent_win.attributes("-topmost", False)
        except tk.TclError:
            pass

        project_id = self.print_project_var.get().strip() or "0"
        order_id = self.print_order_var.get().strip() or "1"
        is_delete = self.print_delete_var.get().strip() or "0"
        project_type = self.print_project_type_var.get().strip() or "1"
        filetype = self.print_filetype_var.get().strip() or "0"
        template_id = self.print_template_var.get().strip() or "-2074360784"
        matrix = self.print_matrix_var.get().strip()

        def work():
            client = self._require_client()
            return send_print_order(
                client,
                file_id=str(file_id),
                printer_id=pid,
                project_id=project_id,
                order_id=order_id,
                is_delete_file=is_delete,
                data_payload={
                    "file_id": str(file_id),
                    "matrix": matrix,
                    "filetype": int(filetype),
                    "project_type": int(project_type),
                    "template_id": int(template_id),
                },
            )

        def done(data):
            self._log("Print order sent")
            self._log(json.dumps(data, indent=2, ensure_ascii=True))
            self._set_status("Print order sent")
            self.refresh_print_projects()
            self.refresh_task_list()
            self._schedule_printer_poll(2000)

        def on_err(exc: Exception) -> None:
            self._log(f"Print order failed: {exc}")
            self._set_status("Print order failed")

        self._set_status("Send print ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _print_tab_printer_id(self) -> Optional[str]:
        pid = self.print_printer_var.get().strip()
        if pid:
            return pid
        return self._selected_printer_id()

    def refresh_print_projects(self) -> None:
        pid = self._print_tab_printer_id()
        if not pid:
            messagebox.showinfo("Print", "Printer ID is required.")
            return

        def work():
            client = self._require_client()
            return get_projects(client, pid, print_status=1, page=1, limit=10)

        def done(data):
            items = self._task_items(data)
            active = len(items) > 0
            self._apply_print_state(active, source="projects")
            if items:
                self._update_job_ui_from_task(items[0])
            else:
                self._reset_job_ui()
            self._set_status("Projects loaded")

        def on_err(exc: Exception) -> None:
            self._log(f"Projects API failed: {exc}")
            self._reset_job_ui()
            self._set_status("Projects failed")

        self._set_status("Projects ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_task_list(self) -> None:
        pid = self._print_tab_printer_id()
        if not pid:
            return

        def work():
            client = self._require_client()
            result = {}
            for status in (0, 1, 2):
                result[str(status)] = get_projects(client, pid, print_status=status, page=1, limit=10)
            return result

        def done(data):
            self._render_task_list(self.printer_box, data)
            items = self._task_items(data.get("1") if isinstance(data, dict) else [])
            active = len(items) > 0
            self._apply_print_state(active, source="tasks")
            self._set_status("Task list loaded")

        def on_err(exc: Exception) -> None:
            self._print_info(self.printer_box, "Task list (error)", {"error": str(exc)})
            self._set_status("Task list failed")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _task_items(self, payload: dict) -> list:
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            return payload.get("data") or []
        if isinstance(payload, list):
            return payload
        return []

    def _parse_json_field(self, value) -> dict:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        return {}

    def _job_status_text(self, item: dict, settings: dict) -> str:
        connect_status = item.get("connect_status")
        device_status = item.get("device_status")
        print_status = item.get("print_status")
        pause = item.get("pause")
        state = settings.get("state")
        if connect_status in (0, "0") or device_status in (0, "0"):
            return "Offline"
        if state == "printing" or print_status == 1:
            return "Busy"
        if pause == 1 or state == "paused":
            return "Paused"
        return "Idle"

    def _apply_print_state(self, active: bool, source: str) -> None:
        if active == self._has_active_print:
            return
        self._has_active_print = active
        if active:
            self._log("Impression lancée (détection auto).")
            self._set_status("Impression en cours")
            return
        self._log("Impression terminée (détection auto).")
        self._set_status("Impression terminée")
        try:
            messagebox.showinfo("Printer", "Impression terminée.")
        except tk.TclError:
            pass

    def _reset_job_ui(self) -> None:
        self.job_printer_name.set("-")
        self.job_printer_status.set("-")
        self.job_printer_type.set("-")
        self._last_job_item = None
        self.job_filename.set("-")
        self.job_state.set("-")
        self.job_progress.set("-")
        self.job_layers.set("-")
        self.job_elapsed.set("-")
        self.job_remaining.set("-")
        self.job_resin.set("-")
        self.job_model_size.set("-")
        self.job_layer_thick.set("-")
        self.job_exposure.set("-")
        self.job_off_time.set("-")
        self.job_bottom_time.set("-")
        self.job_bottom_layers.set("-")
        self.job_progress_bar["value"] = 0
        self.job_preview_label.configure(image="", text="")
        self.job_preview_label.image = None

    def _update_job_ui_from_task(self, item: dict) -> None:
        self._last_job_item = item
        settings = self._parse_json_field(item.get("settings"))
        slice_param = self._parse_json_field(item.get("slice_param")) or self._parse_json_field(item.get("slice_result"))

        filename = settings.get("filename") or item.get("gcode_name") or item.get("name") or "-"
        progress = settings.get("progress")
        if progress is None:
            progress = item.get("progress")
        try:
            progress_val = int(float(progress))
        except (TypeError, ValueError):
            progress_val = 0

        curr_layer = settings.get("curr_layer")
        total_layers = settings.get("total_layers") or slice_param.get("layers")
        layers_text = "-"
        if curr_layer is not None and total_layers is not None:
            layers_text = f"{curr_layer} / {total_layers}"

        remain_time = settings.get("remain_time")
        if remain_time is None:
            remain_time = item.get("remain_time")
        remaining_text = _format_minutes_hm(remain_time)

        print_time = item.get("print_time")
        if isinstance(print_time, (int, float)) and print_time >= 0:
            elapsed_text = f"{int(print_time)}m"
        else:
            elapsed_text = "-"

        supplies = settings.get("supplies_usage")
        if supplies is None:
            supplies = slice_param.get("supplies_usage")
        resin_text = _fmt_num(supplies, "ml", 2) if supplies is not None else "-"

        size_x = slice_param.get("size_x")
        size_y = slice_param.get("size_y")
        size_z = slice_param.get("size_z")
        if (size_x in (None, 0, 0.0)) and (size_y in (None, 0, 0.0)):
            model_size = "-"
        else:
            try:
                model_size = f"{float(size_x):.2f}×{float(size_y):.2f}×{float(size_z or 0):.2f}mm"
            except (TypeError, ValueError):
                model_size = "-"

        self.job_printer_name.set(item.get("printer_name") or item.get("machine_name") or "-")
        self.job_printer_status.set(self._job_status_text(item, settings))
        resin_type = slice_param.get("material_type") or settings.get("material_type") or "-"
        self.job_printer_type.set(resin_type)
        self.job_filename.set(filename)
        self.job_state.set(settings.get("state") or item.get("print_status") or "-")
        self.job_progress.set(f"{progress_val}%")
        self.job_layers.set(layers_text)
        self.job_elapsed.set(elapsed_text)
        self.job_remaining.set(remaining_text)
        self.job_resin.set(resin_text)
        self.job_model_size.set(model_size)
        self.job_layer_thick.set(_fmt_num(slice_param.get("zthick"), "", 3))
        self.job_exposure.set(_fmt_num(slice_param.get("exposure_time"), "", 3))
        self.job_off_time.set(_fmt_num(slice_param.get("off_time"), "", 3))
        self.job_bottom_time.set(_fmt_num(slice_param.get("bott_time"), "", 3))
        self.job_bottom_layers.set(slice_param.get("bott_layers") if slice_param.get("bott_layers") is not None else "-")
        self.job_progress_bar["value"] = progress_val

        img_url = item.get("img") or item.get("image_id")
        if img_url:
            self._load_job_preview(img_url)
        else:
            self.job_preview_label.configure(image="", text="")
            self.job_preview_label.image = None

    def _load_job_preview(self, url: str) -> None:
        def worker() -> None:
            try:
                data = fetch_image_bytes(url, timeout=20.0)
                img = Image.open(BytesIO(data)).convert("RGB")
                img = img.resize((200, 200))
                tk_img = ImageTk.PhotoImage(img)
            except Exception as exc:
                self.root.after(0, lambda exc=exc: self._log(f"Job preview failed: {exc}"))
                return

            def apply() -> None:
                self.job_preview_label.configure(image=tk_img)
                self.job_preview_label.image = tk_img

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _render_task_list(self, box: ScrolledText, payload: dict) -> None:
        lines = ["Task list (status 0/1/2)", ""]
        for status_key in ("0", "1", "2"):
            lines.append(f"status={status_key}")
            items = self._task_items(payload.get(status_key) if isinstance(payload, dict) else [])
            if not items:
                lines.append("  (none)")
                lines.append("")
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                lines.append(f"  taskid: {item.get('taskid') or item.get('id')}")
                lines.append(f"  gcode_id: {item.get('gcode_id')}")
                lines.append(f"  img: {item.get('img')}")
                lines.append(f"  estimate: {item.get('estimate')}")
                lines.append(f"  remain_time: {item.get('remain_time')}")
                lines.append(f"  material: {item.get('material')}")
                lines.append(f"  progress: {item.get('progress')}")
                lines.append(f"  print_status: {item.get('print_status')}")
                lines.append(f"  gcode_name: {item.get('gcode_name') or item.get('name')}")
                lines.append("")
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", "\n".join(lines).strip() + "\n")
        box.see("1.0")
        box.configure(state="disabled")

    def _on_printer_selected(self) -> None:
        self.refresh_print_projects()
        self.refresh_task_list()
        self._schedule_printer_poll(1500)

    def refresh_print_printer_info(self) -> None:
        pid = self._print_tab_printer_id()
        if not pid:
            messagebox.showinfo("Print", "Printer ID is required.")
            return

        def work():
            client = self._require_client()
            return get_printer_info_v2(client, pid)

        def done(data):
            self._last_printer_info = data
            self._show_json_window("Printer info", data)
            self._set_status("Printer info loaded")

        def on_err(exc: Exception) -> None:
            messagebox.showerror("Printer", f"Failed to load printer info:\n{exc}")
            self._set_status("Printer info failed")

        self._set_status("Printer info ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()

    def show_projects_from_tab(self) -> None:
        pid = self._selected_printer_id()
        if not pid:
            messagebox.showinfo("Projects", "Select a printer first.")
            return
        def work():
            client = self._require_client()
            return get_projects(client, pid, print_status=1, page=1, limit=10)

        def done(data):
            self._show_json_window("Projects", data)
            self._set_status("Projects loaded")

        def on_err(exc: Exception) -> None:
            self._log(f"Projects API failed: {exc}")
            messagebox.showerror("Projects", f"Failed to load projects:\n{exc}")
            self._set_status("Projects failed")

        self._set_status("Projects ...")

        def worker():
            try:
                result = work()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: on_err(exc))
                return
            self.root.after(0, lambda: done(result))

        threading.Thread(target=worker, daemon=True).start()


    def _show_json_window(self, title: str, data: dict) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("900x600")

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)

        text = ScrolledText(frame, height=30)
        text.pack(fill="both", expand=True)
        text.insert("1.0", json.dumps(data, indent=2, ensure_ascii=True))
        text.configure(state="normal")
        text.focus_set()

    def _auto_load(self) -> None:
        # Auto-load session if it exists
        try:
            if os.path.exists(DEFAULT_SESSION_PATH):
                self._init_client(DEFAULT_SESSION_PATH)
        except Exception:
            pass

    def _require_client(self) -> CloudClient:
        if not self.client:
            raise RuntimeError("No session loaded. Load a session.json or import a HAR file.")
        return self.client

    def _run_task(self, label: str, fn, on_success) -> None:
        self._set_status(f"{label} ...")

        def worker() -> None:
            try:
                result = fn()
            except Exception as exc:
                self.root.after(0, lambda exc=exc: self._on_error(label, exc))
                return
            self.root.after(0, lambda: on_success(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_error(self, label: str, exc: Exception) -> None:
        self._set_status(f"{label} failed")
        messagebox.showerror("Error", f"{label} failed:\n{exc}")

    def _init_client(self, session_path: str) -> None:
        session = load_session(session_path)
        self.client = CloudClient(cookies=session["cookies"], tokens=session.get("tokens", {}))
        self.session_path = session_path
        self._set_status("Session loaded")
        self.refresh_list()
        self.refresh_quota()
        self.refresh_printers()

    def show_help(self) -> None:
        message = (
            "Anycubic Cloud - Simple GUI\\n\\n"
            "What you can do:\\n"
            "- Import a HAR file to create a session\\n"
            "- List files, view quota, upload, download, delete\\n\\n"
            "How to get the HAR file:\\n"
            "1) Open https://cloud-universe.anycubic.com in your browser\\n"
            "2) Login\\n"
            "3) Open DevTools -> Network\\n"
            "4) Reload the page\\n"
            "5) Right click in Network list -> Save all as HAR\\n"
            "6) Import the HAR in the app\\n\\n"
            "Session info is saved to .accloud/session.json\\n"
            "Once saved, the app will auto-load it on next start."
        )
        messagebox.showinfo("Aide", message)

    def load_session_dialog(self) -> None:
        path = filedialog.askopenfilename(title="Select session.json", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            self._init_client(path)
        except Exception as exc:
            self._on_error("Load session", exc)

    def import_har_dialog(self) -> None:
        path = filedialog.askopenfilename(title="Select HAR file", filetypes=[("HAR files", "*.har")])
        if not path:
            return
        try:
            self.progress.configure(value=1)
            session = load_session_from_har(path)
            self.progress.configure(value=2)
            save_session(DEFAULT_SESSION_PATH, session["cookies"], session.get("tokens", {}))
            self.progress.configure(value=3)
            self._init_client(DEFAULT_SESSION_PATH)
            self.progress.configure(value=4)
            self._set_status(f"Imported HAR -> {DEFAULT_SESSION_PATH}")
            self._log(f"Imported HAR: {path}")
        except Exception as exc:
            self._on_error("Import HAR", exc)

    def refresh_quota(self) -> None:
        def work():
            client = self._require_client()
            return get_quota(client)

        def done(quota):
            free = quota.total_bytes - quota.used_bytes
            self.quota_var.set(
                f"Space use: {format_bytes(quota.used_bytes)}/{format_bytes(quota.total_bytes)}"
            )
            self._set_status("Quota updated")

        self._run_task("Get quota", work, done)

    def refresh_list(self) -> None:
        def work():
            client = self._require_client()
            return list_files(client, page=1, limit=50)

        def done(items):
            for row in self.tree.get_children():
                self.tree.delete(row)
            self.items_by_id = {item.id: item for item in items}
            self._thumb_cache = {}
            self._tree_id_map = {}
            for item in items:
                row_id = self.tree.insert(
                    "",
                    "end",
                    iid=item.id,
                    text="",
                    values=(
                        item.name,
                        f"Size: {_format_mb(item.size_bytes)}",
                        f"Add time: {_format_ts(item.created_at)}",
                        "Details",
                        "Delete | Download",
                    ),
                )
                self._tree_id_map[row_id] = item.id
                if item.thumbnail:
                    self._load_thumbnail(row_id, item.thumbnail)
            self._set_status(f"Loaded {len(items)} items")

        self._run_task("List files", work, done)

    def upload_dialog(self) -> None:
        path = filedialog.askopenfilename(title="Select file to upload")
        if not path:
            return

        def work():
            client = self._require_client()
            return upload_file(client, path)

        def done(file_id):
            self._set_status(f"Upload ok (id={file_id})")
            self.refresh_list()

        self._run_task("Upload", work, done)

    def _selected_ids(self):
        ids = []
        for row_id in self.tree.selection():
            file_id = self._resolve_file_id(row_id)
            if file_id:
                ids.append(file_id)
        return ids

    def download_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            messagebox.showinfo("Download", "Select one file to download.")
            return
        self._download_file_id(ids[0])

    def _download_file_id(self, file_id: str) -> None:
        path = filedialog.asksaveasfilename(title="Save file as")
        if not path:
            return

        def work():
            client = self._require_client()
            url = get_download_url(client, file_id)
            if not url:
                raise RuntimeError("No download URL returned")
            with httpx.stream("GET", url, timeout=60.0) as resp:
                resp.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
            return path

        def done(saved_path):
            self._set_status(f"Downloaded to {saved_path}")

        self._run_task("Download", work, done)

    def delete_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            messagebox.showinfo("Delete", "Select files to delete.")
            return
        self._delete_file_id(ids)

    def _delete_file_id(self, file_ids) -> None:
        if isinstance(file_ids, str):
            ids = [file_ids]
        else:
            ids = list(file_ids)
        if not ids:
            return
        if not messagebox.askyesno("Delete", f"Delete {len(ids)} file(s)?"):
            return

        def work():
            client = self._require_client()
            delete_files(client, ids)
            return True

        def done(_):
            self._set_status("Deleted")
            self.refresh_list()

        self._run_task("Delete", work, done)

    # Info is accessed via the table (double-click on Info column).

    def _show_details_window(self, base_info: dict, gcode_info: dict, note: str = "") -> None:
        win = tk.Toplevel(self.root)
        win.title("File Details")
        win.geometry("940x720")

        bg = "#f4f5f7"
        card_bg = "#ffffff"
        muted = "#666666"
        win.configure(bg=bg)

        outer = tk.Frame(win, bg=bg, padx=16, pady=16)
        outer.pack(fill="both", expand=True)

        card_a = tk.Frame(outer, bg=card_bg, padx=16, pady=16)
        card_a.pack(fill="x", pady=(0, 12))

        header = tk.Frame(card_a, bg=card_bg)
        header.pack(fill="x")
        title = base_info.get("name") or "File"
        tk.Label(header, text=title, bg=card_bg, fg="#111111", font=("Helvetica", 13, "bold")).pack(side="left")
        file_id = base_info.get("id")
        if file_id:
            btn_state = "disabled" if self._has_active_print else "normal"
            tk.Button(
                header,
                text="Print",
                state=btn_state,
                command=lambda fid=str(file_id), w=win: self._send_print_for_file(fid, parent=w),
            ).pack(side="right")

        body = tk.Frame(card_a, bg=card_bg)
        body.pack(fill="x", pady=(12, 0))

        left = tk.Frame(body, bg=card_bg)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        preview = tk.Frame(left, bg="#f0f0f0", width=520, height=320)
        preview.pack(fill="both", expand=True)
        preview.pack_propagate(False)
        preview_label = tk.Label(preview, bg="#f0f0f0")
        preview_label.pack(expand=True)

        right = tk.Frame(body, bg=card_bg)
        right.pack(side="right", fill="y")

        meta_rows = [
            ("File name", base_info.get("name") or "-"),
            ("Type", "Slice file"),
            ("Size", _format_mb(base_info.get("size_bytes") or 0) if "size_bytes" in base_info else base_info.get("size") or "-"),
            ("Time uploaded", _format_ts(base_info.get("created_ts") or 0) if "created_ts" in base_info else base_info.get("created_at") or "-"),
        ]

        for label, value in meta_rows:
            row = tk.Frame(right, bg=card_bg)
            row.pack(anchor="w", pady=4)
            tk.Label(row, text=f"{label}:", bg=card_bg, fg=muted).pack(side="left")
            tk.Label(row, text=str(value), bg=card_bg, fg="#111111").pack(side="left", padx=(6, 0))

        card_b = tk.Frame(outer, bg=card_bg, padx=16, pady=16)
        card_b.pack(fill="both", expand=True)

        b_header = tk.Frame(card_b, bg=card_bg)
        b_header.pack(fill="x")
        tk.Label(b_header, text="⚙  Slicing details", bg=card_bg, fg="#111111", font=("Helvetica", 11, "bold")).pack(anchor="w")
        tk.Frame(card_b, bg="#e6e6e6", height=1).pack(fill="x", pady=(8, 12))

        slice_param = gcode_info.get("slice_param") or gcode_info.get("slice_result") or {}
        machine_name = slice_param.get("machine_name") or gcode_info.get("machine_name") or "-"
        size_x = slice_param.get("size_x")
        size_y = slice_param.get("size_y")
        size_z = slice_param.get("size_z")
        if (size_x in (None, 0, 0.0)) and (size_y in (None, 0, 0.0)):
            print_size = "-"
        else:
            try:
                print_size = f"{float(size_x):.2f} × {float(size_y):.2f} × {float(size_z or 0):.2f} mm"
            except (TypeError, ValueError):
                print_size = "-"

        left_items = [
            ("Printer type", machine_name),
            ("Print size", print_size),
            ("Estimated printing time", _format_seconds_hms(slice_param.get("estimate"))),
            ("Thickness (mm)", _fmt_num(slice_param.get("zthick"), "", 2)),
            ("Lights off time(s)", _fmt_num(slice_param.get("off_time"), "", 2)),
            ("Number of bottom layers", slice_param.get("bott_layers") if slice_param.get("bott_layers") is not None else "-"),
            ("Z Axis lifting speed(mm/s)", _fmt_num(slice_param.get("zup_speed"), "", 2)),
        ]

        right_items = [
            ("Consumables", slice_param.get("material_type") or "-"),
            ("Slice layers", slice_param.get("layers") if slice_param.get("layers") is not None else "-"),
            ("Estimated amount of consumables", _fmt_num(slice_param.get("supplies_usage"), slice_param.get("material_unit") or "", 2)),
            ("Exposure time(s)", _fmt_num(slice_param.get("exposure_time"), "", 2)),
            ("Bottom exposure time(s)", _fmt_num(slice_param.get("bott_time"), "", 2)),
            ("Z Axis lifting distance(mm)", _fmt_num(slice_param.get("zup_height"), "", 2)),
            ("Z Axis fallback speed(mm/s)", _fmt_num(slice_param.get("zdown_speed"), "", 2)),
        ]

        grid = tk.Frame(card_b, bg=card_bg)
        grid.pack(fill="both", expand=True)
        col_left = tk.Frame(grid, bg=card_bg)
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 16))
        col_right = tk.Frame(grid, bg=card_bg)
        col_right.pack(side="right", fill="both", expand=True)

        def add_rows(parent, rows):
            for label, value in rows:
                row = tk.Frame(parent, bg=card_bg)
                row.pack(anchor="w", pady=4, fill="x")
                tk.Label(row, text=f"{label}:", bg=card_bg, fg=muted).pack(side="left")
                tk.Label(row, text=str(value), bg=card_bg, fg="#111111").pack(side="left", padx=(6, 0))

        add_rows(col_left, left_items)
        add_rows(col_right, right_items)

        if note or not gcode_info:
            tk.Label(card_b, text="Some data unavailable", bg=card_bg, fg=muted).pack(anchor="w", pady=(10, 0))

        def load_preview(url: Optional[str]) -> None:
            if not url:
                preview_label.configure(text="Image unavailable", fg=muted)
                return

            def worker() -> None:
                try:
                    data = fetch_image_bytes(url, timeout=20.0)
                    img = Image.open(BytesIO(data)).convert("RGB")
                    img = img.resize((320, 320))
                    tk_img = ImageTk.PhotoImage(img)
                except Exception as exc:
                    self.root.after(0, lambda exc=exc: self._log(f"Preview load failed: {exc}"))
                    self.root.after(0, lambda: preview_label.configure(text="Image unavailable", fg=muted))
                    return

                def apply() -> None:
                    preview_label.configure(image=tk_img)
                    preview_label.image = tk_img

                self.root.after(0, apply)

            threading.Thread(target=worker, daemon=True).start()

        img_url = gcode_info.get("image_id") or gcode_info.get("img") or base_info.get("thumbnail")
        load_preview(img_url)



def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
