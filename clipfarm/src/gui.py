"""
ClipFarm GUI Dashboard
Built with tkinter - no external dependencies required.
"""

import json
import os
import platform
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "clips"
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"

# Ensure output dir exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    """Load settings from config/settings.json."""
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


class RedirectText:
    """Redirect stdout/stderr to a tkinter text widget."""

    def __init__(self, widget: scrolledtext.ScrolledText):
        self.widget = widget

    def write(self, text: str):
        if not text:
            return
        self.widget.after(0, self._append, text)

    def _append(self, text: str):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")

    def flush(self):
        pass


class ClipFarmGUI:
    # Color scheme
    BG = "#1e1e2e"
    BG_SECONDARY = "#2a2a3d"
    BG_INPUT = "#313147"
    FG = "#cdd6f4"
    FG_DIM = "#7f849c"
    ACCENT = "#89b4fa"
    ACCENT_HOVER = "#b4d0fb"
    RED = "#f38ba8"
    GREEN = "#a6e3a1"
    YELLOW = "#f9e2af"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ClipFarm Dashboard")
        self.root.geometry("960x820")
        self.root.minsize(860, 720)
        self.root.configure(bg=self.BG)

        self.settings = load_settings()
        self.url_queue: list[str] = []
        self.results: list[dict] = []
        self._processing = False

        self._build_styles()
        self._build_ui()
        self._redirect_output()

    # ------------------------------------------------------------------
    # Styling helpers
    # ------------------------------------------------------------------

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=self.BG, foreground=self.FG, borderwidth=0)
        style.configure("TFrame", background=self.BG)
        style.configure("Secondary.TFrame", background=self.BG_SECONDARY)
        style.configure("TLabel", background=self.BG, foreground=self.FG, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.ACCENT)
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.ACCENT)

        style.configure(
            "Accent.TButton", background=self.ACCENT, foreground="#1e1e2e",
            font=("Segoe UI", 10, "bold"), padding=(12, 6),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.ACCENT_HOVER), ("disabled", self.FG_DIM)],
        )

        style.configure(
            "Danger.TButton", background=self.RED, foreground="#1e1e2e",
            font=("Segoe UI", 10, "bold"), padding=(12, 6),
        )
        style.map("Danger.TButton", background=[("active", "#f5a0b8")])

        style.configure(
            "Green.TButton", background=self.GREEN, foreground="#1e1e2e",
            font=("Segoe UI", 10, "bold"), padding=(12, 6),
        )
        style.map("Green.TButton", background=[("active", "#b8edaf")])

        style.configure(
            "TButton", background=self.BG_SECONDARY, foreground=self.FG,
            font=("Segoe UI", 10), padding=(10, 5),
        )
        style.map("TButton", background=[("active", self.BG_INPUT)])

        style.configure(
            "TCheckbutton", background=self.BG, foreground=self.FG,
            font=("Segoe UI", 10),
        )
        style.map("TCheckbutton", background=[("active", self.BG)])

        style.configure("Horizontal.TScale", background=self.BG, troughcolor=self.BG_INPUT)
        style.configure(
            "Horizontal.TProgressbar", background=self.ACCENT,
            troughcolor=self.BG_INPUT, thickness=14,
        )

        style.configure(
            "TCombobox", fieldbackground=self.BG_INPUT, background=self.BG_INPUT,
            foreground=self.FG, selectbackground=self.ACCENT, selectforeground="#1e1e2e",
        )
        style.map("TCombobox", fieldbackground=[("readonly", self.BG_INPUT)])

    def _make_entry(self, parent, **kwargs) -> tk.Entry:
        """Create a dark-themed entry widget."""
        e = tk.Entry(
            parent, bg=self.BG_INPUT, fg=self.FG, insertbackground=self.FG,
            relief="flat", font=("Segoe UI", 10), highlightthickness=1,
            highlightbackground=self.BG_SECONDARY, highlightcolor=self.ACCENT,
            **kwargs,
        )
        return e

    def _make_listbox(self, parent, **kwargs) -> tk.Listbox:
        lb = tk.Listbox(
            parent, bg=self.BG_INPUT, fg=self.FG, selectbackground=self.ACCENT,
            selectforeground="#1e1e2e", relief="flat", font=("Consolas", 9),
            highlightthickness=0, activestyle="none", **kwargs,
        )
        return lb

    # ------------------------------------------------------------------
    # Build the full UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Title bar
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill="x", padx=16, pady=(12, 4))
        ttk.Label(title_frame, text="ClipFarm", style="Title.TLabel").pack(side="left")
        ttk.Label(
            title_frame, text="TikTok Clip Automation Pipeline",
            foreground=self.FG_DIM, font=("Segoe UI", 10),
        ).pack(side="left", padx=(10, 0))

        # Main content: left column (input + settings) | right column (log + results)
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=12, pady=4)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.rowconfigure(1, weight=1)

        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self._build_input_section(left)
        self._build_settings_panel(left)
        self._build_actions(left)
        self._build_log_section(right)
        self._build_results_panel(right)

        # Bottom: progress bar
        self._build_progress_bar()

    # ---------- 1. Input Section ----------

    def _build_input_section(self, parent):
        frame = ttk.LabelFrame(parent, text="  Input Queue  ", padding=8)
        frame.pack(fill="x", pady=(0, 6))

        row = ttk.Frame(frame)
        row.pack(fill="x")
        self.url_entry = self._make_entry(row)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self.url_entry.bind("<Return>", lambda e: self._add_to_queue())

        ttk.Button(row, text="Add", style="Accent.TButton", command=self._add_to_queue).pack(
            side="left", padx=(6, 0),
        )

        self.queue_listbox = self._make_listbox(parent, height=6)
        self.queue_listbox.pack(fill="both", expand=True, pady=(6, 0))

        btn_row = ttk.Frame(parent)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="Remove Selected", command=self._remove_selected).pack(side="left")
        ttk.Button(btn_row, text="Clear Queue", style="Danger.TButton", command=self._clear_queue).pack(
            side="right",
        )

    # ---------- 2. Settings Panel ----------

    def _build_settings_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="  Settings  ", padding=8)
        frame.pack(fill="x", pady=(6, 6))

        # TikTok handle
        r0 = ttk.Frame(frame)
        r0.pack(fill="x", pady=2)
        ttk.Label(r0, text="TikTok Handle").pack(side="left")
        self.handle_var = tk.StringVar(value=self.settings.get("tiktok_handle", "@yourhandle"))
        self._make_entry(r0, textvariable=self.handle_var, width=20).pack(side="right")

        # Whisper model
        r1 = ttk.Frame(frame)
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="Whisper Model").pack(side="left")
        self.whisper_var = tk.StringVar(
            value=self.settings.get("ai", {}).get("whisper_model", "base"),
        )
        whisper_cb = ttk.Combobox(
            r1, textvariable=self.whisper_var, values=["tiny", "base", "small", "medium"],
            state="readonly", width=12,
        )
        whisper_cb.pack(side="right")

        # Clips per video
        r2 = ttk.Frame(frame)
        r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="Clips per Video").pack(side="left")
        self.clips_var = tk.IntVar(
            value=self.settings.get("ai", {}).get("top_clips", 5),
        )
        self.clips_label = ttk.Label(r2, text=str(self.clips_var.get()), width=3)
        self.clips_label.pack(side="right")
        clips_scale = ttk.Scale(
            r2, from_=1, to=10, variable=self.clips_var, orient="horizontal",
            command=lambda v: self.clips_label.configure(text=str(int(float(v)))),
        )
        clips_scale.pack(side="right", fill="x", expand=True, padx=(8, 4))

        # Color grade
        r3 = ttk.Frame(frame)
        r3.pack(fill="x", pady=2)
        ttk.Label(r3, text="Color Grade").pack(side="left")
        self.color_var = tk.StringVar(
            value=self.settings.get("effects", {}).get("color_grade", "cinematic"),
        )
        ttk.Combobox(
            r3, textvariable=self.color_var, values=["cinematic", "vibrant", "dark"],
            state="readonly", width=12,
        ).pack(side="right")

        # Checkboxes row
        r4 = ttk.Frame(frame)
        r4.pack(fill="x", pady=(6, 0))
        self.use_ai_var = tk.BooleanVar(value=True)
        self.speed_ramp_var = tk.BooleanVar(
            value=self.settings.get("effects", {}).get("speed_ramp", True),
        )
        self.bass_boost_var = tk.BooleanVar(
            value=self.settings.get("effects", {}).get("bass_boost_db", 6) > 0,
        )
        ttk.Checkbutton(r4, text="Use AI", variable=self.use_ai_var).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r4, text="Speed Ramps", variable=self.speed_ramp_var).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r4, text="Bass Boost", variable=self.bass_boost_var).pack(side="left")

    # ---------- 3. Action Buttons ----------

    def _build_actions(self, parent):
        frame = ttk.LabelFrame(parent, text="  Actions  ", padding=8)
        frame.pack(fill="x", pady=(0, 6))

        row1 = ttk.Frame(frame)
        row1.pack(fill="x", pady=(0, 4))
        self.btn_single = ttk.Button(
            row1, text="Process Single", style="Accent.TButton", command=self._process_single,
        )
        self.btn_single.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.btn_batch = ttk.Button(
            row1, text="Batch Process All", style="Green.TButton", command=self._process_batch,
        )
        self.btn_batch.pack(side="left", fill="x", expand=True, padx=(3, 0))

        row2 = ttk.Frame(frame)
        row2.pack(fill="x")
        ttk.Button(row2, text="Quick Edit (Pick File)", command=self._quick_edit).pack(
            side="left", fill="x", expand=True, padx=(0, 3),
        )
        ttk.Button(row2, text="Open Output Folder", command=self._open_output).pack(
            side="left", fill="x", expand=True, padx=(3, 0),
        )

    # ---------- 4. Log Section ----------

    def _build_log_section(self, parent):
        frame = ttk.LabelFrame(parent, text="  Log  ", padding=4)
        frame.pack(fill="both", expand=True, pady=(0, 6))

        self.log_text = scrolledtext.ScrolledText(
            frame, bg=self.BG_INPUT, fg=self.GREEN, font=("Consolas", 9),
            insertbackground=self.FG, relief="flat", state="disabled",
            wrap="word", highlightthickness=0,
        )
        self.log_text.pack(fill="both", expand=True)

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=(4, 0))
        ttk.Button(btn_row, text="Clear Log", command=self._clear_log).pack(side="right")

    # ---------- 5. Results Panel ----------

    def _build_results_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="  Results  ", padding=4)
        frame.pack(fill="both", expand=True)

        self.results_listbox = self._make_listbox(frame, height=5)
        self.results_listbox.pack(fill="both", expand=True)
        self.results_listbox.bind("<<ListboxSelect>>", self._on_result_select)

        # Caption display
        cap_frame = ttk.Frame(frame)
        cap_frame.pack(fill="x", pady=(4, 0))
        self.caption_text = tk.Text(
            cap_frame, bg=self.BG_INPUT, fg=self.YELLOW, font=("Consolas", 9),
            height=3, relief="flat", wrap="word", highlightthickness=0,
        )
        self.caption_text.pack(fill="x", side="left", expand=True)

        ttk.Button(cap_frame, text="Copy", command=self._copy_caption).pack(side="right", padx=(4, 0))

    # ---------- Progress Bar ----------

    def _build_progress_bar(self):
        bar_frame = ttk.Frame(self.root)
        bar_frame.pack(fill="x", padx=16, pady=(2, 10))
        self.progress = ttk.Progressbar(
            bar_frame, mode="indeterminate", style="Horizontal.TProgressbar",
        )
        self.progress.pack(fill="x")
        self.status_label = ttk.Label(bar_frame, text="Ready", foreground=self.FG_DIM)
        self.status_label.pack(pady=(2, 0))

    # ------------------------------------------------------------------
    # Output redirection
    # ------------------------------------------------------------------

    def _redirect_output(self):
        redirector = RedirectText(self.log_text)
        sys.stdout = redirector
        sys.stderr = redirector

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def _add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.url_queue.append(url)
        self.queue_listbox.insert(tk.END, url)
        self.url_entry.delete(0, tk.END)

    def _remove_selected(self):
        sel = self.queue_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.queue_listbox.delete(idx)
        self.url_queue.pop(idx)

    def _clear_queue(self):
        self.url_queue.clear()
        self.queue_listbox.delete(0, tk.END)

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def _set_processing(self, active: bool):
        self._processing = active
        state = "disabled" if active else "!disabled"
        self.btn_single.state([state])
        self.btn_batch.state([state])
        if active:
            self.progress.start(15)
        else:
            self.progress.stop()
            self.progress["value"] = 0

    def _set_status(self, text: str):
        self.status_label.configure(text=text)

    def _get_pipeline_kwargs(self) -> dict:
        return {
            "handle": self.handle_var.get(),
            "use_ai": self.use_ai_var.get(),
            "whisper_model": self.whisper_var.get(),
            "num_clips": int(self.clips_var.get()),
        }

    def _process_single(self):
        if self._processing:
            return
        if not self.url_queue:
            messagebox.showwarning("No URLs", "Add at least one URL to the queue.")
            return

        url = self.url_queue[0]
        kwargs = self._get_pipeline_kwargs()
        self._set_processing(True)
        self._set_status(f"Processing: {url[:50]}...")

        def _run():
            try:
                # Import here to avoid circular imports at module level
                from .pipeline import process_single
                results = process_single(url=url, **kwargs)
                self.root.after(0, self._on_results, results)
            except Exception as e:
                print(f"\n[ERROR] {e}")
            finally:
                self.root.after(0, self._set_processing, False)
                self.root.after(0, self._set_status, "Done")

        threading.Thread(target=_run, daemon=True).start()

    def _process_batch(self):
        if self._processing:
            return
        if not self.url_queue:
            messagebox.showwarning("No URLs", "Add at least one URL to the queue.")
            return

        urls = list(self.url_queue)
        kwargs = self._get_pipeline_kwargs()
        clips_per = kwargs.pop("num_clips")
        self._set_processing(True)
        self._set_status(f"Batch processing {len(urls)} videos...")

        def _run():
            try:
                from .pipeline import process_batch
                results = process_batch(urls=urls, clips_per_video=clips_per, **kwargs)
                self.root.after(0, self._on_results, results)
            except Exception as e:
                print(f"\n[ERROR] {e}")
            finally:
                self.root.after(0, self._set_processing, False)
                self.root.after(0, self._set_status, "Batch complete")

        threading.Thread(target=_run, daemon=True).start()

    def _quick_edit(self):
        if self._processing:
            return

        video_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.mkv *.webm *.avi *.mov"), ("All files", "*.*")],
        )
        if not video_path:
            return

        # Quick-edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Quick Edit")
        dialog.geometry("380x260")
        dialog.configure(bg=self.BG)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Quick Edit", style="Header.TLabel").pack(pady=(12, 8))
        ttk.Label(dialog, text=Path(video_path).name, foreground=self.FG_DIM).pack()

        fields = ttk.Frame(dialog)
        fields.pack(padx=20, pady=10, fill="x")

        ttk.Label(fields, text="Start (sec)").grid(row=0, column=0, sticky="w", pady=4)
        start_entry = self._make_entry(fields, width=12)
        start_entry.grid(row=0, column=1, padx=(8, 0), pady=4)
        start_entry.insert(0, "0")

        ttk.Label(fields, text="End (sec)").grid(row=1, column=0, sticky="w", pady=4)
        end_entry = self._make_entry(fields, width=12)
        end_entry.grid(row=1, column=1, padx=(8, 0), pady=4)
        end_entry.insert(0, "30")

        ttk.Label(fields, text="Hook Text").grid(row=2, column=0, sticky="w", pady=4)
        hook_entry = self._make_entry(fields, width=20)
        hook_entry.grid(row=2, column=1, padx=(8, 0), pady=4)
        hook_entry.insert(0, "WAIT FOR IT")

        def _do_edit():
            try:
                s = float(start_entry.get())
                e = float(end_entry.get())
                hook = hook_entry.get().strip() or "WAIT FOR IT"
            except ValueError:
                messagebox.showerror("Invalid Input", "Start and End must be numbers.")
                return

            dialog.destroy()
            self._set_processing(True)
            self._set_status("Quick editing clip...")

            def _run():
                try:
                    from .editor import edit_clip, edit_clip_simple
                    try:
                        path = edit_clip(
                            video_path, s, e, hook_text=hook,
                            handle=self.handle_var.get(),
                            color_grade=self.color_var.get(),
                        )
                    except Exception:
                        path = edit_clip_simple(
                            video_path, s, e, hook_text=hook,
                            handle=self.handle_var.get(),
                        )
                    print(f"\n[+] Quick edit done: {path}")
                    result = {
                        "clip_number": 1,
                        "output_path": path,
                        "start": s,
                        "end": e,
                        "hook_text": hook,
                        "captions": {},
                    }
                    self.root.after(0, self._on_results, [result])
                except Exception as ex:
                    print(f"\n[ERROR] Quick edit failed: {ex}")
                finally:
                    self.root.after(0, self._set_processing, False)
                    self.root.after(0, self._set_status, "Done")

            threading.Thread(target=_run, daemon=True).start()

        ttk.Button(dialog, text="Generate Clip", style="Accent.TButton", command=_do_edit).pack(pady=10)

    # ------------------------------------------------------------------
    # Results handling
    # ------------------------------------------------------------------

    def _on_results(self, results: list):
        for r in results:
            self.results.append(r)
            name = Path(r["output_path"]).name if r.get("output_path") else f"clip_{r.get('clip_number', '?')}"
            self.results_listbox.insert(tk.END, name)

    def _on_result_select(self, event):
        sel = self.results_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.results):
            return
        result = self.results[idx]

        self.caption_text.delete("1.0", tk.END)

        captions = result.get("captions", {})
        if isinstance(captions, dict):
            cap_list = captions.get("captions", [])
            hashtags = captions.get("hashtags", [])
            text_parts = []
            for c in cap_list:
                t = c.get("text", "") if isinstance(c, dict) else str(c)
                if t:
                    text_parts.append(t)
            if hashtags:
                text_parts.append(" ".join(hashtags))
            self.caption_text.insert("1.0", "\n".join(text_parts) if text_parts else "(no captions)")
        else:
            self.caption_text.insert("1.0", str(captions) if captions else "(no captions)")

    def _copy_caption(self):
        text = self.caption_text.get("1.0", tk.END).strip()
        if text and text != "(no captions)":
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._set_status("Caption copied to clipboard")

    # ------------------------------------------------------------------
    # Utility actions
    # ------------------------------------------------------------------

    def _open_output(self):
        folder = str(OUTPUT_DIR)
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")


def launch():
    """Entry point to launch the GUI."""
    root = tk.Tk()

    # Set icon if available
    icon_path = PROJECT_ROOT / "assets" / "icon.ico"
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except Exception:
            pass

    app = ClipFarmGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
