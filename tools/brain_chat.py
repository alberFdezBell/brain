#!/usr/bin/env python3
"""
brain_chat.py - Interfaz gráfica nativa estilo ChatGPT para consultar la documentación local.
Conecta llama.cpp (Qwen2.5-1.5B) con el motor de evidencia de Project Brain.
100% Python stdlib (Tkinter + urllib), sin procesos en segundo plano tras el cierre.
Incluye barra lateral de historial, animación fluida, botón copiar en hover y selección uniforme.
"""

import sys
import os
import threading
import queue
import json
import re
import ctypes
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Añadir tools/ al path
TOOLS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(TOOLS_DIR))

from brain_chat_backend import LlamaServerManager, stream_chat_completion
from brain_ask import build_evidence_package
from brain_common import get_brain_home, read_note


# Paleta de colores ChatGPT Dark Mode
BG_DARK = "#212121"
BG_CHAT = "#171717"
BG_SIDEBAR = "#18181b"
BG_SIDEBAR_HOVER = "#27272a"
BG_SIDEBAR_ACTIVE = "#2d2d32"
BG_USER_BUBBLE = "#2f2f2f"
BG_BOT_BUBBLE = "#212121"
BG_INPUT = "#2f2f2f"
FG_TEXT = "#ececec"
FG_MUTED = "#8e8e8e"
ACCENT_GREEN = "#10a37f"
ACCENT_BLUE = "#3b82f6"
BORDER_COLOR = "#383838"

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def get_chats_dir() -> Path:
    d = get_brain_home() / ".cache" / "chats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_saved_sessions() -> list[dict]:
    d = get_chats_dir()
    sessions = []
    for f in d.glob("session_*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, dict) and "id" in data:
                    sessions.append(data)
        except Exception:
            pass
    sessions.sort(key=lambda s: s.get("updated_at", s.get("created_at", "")), reverse=True)
    return sessions


def save_chat_session(session_id: str, title: str, messages: list[dict], raw_history: list[dict]):
    d = get_chats_dir()
    f = d / f"session_{session_id}.json"
    now_iso = datetime.now().astimezone().isoformat()
    created_at = now_iso
    if f.exists():
        try:
            with open(f, "r", encoding="utf-8") as fh:
                prev = json.load(fh)
                created_at = prev.get("created_at", now_iso)
        except Exception:
            pass
    data = {
        "id": session_id,
        "title": title,
        "created_at": created_at,
        "updated_at": now_iso,
        "messages": messages,
        "raw_history": raw_history
    }
    with open(f, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def delete_chat_session(session_id: str):
    d = get_chats_dir()
    f = d / f"session_{session_id}.json"
    if f.exists():
        try:
            f.unlink()
        except Exception:
            pass


class BrainChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Project Brain")
        self.root.geometry("960x760")
        self.root.minsize(680, 500)
        self.root.configure(bg=BG_DARK)

        # Configurar icono nativo de la app (cerebro.ico)
        self.setup_app_icon()

        # Barra de título de Windows sincronizada con el color exacto del header (#171717)
        self.apply_dark_titlebar()
        self.root.after(50, self.apply_dark_titlebar)

        # Centrar ventana
        self.center_window()

        self.server_mgr = LlamaServerManager()
        self.msg_queue = queue.Queue()
        self.is_generating = False
        self.conversation_history = []
        self.display_messages = []
        self.current_session_id = None
        self.bot_msg_start_index = None

        # Bloques de mensajes para el botón copiar en hover
        self.message_blocks = []
        self.active_hover_message = None
        self.mouse_over_copy_btn = False
        self._hide_copy_timer = None

        # Estado del menú lateral
        self.sidebar_visible = False

        # Estado de la animación de carga
        self.is_loading = False
        self.first_token_received = False
        self.spinner_frame_idx = 0
        self.loading_phase_text = "Buscando evidencias en las bóvedas..."

        # Configurar UI
        self.setup_ui()

        # Atajo Ctrl+H para alternar el menú lateral
        self.root.bind("<Control-h>", lambda e: self.toggle_sidebar())
        self.root.bind("<Control-H>", lambda e: self.toggle_sidebar())

        # Protocolo de cierre estricto (0 procesos en reposo)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Arrancar servidor en hilo de fondo
        self.status_label.config(text="⚪ Iniciando motor local (Qwen 1.5B)...", fg="#fbbf24")
        threading.Thread(target=self.init_backend, daemon=True).start()

        # Polling de cola de UI
        self.root.after(40, self.process_queue)

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"+{x}+{y}")

    def setup_app_icon(self):
        """Asigna cerebro.ico como icono de la ventana nativa y de la barra de tareas."""
        try:
            brain_home = get_brain_home()
            candidates = [
                brain_home / "assets" / "cerebro.ico",
                Path.home() / "Desktop" / "cerebro.ico",
                Path(r"C:\Users\alber\Desktop\cerebro.ico")
            ]
            for c in candidates:
                if c.exists():
                    self.root.iconbitmap(str(c))
                    break
        except Exception:
            pass

    def apply_dark_titlebar(self):
        """Sincroniza la barra de título nativa de Windows con el color exacto del header (#171717)."""
        if sys.platform != "win32":
            return
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()

            # Activar modo oscuro inmersivo (Windows 10 1809+ y Windows 11)
            val = ctypes.c_int(1)
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
            if res != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))

            # Pintar la barra de título con el mismo color exacto del header BG_CHAT (#171717)
            r = int(BG_CHAT[1:3], 16)
            g = int(BG_CHAT[3:5], 16)
            b = int(BG_CHAT[5:7], 16)
            caption_color = ctypes.c_int((b << 16) | (g << 8) | r)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))

            # Color del texto del título (blanco / gris suave)
            text_color = ctypes.c_int(0x00d1d5db)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))
        except Exception:
            pass

    def setup_ui(self):
        # 1. Barra superior estilo ChatGPT
        top_bar = tk.Frame(self.root, bg=BG_CHAT, height=52, highlightthickness=1, highlightbackground=BORDER_COLOR)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.pack_propagate(False)

        # Botón Hamburguesa / Sidebar
        self.sidebar_toggle_btn = tk.Button(
            top_bar,
            text="☰",
            font=("Segoe UI", 12),
            bg=BG_CHAT,
            fg=FG_TEXT,
            activebackground="#2a2a2a",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor="hand2",
            command=self.toggle_sidebar
        )
        self.sidebar_toggle_btn.pack(side=tk.LEFT, padx=(10, 4))

        title_lbl = tk.Label(top_bar, text="🧠 Project Brain", font=("Segoe UI", 12, "bold"), fg=FG_TEXT, bg=BG_CHAT)
        title_lbl.pack(side=tk.LEFT, padx=(4, 8))

        # Status label desacoplado del header para mantener una interfaz limpia estilo ChatGPT
        self.status_label = tk.Label(top_bar)

        # Botón Nuevo Chat en barra superior
        self.new_chat_top_btn = tk.Button(
            top_bar,
            text="＋ Nuevo chat",
            font=("Segoe UI", 9),
            bg=BG_INPUT,
            fg=FG_TEXT,
            activebackground="#3e3e3e",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.start_new_chat
        )
        self.new_chat_top_btn.pack(side=tk.RIGHT, padx=14)

        # 2. Contenedor principal horizontal (Sidebar + Chat)
        self.content_container = tk.Frame(self.root, bg=BG_DARK)
        self.content_container.pack(fill=tk.BOTH, expand=True)

        # Panel lateral (Sidebar) - Oculto por defecto
        self.sidebar_frame = tk.Frame(
            self.content_container,
            bg=BG_SIDEBAR,
            width=260,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR
        )
        self.sidebar_frame.pack_propagate(False)
        self.setup_sidebar_ui()

        # Panel central de Chat
        self.main_chat_frame = tk.Frame(self.content_container, bg=BG_DARK)
        self.main_chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Área de conversación
        chat_container = tk.Frame(self.main_chat_frame, bg=BG_DARK)
        chat_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(12, 6))

        self.chat_display = tk.Text(
            chat_container,
            wrap=tk.WORD,
            bg=BG_DARK,
            fg=FG_TEXT,
            font=("Segoe UI", 11),
            insertbackground=FG_TEXT,
            selectbackground=ACCENT_BLUE,
            selectforeground="#ffffff",
            relief=tk.FLAT,
            padx=15,
            pady=15,
            state=tk.DISABLED
        )

        def on_scroll_y(*args):
            self.copy_btn.place_forget()
            self.chat_display.yview(*args)

        scrollbar = tk.Scrollbar(chat_container, command=on_scroll_y, bg=BG_DARK, relief=tk.FLAT, width=10)
        self.chat_display.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tags de formato en el chat
        self.chat_display.tag_config("user_tag", foreground="#60a5fa", font=("Segoe UI", 11, "bold"), spacing1=8, spacing3=2)
        self.chat_display.tag_config("user_text", foreground="#f3f4f6", font=("Segoe UI", 11), spacing1=2, spacing3=6)
        self.chat_display.tag_config("bot_tag", foreground=ACCENT_GREEN, font=("Segoe UI", 11, "bold"), spacing1=10, spacing3=2)
        self.chat_display.tag_config("evidence_box", foreground="#94a3b8", font=("Consolas", 9), background="#1a1a1a", spacing1=2, spacing3=6)
        self.chat_display.tag_config("muted", foreground=FG_MUTED, font=("Segoe UI", 9, "italic"))
        self.chat_display.tag_config("loading_tag", foreground="#38bdf8", font=("Segoe UI", 10, "italic"), spacing1=4, spacing3=4)

        # Tags de Markdown enriquecido
        self.chat_display.tag_config("md_h1", foreground="#ffffff", font=("Segoe UI", 13, "bold"), spacing1=10, spacing3=4)
        self.chat_display.tag_config("md_h2", foreground="#f3f4f6", font=("Segoe UI", 12, "bold"), spacing1=8, spacing3=3)
        self.chat_display.tag_config("md_h3", foreground="#e5e7eb", font=("Segoe UI", 11, "bold"), spacing1=6, spacing3=2)
        self.chat_display.tag_config("md_normal", foreground=FG_TEXT, font=("Segoe UI", 11), spacing1=2, spacing3=3)
        self.chat_display.tag_config("md_list_text", foreground=FG_TEXT, font=("Segoe UI", 11), lmargin1=15, lmargin2=35, spacing1=2, spacing3=2)
        self.chat_display.tag_config("md_list_bullet", foreground=ACCENT_GREEN, font=("Segoe UI", 11, "bold"), lmargin1=15, lmargin2=35)
        self.chat_display.tag_config("md_list_num", foreground="#60a5fa", font=("Segoe UI", 11, "bold"), lmargin1=15, lmargin2=35)
        self.chat_display.tag_config("md_quote", foreground="#9ca3af", font=("Segoe UI", 10, "italic"), lmargin1=20, lmargin2=20, spacing1=3, spacing3=3)
        self.chat_display.tag_config("md_code_block", foreground="#e2e8f0", background="#18181b", font=("Consolas", 10), lmargin1=20, lmargin2=20, spacing1=4, spacing3=4)
        self.chat_display.tag_config("md_bold", foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_config("md_italic", foreground="#d1d5db", font=("Segoe UI", 11, "italic"))
        self.chat_display.tag_config("md_code_inline", foreground="#f87171", background="#2a2b32", font=("Consolas", 10))
        self.chat_display.tag_config("md_link", foreground="#38bdf8", font=("Segoe UI", 11, "underline"))
        self.chat_display.tag_config("stream_chunk", foreground=FG_TEXT, font=("Segoe UI", 11))

        # Prioridad de tags: inline sobre bloques, y 'sel' (selección) en la cima absoluta
        self.chat_display.tag_raise("md_bold")
        self.chat_display.tag_raise("md_italic")
        self.chat_display.tag_raise("md_code_inline")
        self.chat_display.tag_raise("md_code_block")
        self.chat_display.tag_raise("md_link")
        self.chat_display.tag_raise("sel")

        # Asegurar que cualquier selección mantenga la prioridad de 'sel' uniforme sobre códigos o bloques
        self.chat_display.bind("<<Selection>>", lambda e: self.chat_display.tag_raise("sel"))
        self.chat_display.bind("<Button-1>", lambda e: self.chat_display.tag_raise("sel"), add="+")
        self.chat_display.bind("<B1-Motion>", lambda e: self.chat_display.tag_raise("sel"), add="+")

        # Botón flotante para copiar mensaje en hover
        self.copy_btn = tk.Button(
            self.chat_display,
            text="📋 Copiar",
            font=("Segoe UI", 8),
            bg="#2a2b32",
            fg="#d1d5db",
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.copy_hovered_message
        )
        self.copy_btn.bind("<Enter>", lambda e: self.on_copy_btn_enter())
        self.copy_btn.bind("<Leave>", lambda e: self.on_copy_btn_leave())

        self.chat_display.bind("<Motion>", self.on_chat_motion)
        self.chat_display.bind("<Leave>", self.on_chat_leave)
        self.chat_display.bind("<MouseWheel>", lambda e: self.copy_btn.place_forget(), add="+")

        # 3. Área inferior de entrada (Estilo ChatGPT)
        bottom_frame = tk.Frame(self.main_chat_frame, bg=BG_DARK, pady=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20)

        input_box_wrapper = tk.Frame(bottom_frame, bg=BG_INPUT, highlightthickness=1, highlightbackground=BORDER_COLOR)
        input_box_wrapper.pack(fill=tk.X, expand=True)

        self.input_text = tk.Text(
            input_box_wrapper,
            height=3,
            wrap=tk.WORD,
            bg=BG_INPUT,
            fg=FG_TEXT,
            font=("Segoe UI", 11),
            insertbackground=FG_TEXT,
            relief=tk.FLAT,
            padx=12,
            pady=10
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.input_text.bind("<Return>", self.on_enter_pressed)
        self.input_text.bind("<Shift-Return>", self.on_shift_enter)
        self.input_text.bind("<KeyRelease>", self.on_input_key_release)
        self.input_text.bind("<Down>", self.on_input_arrow_down)
        self.input_text.bind("<Up>", self.on_input_arrow_up)
        self.input_text.bind("<Tab>", self.on_input_tab)
        self.input_text.bind("<Escape>", lambda e: self.hide_mention_popup())
        self.input_text.bind("<Control-Delete>", self.on_control_delete)
        self.input_text.bind("<Control-Key-Delete>", self.on_control_delete)
        self.input_text.bind("<Control-BackSpace>", self.on_control_backspace)
        self.input_text.bind("<Control-Key-BackSpace>", self.on_control_backspace)
        self.input_text.bind("<Control-a>", self.on_control_select_all)
        self.input_text.bind("<Control-A>", self.on_control_select_all)

        # Menú flotante de menciones (@proyecto)
        self.mention_popup = tk.Frame(
            self.root,
            bg="#18181b",
            highlightthickness=1,
            highlightbackground=ACCENT_BLUE
        )
        self.mention_title_lbl = tk.Label(
            self.mention_popup,
            text="PROYECTOS EN BRAIN",
            font=("Segoe UI", 7, "bold"),
            fg="#71717a",
            bg="#18181b",
            anchor="w",
            padx=8,
            pady=3
        )
        self.mention_title_lbl.pack(fill=tk.X)

        self.mention_listbox = tk.Listbox(
            self.mention_popup,
            bg="#18181b",
            fg=FG_TEXT,
            selectbackground=ACCENT_BLUE,
            selectforeground="#ffffff",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            activestyle="none"
        )
        self.mention_listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
        self.mention_listbox.bind("<ButtonRelease-1>", self.on_mention_selected)

        # Botón enviar redondo minimalista
        self.send_btn = tk.Button(
            input_box_wrapper,
            text="▲",
            font=("Segoe UI", 12, "bold"),
            bg=ACCENT_GREEN,
            fg="#ffffff",
            activebackground="#0e8c6d",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            width=3,
            height=1,
            cursor="hand2",
            command=self.submit_message
        )
        self.send_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        self.append_system_message("Bienvenido a Project Brain Chat. Haz cualquier pregunta sobre tus notas, decisiones, proyectos o arquitectura.")

    def on_copy_btn_enter(self):
        self.mouse_over_copy_btn = True
        if self._hide_copy_timer:
            self.root.after_cancel(self._hide_copy_timer)
            self._hide_copy_timer = None
        self.copy_btn.config(bg="#3f3f46", fg="#ffffff")

    def on_copy_btn_leave(self):
        self.mouse_over_copy_btn = False
        self.copy_btn.config(bg="#2a2b32", fg="#d1d5db")
        self.schedule_hide_copy_btn()

    def schedule_hide_copy_btn(self):
        if self._hide_copy_timer:
            self.root.after_cancel(self._hide_copy_timer)
        self._hide_copy_timer = self.root.after(250, self._check_and_hide_copy_btn)

    def _check_and_hide_copy_btn(self):
        self._hide_copy_timer = None
        if self.mouse_over_copy_btn:
            return
        try:
            px = self.root.winfo_pointerx()
            py = self.root.winfo_pointery()
            bx = self.copy_btn.winfo_rootx()
            by = self.copy_btn.winfo_rooty()
            bw = self.copy_btn.winfo_width()
            bh = self.copy_btn.winfo_height()
            if bx <= px <= bx + bw and by <= py <= by + bh:
                self.mouse_over_copy_btn = True
                return
        except Exception:
            pass
        self.copy_btn.place_forget()
        self.active_hover_message = None

    def copy_hovered_message(self):
        if not self.active_hover_message:
            return
        text_to_copy = self.active_hover_message.get("text", "").strip()
        if not text_to_copy:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text_to_copy)
        self.copy_btn.config(text="✓ Copiado", fg="#10a37f")
        self.root.after(1400, lambda: self.copy_btn.config(text="📋 Copiar", fg="#d1d5db"))

    def on_chat_motion(self, event):
        if self.mouse_over_copy_btn:
            if self._hide_copy_timer:
                self.root.after_cancel(self._hide_copy_timer)
                self._hide_copy_timer = None
            return

        try:
            curr_idx = self.chat_display.index(f"@{event.x},{event.y}")
        except Exception:
            return

        hovered = None
        for block in self.message_blocks:
            try:
                if self.chat_display.compare(curr_idx, ">=", block["start"]) and self.chat_display.compare(curr_idx, "<=", block["end"]):
                    hovered = block
                    break
            except Exception:
                pass

        if hovered:
            if self._hide_copy_timer:
                self.root.after_cancel(self._hide_copy_timer)
                self._hide_copy_timer = None
            self.active_hover_message = hovered
            try:
                # Posicionar abajo a la derecha de ese mensaje
                bbox = self.chat_display.bbox(f"{hovered['end']}-2c")
                if bbox:
                    btn_w = 82
                    x = max(10, self.chat_display.winfo_width() - btn_w - 20)
                    y = max(5, bbox[1] - 4)
                    self.copy_btn.place(x=x, y=y)
                    self.copy_btn.lift()
                    return
            except Exception:
                pass

        self.schedule_hide_copy_btn()

    def on_chat_leave(self, event):
        self.schedule_hide_copy_btn()

    def get_available_projects(self) -> list[str]:
        """Obtiene la lista de bóvedas/proyectos disponibles en Project Brain."""
        try:
            vaults = get_all_vaults(get_brain_home())
            projs = [v.name for v in vaults if v.name != "_global"]
            return sorted(projs)
        except Exception:
            return ["dj", "portafolio-dev", "project-brain"]

    def on_input_key_release(self, event):
        """Detecta si el usuario está escribiendo una mención @proyecto y muestra autocompletado."""
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        try:
            cursor_pos = self.input_text.index(tk.INSERT)
            line_text = self.input_text.get(f"{cursor_pos} linestart", cursor_pos)
            m = re.search(r"@([a-zA-Z0-9_-]*)$", line_text)
            if m:
                filter_term = m.group(1).lower()
                all_projs = self.get_available_projects()
                matches = [p for p in all_projs if filter_term in p.lower()]
                if matches:
                    self.show_mention_popup(matches)
                    return
        except Exception:
            pass

        self.hide_mention_popup()

    def show_mention_popup(self, matches: list[str]):
        """Muestra el popup desplegable flotante con las menciones sugeridas."""
        self.mention_listbox.delete(0, tk.END)
        for p in matches:
            self.mention_listbox.insert(tk.END, f"  @{p}")
        self.mention_listbox.selection_set(0)

        try:
            self.root.update_idletasks()
            ix = self.input_text.winfo_rootx() - self.root.winfo_rootx()
            iy = self.input_text.winfo_rooty() - self.root.winfo_rooty()
            h = min(140, max(50, len(matches) * 24 + 26))
            w = 210
            self.mention_popup.place(x=ix + 12, y=iy - h - 4, width=w, height=h)
            self.mention_popup.lift()
        except Exception:
            pass

    def hide_mention_popup(self):
        """Oculta el menú desplegable de menciones."""
        if self.mention_popup.winfo_ismapped():
            self.mention_popup.place_forget()

    def on_input_arrow_down(self, event):
        if self.mention_popup.winfo_ismapped():
            cur = self.mention_listbox.curselection()
            idx = cur[0] if cur else 0
            if idx < self.mention_listbox.size() - 1:
                self.mention_listbox.selection_clear(0, tk.END)
                self.mention_listbox.selection_set(idx + 1)
                self.mention_listbox.see(idx + 1)
            return "break"
        return None

    def on_input_arrow_up(self, event):
        if self.mention_popup.winfo_ismapped():
            cur = self.mention_listbox.curselection()
            idx = cur[0] if cur else 0
            if idx > 0:
                self.mention_listbox.selection_clear(0, tk.END)
                self.mention_listbox.selection_set(idx - 1)
                self.mention_listbox.see(idx - 1)
            return "break"
        return None

    def on_input_tab(self, event):
        if self.mention_popup.winfo_ismapped():
            self.insert_selected_mention()
            return "break"
        return None

    def on_mention_selected(self, event):
        self.insert_selected_mention()

    def insert_selected_mention(self):
        """Inserta el proyecto seleccionado de la lista de menciones."""
        cur = self.mention_listbox.curselection()
        if not cur:
            self.hide_mention_popup()
            return
        selected_text = self.mention_listbox.get(cur[0]).strip().lstrip("@")

        try:
            cursor_pos = self.input_text.index(tk.INSERT)
            line_text = self.input_text.get(f"{cursor_pos} linestart", cursor_pos)
            m = re.search(r"@([a-zA-Z0-9_-]*)$", line_text)
            if m:
                start_idx = f"{cursor_pos} - {len(m.group(0))}c"
                self.input_text.delete(start_idx, cursor_pos)
                self.input_text.insert(start_idx, f"@{selected_text} ")
        except Exception:
            pass

        self.hide_mention_popup()
        self.input_text.focus_set()

    def on_control_delete(self, event=None):
        """Elimina la palabra siguiente hacia la derecha del cursor (estándar Windows Ctrl+Delete)."""
        try:
            if self.input_text.tag_ranges("sel"):
                self.input_text.delete("sel.first", "sel.last")
                return "break"

            text_after = self.input_text.get("insert", "end-1c")
            if not text_after:
                return "break"

            if text_after.startswith("\r\n") or text_after.startswith("\n"):
                m = re.match(r"^\r?\n[ \t]*", text_after)
                count = len(m.group(0)) if m else 1
            elif text_after[0] in " \t":
                m = re.match(r"^[ \t]+(\w+|[^\w\s]+)?", text_after)
                count = len(m.group(0)) if m else 1
            elif text_after[0].isalnum() or text_after[0] == "_":
                m = re.match(r"^\w+", text_after)
                count = len(m.group(0)) if m else 1
            else:
                m = re.match(r"^[^\w\s]+", text_after)
                count = len(m.group(0)) if m else 1

            if count > 0:
                self.input_text.delete("insert", f"insert+{count}c")
        except Exception:
            pass
        return "break"

    def on_control_backspace(self, event=None):
        """Elimina la palabra anterior hacia la izquierda del cursor (estándar Windows Ctrl+Backspace)."""
        try:
            if self.input_text.tag_ranges("sel"):
                self.input_text.delete("sel.first", "sel.last")
                return "break"

            text_before = self.input_text.get("1.0", "insert")
            if not text_before:
                return "break"

            rev = text_before[::-1]
            if rev.startswith("\n\r") or rev.startswith("\n"):
                m = re.match(r"^\r?\n[ \t]*", rev)
                count = len(m.group(0)) if m else 1
            elif rev[0] in " \t":
                m = re.match(r"^[ \t]+(\w+|[^\w\s]+)?", rev)
                count = len(m.group(0)) if m else 1
            elif rev[0].isalnum() or rev[0] == "_":
                m = re.match(r"^\w+", rev)
                count = len(m.group(0)) if m else 1
            else:
                m = re.match(r"^[^\w\s]+", rev)
                count = len(m.group(0)) if m else 1

            if count > 0:
                self.input_text.delete(f"insert-{count}c", "insert")
        except Exception:
            pass
        return "break"

    def on_control_select_all(self, event=None):
        """Selecciona todo el texto del cuadro de entrada con Ctrl+A."""
        try:
            self.input_text.tag_add("sel", "1.0", "end-1c")
        except Exception:
            pass
        return "break"

    def setup_sidebar_ui(self):
        """Configura los elementos internos del menú lateral de historial."""
        sidebar_top = tk.Frame(self.sidebar_frame, bg=BG_SIDEBAR, pady=12, padx=12)
        sidebar_top.pack(fill=tk.X)

        lbl = tk.Label(sidebar_top, text="Historial de chats", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg=BG_SIDEBAR)
        lbl.pack(side=tk.LEFT)

        close_btn = tk.Button(
            sidebar_top,
            text="✕",
            font=("Segoe UI", 9),
            bg=BG_SIDEBAR,
            fg=FG_MUTED,
            activebackground=BG_SIDEBAR_HOVER,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            cursor="hand2",
            command=self.toggle_sidebar
        )
        close_btn.pack(side=tk.RIGHT)

        new_btn = tk.Button(
            self.sidebar_frame,
            text="＋ Nuevo Chat",
            font=("Segoe UI", 9, "bold"),
            bg=BG_SIDEBAR_HOVER,
            fg="#ffffff",
            activebackground="#3f3f46",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=6,
            cursor="hand2",
            command=self.start_new_chat
        )
        new_btn.pack(fill=tk.X, padx=12, pady=(0, 10))

        div = tk.Frame(self.sidebar_frame, height=1, bg=BORDER_COLOR)
        div.pack(fill=tk.X, padx=12, pady=4)

        sec_lbl = tk.Label(self.sidebar_frame, text="SESIONES GUARDADAS", font=("Segoe UI", 8, "bold"), fg="#71717a", bg=BG_SIDEBAR)
        sec_lbl.pack(anchor="w", padx=14, pady=(6, 4))

        self.sidebar_canvas = tk.Canvas(self.sidebar_frame, bg=BG_SIDEBAR, highlightthickness=0)
        self.sidebar_scrollbar = tk.Scrollbar(self.sidebar_frame, orient="vertical", command=self.sidebar_canvas.yview, bg=BG_SIDEBAR, width=6)
        self.sidebar_scroll_frame = tk.Frame(self.sidebar_canvas, bg=BG_SIDEBAR)

        self.sidebar_scroll_frame.bind(
            "<Configure>",
            lambda e: self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        )
        self.sidebar_canvas_win = self.sidebar_canvas.create_window((0, 0), window=self.sidebar_scroll_frame, anchor="nw")
        self.sidebar_canvas.bind("<Configure>", lambda e: self.sidebar_canvas.itemconfig(self.sidebar_canvas_win, width=e.width))
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scrollbar.set)

        # Footer inferior del sidebar con información del modelo (estilo ChatGPT)
        sidebar_footer = tk.Frame(self.sidebar_frame, bg=BG_SIDEBAR, pady=10, padx=14)
        sidebar_footer.pack(side=tk.BOTTOM, fill=tk.X)

        div_bottom = tk.Frame(self.sidebar_frame, height=1, bg=BORDER_COLOR)
        div_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 4))

        model_badge = tk.Label(
            sidebar_footer,
            text="⚡ Qwen 2.5 1.5B",
            font=("Segoe UI", 9),
            fg=FG_MUTED,
            bg=BG_SIDEBAR
        )
        model_badge.pack(side=tk.LEFT)

        self.sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

    def toggle_sidebar(self):
        """Abre o cierra el menú lateral estilo ChatGPT."""
        if self.sidebar_visible:
            self.sidebar_frame.pack_forget()
            self.sidebar_visible = False
            self.sidebar_toggle_btn.config(bg=BG_CHAT)
        else:
            self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, before=self.main_chat_frame)
            self.sidebar_visible = True
            self.sidebar_toggle_btn.config(bg=BG_SIDEBAR_ACTIVE)
            self.refresh_sidebar_sessions()

    def refresh_sidebar_sessions(self):
        """Recarga la lista de sesiones guardadas en el panel lateral."""
        for w in self.sidebar_scroll_frame.winfo_children():
            w.destroy()

        sessions = list_saved_sessions()
        if not sessions:
            empty_lbl = tk.Label(
                self.sidebar_scroll_frame,
                text="No hay sesiones previas.\nEnvía un mensaje para comenzar.",
                font=("Segoe UI", 9, "italic"),
                fg=FG_MUTED,
                bg=BG_SIDEBAR,
                justify=tk.CENTER,
                pady=20
            )
            empty_lbl.pack(fill=tk.X, padx=10)
            return

        for sess in sessions:
            sess_id = sess.get("id")
            title = sess.get("title", "Conversación sin título")
            is_active = (sess_id == self.current_session_id)

            item_bg = BG_SIDEBAR_ACTIVE if is_active else BG_SIDEBAR

            item_frame = tk.Frame(
                self.sidebar_scroll_frame,
                bg=item_bg,
                cursor="hand2",
                pady=6,
                padx=8,
                highlightthickness=1,
                highlightbackground="#3f3f46" if is_active else BG_SIDEBAR
            )
            item_frame.pack(fill=tk.X, pady=2, padx=4)

            txt_box = tk.Frame(item_frame, bg=item_bg, cursor="hand2")
            txt_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            short_title = title if len(title) <= 24 else title[:22] + "..."
            t_lbl = tk.Label(
                txt_box,
                text=short_title,
                font=("Segoe UI", 9, "bold" if is_active else "normal"),
                fg="#ffffff" if is_active else FG_TEXT,
                bg=item_bg,
                anchor="w",
                cursor="hand2"
            )
            t_lbl.pack(anchor="w")

            created_str = sess.get("created_at", "")[:16].replace("T", " ")
            d_lbl = tk.Label(
                txt_box,
                text=created_str,
                font=("Segoe UI", 8),
                fg="#71717a",
                bg=item_bg,
                anchor="w",
                cursor="hand2"
            )
            d_lbl.pack(anchor="w")

            del_btn = tk.Button(
                item_frame,
                text="✕",
                font=("Segoe UI", 8),
                bg=item_bg,
                fg="#71717a",
                activebackground="#dc2626",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                padx=4,
                pady=2,
                command=lambda s_id=sess_id: self.delete_session_clicked(s_id)
            )
            del_btn.pack(side=tk.RIGHT, padx=2)

            def on_click(e, s_id=sess_id):
                self.load_session_clicked(s_id)

            def on_enter(e, f=item_frame, tb=txt_box, tl=t_lbl, dl=d_lbl, db=del_btn, active=is_active):
                if not active:
                    for widget in (f, tb, tl, dl, db):
                        widget.config(bg=BG_SIDEBAR_HOVER)

            def on_leave(e, f=item_frame, tb=txt_box, tl=t_lbl, dl=d_lbl, db=del_btn, active=is_active):
                if not active:
                    for widget in (f, tb, tl, dl, db):
                        widget.config(bg=BG_SIDEBAR)

            for widget in (item_frame, txt_box, t_lbl, d_lbl):
                widget.bind("<Button-1>", on_click)
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)

    def load_session_clicked(self, session_id: str):
        """Carga una conversación guardada en el área de chat."""
        if self.is_generating:
            return

        sessions = list_saved_sessions()
        target = next((s for s in sessions if s.get("id") == session_id), None)
        if not target:
            return

        self.current_session_id = session_id
        self.conversation_history = target.get("raw_history", [])
        self.display_messages = target.get("messages", [])
        self.message_blocks = []
        self.copy_btn.place_forget()

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)

        for m in self.display_messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                start_idx = self.chat_display.index("end-1c")
                self.chat_display.insert(tk.END, "\nTú\n", "user_tag")
                self.chat_display.insert(tk.END, f"{content}\n\n", "user_text")
                end_idx = self.chat_display.index("end-1c")
                self.message_blocks.append({"role": "user", "text": content, "start": start_idx, "end": end_idx})
            elif role == "assistant":
                self.chat_display.insert(tk.END, "Brain AI\n", "bot_tag")
                start_idx = self.chat_display.index("end-1c")
                self.render_markdown(content)
                self.chat_display.insert(tk.END, "\n\n")
                end_idx = self.chat_display.index("end-1c")
                self.message_blocks.append({"role": "assistant", "text": content, "start": start_idx, "end": end_idx})

        self.chat_display.tag_raise("sel")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        self.refresh_sidebar_sessions()

    def start_new_chat(self):
        """Reinicia la conversación actual para empezar un nuevo chat limpio."""
        if self.is_generating:
            return

        self.current_session_id = None
        self.conversation_history = []
        self.display_messages = []
        self.message_blocks = []
        self.copy_btn.place_forget()
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.append_system_message("Nueva conversación iniciada. Puedes formular tu pregunta.")
        if self.sidebar_visible:
            self.refresh_sidebar_sessions()

    def delete_session_clicked(self, session_id: str):
        """Elimina una sesión guardada."""
        delete_chat_session(session_id)
        if self.current_session_id == session_id:
            self.start_new_chat()
        else:
            self.refresh_sidebar_sessions()

    def init_backend(self):
        try:
            try:
                from brain_index import build_index
                build_index()
            except Exception:
                pass

            ok = self.server_mgr.start()
            if ok:
                self.msg_queue.put(("STATUS", ("🟢 Motor listo (0 MB en reposo al cerrar)", "#10a37f")))
            else:
                self.msg_queue.put(("STATUS", ("🔴 Error al iniciar motor", "#ef4444")))
        except Exception as e:
            self.msg_queue.put(("STATUS", (f"🔴 {e}", "#ef4444")))

    def on_enter_pressed(self, event):
        if self.mention_popup.winfo_ismapped():
            self.insert_selected_mention()
            return "break"

        if not event.state & 0x1:
            self.submit_message()
            return "break"
        return None

    def on_shift_enter(self, event):
        return None

    def submit_message(self):
        if self.is_generating:
            return

        query = self.input_text.get("1.0", tk.END).strip()
        if not query:
            return

        if not self.current_session_id:
            self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.input_text.delete("1.0", tk.END)
        self.is_generating = True
        self.send_btn.config(state=tk.DISABLED, bg=BG_INPUT, fg=FG_MUTED)
        self.status_label.config(text="🟡 Consultando memoria y razonando...", fg="#fbbf24")

        # 1. Mostrar mensaje de usuario
        self.append_user_message(query)
        self.display_messages.append({"role": "user", "content": query})

        # 2. Insertar cabecera del bot (la respuesta estará inmediatamente en la siguiente línea)
        self.is_loading = True
        self.first_token_received = False
        self.spinner_frame_idx = 0
        self.loading_phase_text = "Buscando evidencias en las bóvedas..."

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "Brain AI\n", "bot_tag")

        # Región para el cartel de evidencia (se inserta si se encuentra y se oculta al soltar texto)
        self.chat_display.mark_set("evidence_start", "end-1c")
        self.chat_display.mark_gravity("evidence_start", tk.LEFT)
        self.chat_display.mark_set("evidence_end", "end-1c")
        self.chat_display.mark_gravity("evidence_end", tk.RIGHT)

        # Región para el spinner animado (gira mientras busca y mientras razona)
        self.chat_display.mark_set("loading_start", "end-1c")
        self.chat_display.mark_gravity("loading_start", tk.LEFT)
        init_frame = SPINNER_FRAMES[0]
        self.chat_display.insert("end", f"✦ {init_frame} {self.loading_phase_text}\n", "loading_tag")
        self.chat_display.mark_set("loading_end", "end-1c")
        self.chat_display.mark_gravity("loading_end", tk.RIGHT)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

        # Iniciar ciclo de animación
        self.tick_loading_animation()

        # Iniciar inferencia en segundo plano
        threading.Thread(target=self.generate_response, args=(query,), daemon=True).start()

    def tick_loading_animation(self):
        """Actualiza el spinner de carga en el chat mientras se recopilan evidencias."""
        if not self.is_loading:
            return

        try:
            if "loading_start" in self.chat_display.mark_names() and "loading_end" in self.chat_display.mark_names():
                self.spinner_frame_idx += 1
                f = SPINNER_FRAMES[self.spinner_frame_idx % len(SPINNER_FRAMES)]
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete("loading_start", "loading_end")
                self.chat_display.insert("loading_start", f"✦ {f} {self.loading_phase_text}\n", "loading_tag")
                self.chat_display.config(state=tk.DISABLED)
        except Exception:
            pass

        self.root.after(80, self.tick_loading_animation)

    def generate_response(self, query: str):
        # 1. Extraer paquete de evidencia con brain_ask (BM25 y Git sin cmds emergentes)
        self.msg_queue.put(("LOADING_PHASE", "Buscando notas y evidencias en las bóvedas..."))
        evidence_pkg = build_evidence_package(query)
        has_evidence = evidence_pkg.get("status") == "success" and len(evidence_pkg.get("notes", [])) > 0

        self.msg_queue.put(("LOADING_PHASE", "Analizando contexto y commits en git..."))

        # Construir prompt
        system_content = (
            "Eres el asistente técnico de Project Brain, la infraestructura de memoria y documentación del usuario. "
            "Project Brain almacena las notas, arquitectura, decisiones y sesiones de múltiples proyectos del usuario (como 'dj', 'portafolio-dev', etc.).\n"
            "Tu misión es responder preguntas sobre estos proyectos de forma concisa, precisa y en español, basándote en la evidencia provista.\n"
        )

        if has_evidence:
            system_content += "\nEVIDENCIA Y NOTAS REGISTRADAS EN LA BÓVEDA:\n"
            b_home = get_brain_home()

            for n in evidence_pkg.get("notes", [])[:4]:
                system_content += f"\n### Nota: [[{n['title']}]] (Proyecto: {n.get('project', 'general')} | Tipo: {n.get('type', 'nota')})\n"
                note_path = b_home / n.get("path", "")
                if note_path.exists() and n.get("type") in ["context", "decision", "learning", "session"]:
                    _, body_text = read_note(note_path)
                    clean_body = body_text.strip()[:1400]
                    system_content += f"{clean_body}\n"
                else:
                    for sn in n.get("snippets", [])[:3]:
                        system_content += f"- Extracto: {sn}\n"

            if evidence_pkg.get("timeline"):
                system_content += "\nLÍNEA TEMPORAL DE COMMITS Y EVENTOS (MÁS RECIENTES PRIMERO):\n"
                sorted_timeline = sorted(evidence_pkg["timeline"], key=lambda x: str(x.get("timestamp", "")), reverse=True)
                for ev in sorted_timeline[:8]:
                    system_content += f"- [{ev.get('timestamp', '')}] {ev.get('title', '')} ({ev.get('detail', '')})\n"

            system_content += (
                "\nInstrucciones de respuesta:\n"
                "- Si el usuario pregunta por el último cambio, cita el commit, sesión o fecha más reciente disponible en la evidencia.\n"
                "- Explica qué se implementó, archivos modificados y decisiones técnicas clave.\n"
                "- Redacta en español formal y conciso, sin repetir palabras ni bucles."
            )
        else:
            system_content += "\nLa base de documentación de Project Brain no contiene notas relevantes sobre esta consulta específica. Infórmalo con total transparencia."

        if has_evidence:
            self.msg_queue.put(("EVIDENCE_FOUND", True))

        self.msg_queue.put(("LOADING_PHASE", "Razonando respuesta con el modelo local..."))

        messages = [
            {"role": "system", "content": system_content}
        ]
        for m in self.conversation_history[-4:]:
            messages.append(m)
        messages.append({"role": "user", "content": query})

        accumulated = []
        stop_streaming = False

        def clean_repetition(text: str) -> str:
            words = text.split()
            for cycle_len in range(1, 6):
                for repeats in range(6, 2, -1):
                    if len(words) >= cycle_len * repeats:
                        chunks = [words[-cycle_len * (i + 1) : len(words) - cycle_len * i] for i in range(repeats)]
                        if all(c == chunks[0] for c in chunks):
                            keep_words = words[: -cycle_len * (repeats - 1)]
                            return " ".join(keep_words).rstrip(" ,;:-") + "."
            return text

        def check_repetition(text: str) -> bool:
            words = text.split()
            if len(words) < 8:
                return False
            for cycle_len in range(1, 6):
                if len(words) >= cycle_len * 3:
                    chunks = [words[-cycle_len * (i + 1) : len(words) - cycle_len * i] for i in range(3)]
                    if all(c == chunks[0] for c in chunks):
                        return True
            return False

        def on_token(token: str):
            nonlocal stop_streaming
            if stop_streaming:
                return False
            accumulated.append(token)
            curr_text = "".join(accumulated)
            if check_repetition(curr_text):
                stop_streaming = True
                return False
            self.msg_queue.put(("TOKEN", token))
            return True

        stream_chat_completion(messages, on_token, port=self.server_mgr.port)

        full_answer = "".join(accumulated)
        if check_repetition(full_answer):
            full_answer = clean_repetition(full_answer)

        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": full_answer})

        self.display_messages.append({"role": "assistant", "content": full_answer, "evidence": has_evidence})

        # Guardar automáticamente la sesión en disco
        session_title = self.display_messages[0]["content"][:30].strip()
        save_chat_session(
            self.current_session_id,
            session_title,
            self.display_messages,
            self.conversation_history
        )

        self.msg_queue.put(("FINISH_BOT_MESSAGE", full_answer))

    def append_user_message(self, text: str):
        self.chat_display.config(state=tk.NORMAL)
        start_idx = self.chat_display.index("end-1c")
        self.chat_display.insert(tk.END, "\nTú\n", "user_tag")
        self.chat_display.insert(tk.END, f"{text}\n\n", "user_text")
        end_idx = self.chat_display.index("end-1c")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        self.message_blocks.append({
            "role": "user",
            "text": text,
            "start": start_idx,
            "end": end_idx
        })

    def insert_inline_formatted(self, text: str, base_tag: str = "md_normal"):
        """Parsea e inserta formato inline: negrita, cursiva, código, enlaces y wikilinks."""
        pattern = re.compile(r'(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[\[[^\]]+\]\]|\[([^\]]+)\]\(([^)]+)\))')
        pos = 0
        for match in pattern.finditer(text):
            start, end = match.span()
            if start > pos:
                self.chat_display.insert(tk.END, text[pos:start], base_tag)
            token = match.group(0)
            if token.startswith('`') and token.endswith('`'):
                self.chat_display.insert(tk.END, token[1:-1], ("md_code_inline", base_tag))
            elif (token.startswith('**') and token.endswith('**')) or (token.startswith('__') and token.endswith('__')):
                self.chat_display.insert(tk.END, token[2:-2], ("md_bold", base_tag))
            elif (token.startswith('*') and token.endswith('*')) or (token.startswith('_') and token.endswith('_')):
                self.chat_display.insert(tk.END, token[1:-1], ("md_italic", base_tag))
            elif token.startswith('[[') and token.endswith(']]'):
                clean_link = token[2:-2].split("|")[-1]
                self.chat_display.insert(tk.END, f"[[{clean_link}]]", ("md_link", base_tag))
            elif match.group(2) and match.group(3):
                self.chat_display.insert(tk.END, match.group(2), ("md_link", base_tag))
            pos = end

        if pos < len(text):
            self.chat_display.insert(tk.END, text[pos:], base_tag)

    def render_markdown(self, markdown_text: str):
        """Renderiza Markdown completo con bloques, listas, código y estilos."""
        lines = markdown_text.splitlines()
        in_code_block = False
        code_block_lines = []

        for line in lines:
            stripped = line.strip()

            # 1. Bloques de código multilínea ```
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                    block_text = "\n".join(code_block_lines) + "\n"
                    self.chat_display.insert(tk.END, block_text, "md_code_block")
                    code_block_lines = []
                else:
                    in_code_block = True
                    code_block_lines = []
                continue

            if in_code_block:
                code_block_lines.append(line)
                continue

            # 2. Encabezados (#, ##, ###, ####...)
            if stripped.startswith("#"):
                m_h = re.match(r"^(#{1,6})\s+(.*)", stripped)
                if m_h:
                    hashes, title_text = m_h.groups()
                    h_level = min(len(hashes), 3)
                    tag = f"md_h{h_level}"
                    self.insert_inline_formatted(title_text + "\n", base_tag=tag)
                    continue

            # 3. Blockquotes (> cita)
            if stripped.startswith(">"):
                quote_text = re.sub(r"^>\s*", "", stripped)
                self.insert_inline_formatted(quote_text + "\n", base_tag="md_quote")
                continue

            # 4. Listas numeradas (ej. 1. **Objetivo**: ...)
            m_num = re.match(r"^(\s*\d+\.\s+)(.*)", line)
            if m_num:
                num_prefix, rest = m_num.groups()
                self.chat_display.insert(tk.END, num_prefix, ("md_list_num", "md_list_text"))
                self.insert_inline_formatted(rest + "\n", base_tag="md_list_text")
                continue

            # 5. Listas con viñeta (ej. - item, * item, • item)
            m_bul = re.match(r"^(\s*[-*•]\s+)(.*)", line)
            if m_bul:
                _, rest = m_bul.groups()
                self.chat_display.insert(tk.END, "• ", ("md_list_bullet", "md_list_text"))
                self.insert_inline_formatted(rest + "\n", base_tag="md_list_text")
                continue

            # 6. Párrafo normal o línea en blanco
            if not stripped:
                self.chat_display.insert(tk.END, "\n")
            else:
                self.insert_inline_formatted(line + "\n", base_tag="md_normal")

        if in_code_block and code_block_lines:
            self.chat_display.insert(tk.END, "\n".join(code_block_lines) + "\n", "md_code_block")

    def append_system_message(self, text: str):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"ℹ {text}\n\n", "muted")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "STATUS":
                    txt, col = data
                    self.status_label.config(text=txt, fg=col)
                elif msg_type == "LOADING_PHASE":
                    self.loading_phase_text = data
                elif msg_type == "EVIDENCE_FOUND":
                    # Mostrar que se halló evidencia mientras el spinner sigue girando debajo
                    if "evidence_start" in self.chat_display.mark_names():
                        self.chat_display.config(state=tk.NORMAL)
                        self.chat_display.insert("evidence_start", "[✓ Evidencia encontrada en la bóveda]\n\n", "evidence_box")
                        self.chat_display.config(state=tk.DISABLED)
                        self.chat_display.see(tk.END)
                elif msg_type == "TOKEN":
                    # Al llegar el primer token de texto, ocultar evidencia y spinner
                    if not self.first_token_received:
                        self.first_token_received = True
                        self.is_loading = False
                        self.chat_display.config(state=tk.NORMAL)
                        if "loading_start" in self.chat_display.mark_names() and "loading_end" in self.chat_display.mark_names():
                            try:
                                self.chat_display.delete("loading_start", "loading_end")
                            except Exception:
                                pass
                        if "evidence_start" in self.chat_display.mark_names() and "evidence_end" in self.chat_display.mark_names():
                            try:
                                self.chat_display.delete("evidence_start", "evidence_end")
                            except Exception:
                                pass

                        # Garantizar que la respuesta comience en la línea inmediatamente debajo de "Brain AI" (exactamente 1 salto de línea)
                        actual_text = self.chat_display.get("1.0", "end-1c")
                        while actual_text.endswith("\n\n"):
                            self.chat_display.delete("end-2c")
                            actual_text = self.chat_display.get("1.0", "end-1c")
                        if not actual_text.endswith("\n"):
                            self.chat_display.insert(tk.END, "\n")

                        self.bot_msg_start_index = self.chat_display.index("end-1c")

                    self.chat_display.insert(tk.END, data, "stream_chunk")
                    self.chat_display.see(tk.END)
                elif msg_type == "FINISH_BOT_MESSAGE":
                    if not self.first_token_received:
                        self.first_token_received = True
                        self.is_loading = False
                        self.chat_display.config(state=tk.NORMAL)
                        if "loading_start" in self.chat_display.mark_names() and "loading_end" in self.chat_display.mark_names():
                            try:
                                self.chat_display.delete("loading_start", "loading_end")
                            except Exception:
                                pass
                        if "evidence_start" in self.chat_display.mark_names() and "evidence_end" in self.chat_display.mark_names():
                            try:
                                self.chat_display.delete("evidence_start", "evidence_end")
                            except Exception:
                                pass
                        self.bot_msg_start_index = self.chat_display.index("end-1c")

                    if self.bot_msg_start_index:
                        try:
                            self.chat_display.delete(self.bot_msg_start_index, tk.END)
                        except Exception:
                            pass

                    # Asegurar exactamente 1 salto de línea antes de renderizar la respuesta final
                    actual_text = self.chat_display.get("1.0", "end-1c")
                    while actual_text.endswith("\n\n"):
                        self.chat_display.delete("end-2c")
                        actual_text = self.chat_display.get("1.0", "end-1c")
                    if not actual_text.endswith("\n"):
                        self.chat_display.insert(tk.END, "\n")

                    bot_render_start = self.chat_display.index("end-1c")
                    try:
                        self.render_markdown(data if data else "")
                    except Exception:
                        pass

                    end_idx = self.chat_display.index("end-1c")
                    self.message_blocks.append({
                        "role": "assistant",
                        "text": data if data else "",
                        "start": bot_render_start,
                        "end": end_idx
                    })
                    self.bot_msg_start_index = None

                    self.chat_display.insert(tk.END, "\n\n")
                    self.chat_display.tag_raise("sel")
                    self.chat_display.config(state=tk.DISABLED)
                    self.chat_display.see(tk.END)
                    self.is_generating = False
                    self.send_btn.config(state=tk.NORMAL, bg=ACCENT_GREEN, fg="#ffffff")
                    self.status_label.config(text="🟢 Motor listo (0 MB en reposo al cerrar)", fg="#10a37f")
                    if self.sidebar_visible:
                        self.refresh_sidebar_sessions()
        except queue.Empty:
            pass
        self.root.after(40, self.process_queue)

    def on_close(self):
        """Cierre inmediato y eliminación de todo proceso en memoria."""
        try:
            self.status_label.config(text="Deteniendo procesos...", fg="#ef4444")
            self.root.update()
        except Exception:
            pass
        self.server_mgr.stop()
        self.root.destroy()
        sys.exit(0)


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("projectbrain.chat.desktop.1.0")
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    app = BrainChatApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
