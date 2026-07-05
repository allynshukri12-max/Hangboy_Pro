"""
================================================================================
                                HANGBOY PRO
            Premium Desktop Client Interface Engine - Competitive Edition
================================================================================
"""

from __future__ import annotations
import math
import random
import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple

import config
from network_utils import recv_msg, send_msg

# ---------------- GRAPHICS INFRASTRUCTURE MODULES ---------------- #

class ParticleBackground(tk.Canvas):
    """Subtle drifting glowing pink ambient particle matrix background simulation."""
    def __init__(self, parent: Any, **kwargs: Any) -> None:
        super().__init__(parent, bg=config.COLOR_BG, highlightthickness=0, bd=0, **kwargs)
        self.particles: List[Dict[str, Any]] = []
        self.active = True
        self.bind("<Configure>", self._on_resize)
        self._init_simulation_pool()
        self._execution_loop()

    def _init_simulation_pool(self) -> None:
        for _ in range(30):
            self.particles.append({
                "x": random.uniform(10, 900),
                "y": random.uniform(10, 580),
                "vx": random.uniform(-0.2, 0.2),
                "vy": random.uniform(-0.3, -0.1),
                "radius": random.uniform(2.0, 3.5)
            })

    def _on_resize(self, event: tk.ConfigureEvent) -> None:
        self.w = event.width
        self.h = event.height

    def _execution_loop(self) -> None:
        if not self.active or not self.winfo_exists(): return
        self.delete("p")
        w = getattr(self, "w", self.winfo_width())
        h = getattr(self, "h", self.winfo_height())

        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["x"] < 0 or p["x"] > w: p["vx"] *= -1
            if p["y"] < 0:
                p["y"] = h
                p["x"] = random.uniform(0, w)

            self.create_oval(
                p["x"] - p["radius"], p["y"] - p["radius"],
                p["x"] + p["radius"], p["y"] + p["radius"],
                fill=config.COLOR_PANEL, outline=config.COLOR_PRIMARY, width=1, tags="p"
            )
        self.after(33, self._execution_loop)

class RoundedButton(tk.Canvas):
    """Interactive smooth canvas control button with modern hover and click transitions."""
    def __init__(self, parent: Any, text: str, command: Any, bg: str = config.COLOR_PRIMARY, width: int = 140, height: int = 36) -> None:
        super().__init__(parent, width=width, height=height, bg=parent["bg"], highlightthickness=0, bd=0, cursor="hand2")
        self.command = command
        self.text = text
        self.base_bg = bg
        self.w = width
        self.h = height

        self.poly_id = self._render_shape(0, fill=self.base_bg)
        self.text_id = self.create_text(self.w // 2, self.h // 2, text=text, fill=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_BUTTONS, "bold"))

        self.bind("<Enter>", lambda _: self._animate_hover(True))
        self.bind("<Leave>", lambda _: self._animate_hover(False))
        self.bind("<ButtonPress-1>", self._on_press)

    def _render_shape(self, offset: float, fill: str) -> int:
        r = 6
        x1, y1, x2, y2 = offset, offset, self.w - offset, self.h - offset   
        pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(pts, fill=fill, smooth=True)

    def _animate_hover(self, entering: bool) -> None:
        target_col = config.COLOR_HOVER if entering else self.base_bg
        self.delete(self.poly_id)
        pad = 1.5 if entering else 0
        self.poly_id = self._render_shape(pad, fill=target_col)
        self.tag_raise(self.text_id)

    def _on_press(self, _: Any) -> None:
        self.move(self.text_id, 1, 1)
        self.after(70, self._on_release)

    def _on_release(self) -> None:
        if self.winfo_exists():
            self.move(self.text_id, -1, -1)
            self.command()

# ---------------- FIXED COHESIVE CARD MODULE INTERFACES ---------------- #

class ModernLeaderboardWidget(tk.Frame):
    """Luxury card list mapping distinct alignment metrics to guarantee pixel alignment."""
    def __init__(self, parent: Any, max_width: int = 220, **kwargs: Any) -> None:
        super().__init__(parent, bg=config.COLOR_PANEL, **kwargs)
        self.max_width = max_width
        self.slots: List[tk.Canvas] = []
        self.last_data = ""
        self.last_player = ""
        self.bind("<Configure>", self._on_configure_resize)

    def _on_configure_resize(self, event: tk.ConfigureEvent) -> None:
        """Tracks column width changes to resize horizontal bounding layers dynamically."""
        self.max_width = max(10, event.width)
        for slot in self.slots:
            slot.configure(width=self.max_width)
        if self.last_data:
            self._redraw_rankings()

    def populate_rankings(self, data_str: str, current_player: str) -> None:
        self.last_data = data_str
        self.last_player = current_player
        self._redraw_rankings()

    def _redraw_rankings(self) -> None:
        if not self.last_data: return
        lines = [ln for ln in self.last_data.split(";") if ln.strip()]

        while len(self.slots) < len(lines):
            card_canvas = tk.Canvas(self, width=self.max_width, height=38, bg=config.COLOR_PANEL, highlightthickness=0, bd=0)
            card_canvas.pack(fill="x", pady=4)
            self.slots.append(card_canvas)

        while len(self.slots) > len(lines):
            old_slot = self.slots.pop()
            old_slot.destroy()

        for idx, text_line in enumerate(lines):
            bits = text_line.split(",")
            if len(bits) >= 3:
                rank_num, p_name, p_score = bits[0], bits[1], bits[-1]
                canvas = self.slots[idx]
                
                bg_col = config.COLOR_CARD if p_name == self.last_player else config.COLOR_PANEL
                canvas.configure(bg=bg_col)
                canvas.delete("all")

                # Medal Badges Circle Allocation
                c_map = {"1": config.COLOR_GOLD, "2": config.COLOR_SILVER, "3": config.COLOR_BRONZE}
                badge_fill = c_map.get(rank_num, config.COLOR_BORDER)
                canvas.create_oval(8, 8, 26, 26, fill=badge_fill, width=0)
                
                badge_txt = rank_num
                if rank_num == "1": badge_txt = "🥇"
                elif rank_num == "2": badge_txt = "🥈"
                elif rank_num == "3": badge_txt = "🥉"
                canvas.create_text(17, 17, text=badge_txt, fill=config.COLOR_BG, font=(config.FONT_FAMILY, 8, "bold"))

                # Player Text
                text_col = config.COLOR_PRIMARY if p_name == self.last_player else config.COLOR_TEXT
                canvas.create_text(42, 17, text=p_name, fill=text_col, font=(config.FONT_FAMILY, 10, "bold"), anchor="w")

                # Points Text pinned cleanly inside dynamic right edges
                canvas.create_text(self.max_width - 12, 17, text=f"{p_score} pts", fill=text_col, font=(config.FONT_MONO, 9, "bold"), anchor="e")

class LobbyWidget(tk.Frame):
    def __init__(self, parent: Any) -> None:
        super().__init__(parent, bg=config.COLOR_CARD, padx=30, pady=30, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        self.lbl_title = tk.Label(self, text="Waiting for Players...", bg=config.COLOR_CARD, fg=config.COLOR_PRIMARY, font=(config.FONT_FAMILY, config.FONT_TITLE, "bold"))
        self.lbl_title.pack(pady=(0, 10))
        
        self.lbl_count = tk.Label(self, text="0 / 0 Ready", bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_HEADING))
        self.lbl_count.pack(pady=5)

        self.list_frame = tk.Frame(self, bg=config.COLOR_PANEL, padx=15, pady=15, highlightthickness=1, highlightbackground=config.COLOR_BORDER, width=280, height=180)
        self.list_frame.pack_propagate(False)
        self.list_frame.pack(pady=15)

    def sync_lobby(self, status: str, ready_count: str, raw_players: str) -> None:
        self.lbl_title.configure(text=status)
        self.lbl_count.configure(text=f"Lobby: {ready_count}")
        for child in self.list_frame.winfo_children(): child.destroy()
        for name in raw_players.split(","):
            if name.strip():
                r = tk.Frame(self.list_frame, bg=config.COLOR_PANEL)
                r.pack(fill="x", pady=3)
                tk.Label(r, text=f"👤  {name.strip()}", bg=config.COLOR_PANEL, fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_BODY)).pack(side="left")
                tk.Label(r, text="READY", bg=config.COLOR_PANEL, fg=config.COLOR_SUCCESS, font=(config.FONT_FAMILY, config.FONT_LEADERBOARD, "bold")).pack(side="right")

# ---------------- APPLICATION SYSTEM MANAGER ---------------- #

class HangboyClientApplication:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(config.WINDOW_TITLE)
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=config.COLOR_BG)
        self.gameover_screen_loaded = False
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.username = ""
        self.local_cached_lives = config.STARTING_LIVES
        self.current_bar_ratio = 1.0
        
        self.current_view_state = "LOGIN" 
        self.base_container = tk.Frame(self.root, bg=config.COLOR_BG)
        self.base_container.pack(fill="both", expand=True)

        self.show_login_workspace()

    def set_view_layout_state(self, target_state: str) -> bool:
        if self.current_view_state == target_state: return False
        self.current_view_state = target_state
        if hasattr(self, "ambient_fx") and self.ambient_fx: self.ambient_fx.active = False
        for child in self.base_container.winfo_children(): child.destroy()
        return True

    def show_login_workspace(self) -> None:
        self.current_view_state = "LOGIN"
        for child in self.base_container.winfo_children(): child.destroy()

        self.ambient_fx = ParticleBackground(self.base_container)
        self.ambient_fx.pack(fill="both", expand=True)

        card = tk.Frame(self.ambient_fx, bg=config.COLOR_CARD, padx=35, pady=35, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        card.place(relx=0.5, rely=0.48, anchor="center")

        logo = tk.Label(card, text="🎯 HANGBOY PRO", bg=config.COLOR_CARD, fg=config.COLOR_PRIMARY, font=(config.FONT_FAMILY, config.FONT_TITLE, "bold"))
        logo.pack(pady=(0, 2))
        tk.Label(card, text="Competitive Arena Launcher Engine", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY)).pack(pady=(0, 25))

        tk.Label(card, text="PLAYER NICKNAME", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold")).pack(anchor="w", pady=(0, 4))
        self.ent_user = tk.Entry(card, bg=config.COLOR_BG, fg=config.COLOR_TEXT, bd=0, insertbackground=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_BODY), width=30, highlightthickness=1, highlightbackground=config.COLOR_BORDER, highlightcolor=config.COLOR_PRIMARY)
        self.ent_user.pack(pady=(0, 15), ipady=6)
        self.ent_user.focus_set()
        self.ent_user.bind("<Return>", lambda _: self.trigger_handshake_sequence())

        tk.Label(card, text="SERVER NODE IP ADDRESS", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold")).pack(anchor="w", pady=(0, 4))
        self.ent_host = tk.Entry(card, bg=config.COLOR_BG, fg=config.COLOR_TEXT, bd=0, insertbackground=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_BODY), width=30, highlightthickness=1, highlightbackground=config.COLOR_BORDER, highlightcolor=config.COLOR_PRIMARY)
        self.ent_host.insert(0, config.SERVER_IP)
        self.ent_host.pack(pady=(0, 25), ipady=6)
        self.ent_host.bind("<Return>", lambda _: self.trigger_handshake_sequence())

        RoundedButton(card, "ENTER ARENA", self.trigger_handshake_sequence, width=270, height=38).pack()
        self.lbl_status = tk.Label(card, text="Status: Ready", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY, "italic"))
        self.lbl_status.pack(pady=(15, 0))
        self.gameover_screen_loaded = False

    def inflate_lobby_viewport(self) -> None:
        self.lobby_panel = LobbyWidget(self.base_container)
        self.lobby_panel.place(relx=0.5, rely=0.5, anchor="center")

    def assemble_game_grid(self) -> None:
        # ===== Root Layout =====
        self.base_container.grid_rowconfigure(0, weight=1)

        self.base_container.grid_columnconfigure(0, weight=20, minsize=220)
        self.base_container.grid_columnconfigure(1, weight=60, minsize=620)
        self.base_container.grid_columnconfigure(2, weight=20, minsize=260)
    

        # ---------------- LEFT PANEL (STATIONARY SIDEBAR) ---------------- #
        self.left_panel = tk.Frame(self.base_container, bg=config.COLOR_PANEL)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10,5), pady=10)
        
        box = tk.Frame(self.left_panel, bg=config.COLOR_CARD, padx=12, pady=12, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        box.pack(fill="x", padx=10, pady=(15, 10))

        self.lbl_local_name = tk.Label(box, text=self.username, bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold"), anchor="w")
        self.lbl_local_name.pack(fill="x")
        self.lbl_local_score = tk.Label(box, text="Current Score: 0 pts", bg=config.COLOR_CARD, fg=config.COLOR_PRIMARY, font=(config.FONT_FAMILY, config.FONT_BODY), anchor="w")
        self.lbl_local_score.pack(fill="x", pady=(2, 10))

        inner_lbls = tk.Frame(box, bg=config.COLOR_CARD)
        inner_lbls.pack(fill="x")
        tk.Label(inner_lbls, text="VITALITY MATRIX", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_LEADERBOARD, "bold")).pack(side="left")
        self.lbl_lives_text = tk.Label(inner_lbls, text="6/6", bg=config.COLOR_CARD, fg=config.COLOR_SUCCESS, font=(config.FONT_FAMILY, config.FONT_LEADERBOARD, "bold"))
        self.lbl_lives_text.pack(side="right")

        self.bar_canvas = tk.Canvas(box, height=5, bg=config.COLOR_BG, highlightthickness=0, bd=0)
        self.bar_canvas.pack(fill="x", pady=(5, 0))
        self.bar_rect_id = self.bar_canvas.create_rectangle(0, 0, 0, 5, fill=config.COLOR_SUCCESS, width=0)

        tk.Label(self.left_panel, text="LIVE STANDINGS", bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold"), anchor="w").pack(fill="x", padx=12, pady=(15, 2))
        self.scoreboard_view = ModernLeaderboardWidget(self.left_panel, max_width=215)
        self.scoreboard_view.pack(fill="x", padx=12)

        # ---------------- CENTER PANEL (MAIN GAMEPLAY CORE) ---------------- #
        self.center_panel = tk.Frame(self.base_container, bg=config.COLOR_BG)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        self.center_panel.columnconfigure(0, weight=1)
        self.center_panel.rowconfigure(2, weight=1)

        self.lbl_clue = tk.Label(self.center_panel, text="Hint: Clue loading...", bg=config.COLOR_BG, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY, "italic"), justify="center", wraplength=560)
        self.lbl_clue.grid(row=0, column=0, pady=(2, 2), sticky="ew")

        self.lbl_puzzle_string = tk.Label(self.center_panel, text="_ _ _ _ _", bg=config.COLOR_BG, fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, 24, "bold"), justify="center")
        self.lbl_puzzle_string.grid(row=1, column=0, pady=(2, 5), sticky="ew")

        self.focus_card = tk.Frame(self.center_panel, bg=config.COLOR_CARD, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        self.focus_card.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.focus_card.columnconfigure(0, weight=1)
        self.focus_card.rowconfigure(0, weight=1)

        self.hangman_canvas = tk.Canvas(self.focus_card, bg=config.COLOR_CARD, highlightthickness=0, bd=0, height=360)
        self.hangman_canvas.grid(row=0, column=0, sticky="nsew")
        
        ctrls = tk.Frame(self.center_panel, bg=config.COLOR_BG)
        ctrls.grid(row=3, column=0, pady=(6, 2))

        self.ent_char = tk.Entry(ctrls, bg=config.COLOR_CARD, fg=config.COLOR_TEXT, bd=0, insertbackground=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold"), width=4, justify="center", highlightthickness=1, highlightbackground=config.COLOR_BORDER, highlightcolor=config.COLOR_PRIMARY)
        self.ent_char.pack(side="left", padx=6, ipady=5)
        self.ent_char.bind("<Return>", lambda _: self.dispatch_guess_payload())

        self.btn_guess = RoundedButton(ctrls, "SUBMIT", self.dispatch_guess_payload, width=90, height=32)
        self.btn_guess.pack(side="left", padx=3)
        self.btn_skip = RoundedButton(ctrls, "NEXT LEVEL", self.dispatch_skip_payload, bg=config.COLOR_PANEL, width=110, height=32)
        self.btn_skip.pack(side="left", padx=3)

        # ---------------- RIGHT PANEL (ACTIVITY INFORMATION) ---------------- #
        self.right_panel = tk.Frame(self.base_container, bg=config.COLOR_PANEL)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(5,10), pady=(10))

        meta = tk.Frame(self.right_panel, bg=config.COLOR_CARD, padx=12, pady=10, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        meta.pack(fill="x", padx=10, pady=(15, 8))
        self.lbl_round_tag = tk.Label(meta, text="ROUND --", bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold"), anchor="w")
        self.lbl_round_tag.pack(fill="x")
        self.lbl_timer_tag = tk.Label(meta, text="Elapsed Duration: 00:00", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY), anchor="w")
        self.lbl_timer_tag.pack(fill="x", pady=(2, 0))

        tk.Label(self.right_panel, text="ARENA STREAM LOG", bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 2))
        log_shell = tk.Frame(self.right_panel, bg=config.COLOR_CARD, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        log_shell.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        self.txt_console = tk.Text(log_shell, bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_MONO, config.FONT_ACTIVITY), bd=0, highlightthickness=0, state="disabled", wrap="word")
        self.txt_console.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scroll = ttk.Scrollbar(log_shell, orient="vertical", command=self.txt_console.yview)
        scroll.pack(side="right", fill="y")
        self.txt_console.configure(yscrollcommand=scroll.set)

        # Force structural layout sequence prior to mapping canvas configure anchors
        self.root.update_idletasks()
        self.hangman_canvas.bind("<Configure>", lambda _: self._draw_hangman_scaffold(self.local_cached_lives))
        self._draw_hangman_scaffold(self.local_cached_lives)

    def inflate_round_defeat_workspace(self, correct_word: str, state: Dict[str, str]) -> None:
        card = tk.Frame(self.base_container, bg=config.COLOR_CARD, padx=40, pady=35, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", width=540, height=360)

        tk.Label(card, text="☠️", fg=config.COLOR_ERROR, bg=config.COLOR_CARD, font=(config.FONT_FAMILY, 38)).pack()
        tk.Label(card, text="YOU WERE ELIMINATED", fg=config.COLOR_ERROR, bg=config.COLOR_CARD, font=(config.FONT_FAMILY, config.FONT_TITLE, "bold")).pack(pady=4)
        
        tk.Label(card, text=f"The correct word was: {correct_word}", bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold")).pack(pady=8)
        tk.Label(card, text=f"Your Current Score: {state.get('MY_SCORE', '0')} pts", bg=config.COLOR_CARD, fg=config.COLOR_PRIMARY, font=(config.FONT_FAMILY, config.FONT_BODY, "bold")).pack()

        status_frame = tk.Frame(card, bg=config.COLOR_PANEL, padx=15, pady=10, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        status_frame.pack(fill="x", padx=20, pady=15)
        
        tk.Label(status_frame, text=f"Players Finished: {state.get('FINISHED_COUNT','0')} / {state.get('TOTAL_PLAYERS','0')}", bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY)).pack(anchor="w")
        tk.Label(status_frame, text=f"Players Remaining: {state.get('REMAINING_COUNT','0')}", bg=config.COLOR_PANEL, fg=config.COLOR_SUCCESS, font=(config.FONT_FAMILY, config.FONT_BODY, "bold")).pack(anchor="w", pady=(2,0))

        tk.Label(card, text="Tournament continues. Waiting for remaining players...", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY, "italic")).pack()

    def inflate_waiting_for_competitors_workspace(self, state: Dict[str, str]) -> None:
        card = tk.Frame(self.base_container, bg=config.COLOR_CARD, padx=40, pady=35, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", width=540, height=360)

        tk.Label(card, text="🏁", bg=config.COLOR_CARD, font=(config.FONT_FAMILY, 36)).pack()
        tk.Label(card, text="TOURNAMENT FINISHED RUN!", fg=config.COLOR_SUCCESS, bg=config.COLOR_CARD, font=(config.FONT_FAMILY, config.FONT_TITLE, "bold")).pack(pady=4)
        
        tk.Label(card, text="Waiting for remaining players...", bg=config.COLOR_CARD, fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold")).pack(pady=5)
        tk.Label(card, text=f"Your Current Position: #{state.get('MY_RANK','1')} Rank", bg=config.COLOR_CARD, fg=config.COLOR_PRIMARY, font=(config.FONT_FAMILY, config.FONT_BODY, "bold")).pack()

        status_frame = tk.Frame(card, bg=config.COLOR_PANEL, padx=15, pady=10, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        status_frame.pack(fill="x", padx=20, pady=15)
        
        tk.Label(status_frame, text=f"Players Finished: {state.get('FINISHED_COUNT','0')} / {state.get('TOTAL_PLAYERS','0')}", bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY)).pack(anchor="w")
        tk.Label(status_frame, text=f"Players Remaining: {state.get('REMAINING_COUNT','0')}", bg=config.COLOR_PANEL, fg=config.COLOR_SUCCESS, font=(config.FONT_FAMILY, config.FONT_BODY, "bold")).pack(anchor="w", pady=(2,0))

        tk.Label(card, text="Final scoreboard calculations will unlock automatically.", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY, "italic")).pack()

    # ---------------- FULL VIEW TERMINAL RESULTS SCENES (IMAGE_FEC953) ---------------- #

    def present_champion_scene(self, winner_name: str, final_score: str, scoreboard_raw: str, state: Dict[str, str]) -> None:
        self.root.geometry("1100x700")
        self.root.minsize(1000, 650)
        for widget in self.base_container.winfo_children():
            widget.destroy()
        terminal_root = tk.Frame(self.base_container, bg=config.COLOR_BG)
        terminal_root.pack(fill="both", expand=True)
        # ---------------- GRID ----------------
        terminal_root.grid_columnconfigure(0, weight=7)
        terminal_root.grid_columnconfigure(1, weight=3)
        terminal_root.grid_rowconfigure(0, weight=1)
        # ---------------- CONFETTI BACKGROUND ----------------
        confetti_canvas = tk.Canvas(
            terminal_root,
            bg=config.COLOR_BG,
            highlightthickness=0,
            bd=0
        )
        confetti_canvas.place(
            relx=0,
            rely=0,
            relwidth=1,
            relheight=1
        )
        confetti = []
        for _ in range(220):
            confetti.append({
                "x": random.randint(0, config.WINDOW_WIDTH),
                "y": random.randint(-700, 0),
                "vy": random.uniform(3, 8),
                "size": random.randint(3, 7),
                "col": random.choice([config.COLOR_PRIMARY, config.COLOR_GOLD, config.COLOR_SUCCESS,
                                       "#00FFFF", "#FF69B4", "#FFD700", "#00FF7F", "#BA55D3"]) })

        self._deploy_confetti_stream(confetti_canvas, confetti)
        # =======================================================
        # LEFT PANEL
        # =======================================================
        left = tk.Frame(terminal_root, bg=config.COLOR_BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(25,15), pady=20)
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_anchor("center")

        card = tk.Frame(left, bg=config.COLOR_CARD, highlightthickness=1, highlightbackground=config.COLOR_BORDER, padx=40, pady=30)
        card.grid(row=0, column=0)

        tk.Label(
            card,
            text="🏆 TOURNAMENT COMPLETE",
            bg=config.COLOR_CARD,
            fg=config.COLOR_GOLD,
            font=(config.FONT_FAMILY,18,"bold")
        ).pack()

        tk.Label(
            card,
            text="CHAMPION!",
            bg=config.COLOR_CARD,
            fg=config.COLOR_TEXT,
            font=(config.FONT_FAMILY,34,"bold")
        ).pack(pady=(8,18))

        trophy = tk.Canvas(
            card,
            width=240,
            height=180,
            bg=config.COLOR_CARD,
            highlightthickness=0
        )

        trophy.pack()

        self._render_premium_trophy(trophy)

        tk.Label(
            card,
            text=winner_name.upper(),
            bg=config.COLOR_CARD,
            fg=config.COLOR_GOLD,
            font=(config.FONT_FAMILY,22,"bold")
        ).pack(pady=(20,0))

        tk.Label(
            card,
            text="Tournament Champion 🏆",
            bg=config.COLOR_CARD,
            fg=config.COLOR_TEXT,
            font=(config.FONT_FAMILY,16)
        ).pack()

        score_box = tk.Frame(
            card,
            bg=config.COLOR_PANEL,
            padx=25,
            pady=12,
            highlightthickness=1,
            highlightbackground=config.COLOR_BORDER
        )

        score_box.pack(pady=20)

        tk.Label(
            score_box,
            text=f"⭐ {final_score} pts",
            bg=config.COLOR_PANEL,
            fg=config.COLOR_GOLD,
            font=(config.FONT_FAMILY,20,"bold")
        ).pack()

        btns = tk.Frame(card,bg=config.COLOR_CARD)

        btns.pack(pady=20)

        RoundedButton(
            btns,
            "PLAY AGAIN",
            self.dispatch_skip_payload,
            width=120,
            height=36
        ).pack(side="left",padx=8)

        RoundedButton(
            btns,
            "EXIT",
            self.disconnect_and_terminate,
            bg=config.COLOR_PANEL,
            width=120,
            height=36
        ).pack(side="left",padx=8)

        # =======================================================
        # RIGHT PANEL
        # =======================================================

        right = tk.Frame(
            terminal_root,
            bg=config.COLOR_PANEL
        )

        right.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(10,20),
            pady=20
        )

        right.grid_rowconfigure(0,weight=1)
        right.grid_rowconfigure(1,weight=1)
        right.grid_columnconfigure(0,weight=1)

        lb = tk.Frame(
            right,
            bg=config.COLOR_PANEL,
            padx=18,
            pady=18,
            highlightthickness=1,
            highlightbackground=config.COLOR_BORDER
        )

        lb.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(12,6)
        )

        tk.Label(
            lb,
            text="🏆 FINAL TOURNAMENT STANDINGS",
            bg=config.COLOR_PANEL,
            fg=config.COLOR_MUTED,
            font=(config.FONT_FAMILY,config.FONT_HEADING,"bold")
        ).pack(anchor="w")

        leaderboard = ModernLeaderboardWidget(
            lb,
            max_width=420
        )

        leaderboard.pack(fill="x",pady=10)

        leaderboard.populate_rankings(
            scoreboard_raw,
            self.username
        )

        stats = tk.Frame(
            right,
            bg=config.COLOR_PANEL,
            padx=18,
            pady=18,
            highlightthickness=1,
            highlightbackground=config.COLOR_BORDER
        )

        stats.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(6,12)
        )

        tk.Label(
            stats,
            text="📊 YOUR PERFORMANCE",
            bg=config.COLOR_PANEL,
            fg=config.COLOR_MUTED,
            font=(config.FONT_FAMILY,config.FONT_HEADING,"bold")
        ).pack(anchor="w",pady=(0,10))

        def add_row(label,value,color=config.COLOR_TEXT):

            row=tk.Frame(stats,bg=config.COLOR_PANEL)

            row.pack(fill="x",pady=2)

            tk.Label(
                row,
                text=label,
                bg=config.COLOR_PANEL,
                fg=config.COLOR_MUTED
            ).pack(side="left")

            tk.Label(
                row,
                text=value,
                bg=config.COLOR_PANEL,
                fg=color,
                font=(config.FONT_FAMILY,11,"bold")
            ).pack(side="right")

        add_row("Final Rank",f"#{state.get('MY_RANK','1')}",config.COLOR_PRIMARY)
        add_row("Final Score",f"{state.get('MY_SCORE','0')} pts",config.COLOR_PRIMARY)
        add_row("Accuracy",state.get("ACCURACY","0%"),config.COLOR_SUCCESS)
        add_row("Correct Guesses",state.get("CORRECT_GUESSES","0"))
        add_row("Wrong Guesses",state.get("WRONG_GUESSES","0"),config.COLOR_ERROR)
        add_row("Levels Won",f"{state.get('ROUNDS_WON','0')} / 5",config.COLOR_SUCCESS)
        add_row("Levels Lost",f"{state.get('ROUNDS_LOST','0')} / 5",config.COLOR_ERROR)
    
    def present_game_over_scene(self, fields: Dict[str, str], scoreboard_raw: str) -> None:
        for widget in self.base_container.winfo_children():
            widget.destroy()

        self.root.geometry("1100x700")
        self.root.minsize(1000, 650)

        terminal_root = tk.Frame(
            self.base_container,
            bg=config.COLOR_BG
        )

        terminal_root.pack(fill="both", expand=True)

        terminal_root.grid_columnconfigure(0, weight=7)
        terminal_root.grid_columnconfigure(1, weight=3)
        terminal_root.grid_rowconfigure(0, weight=1)

        # ---------------- LEFT PANEL ----------------
        left_flow = tk.Frame(
            terminal_root,
            bg=config.COLOR_BG
        )

        left_flow.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(20,10),
            pady=20
        )

        left_flow.grid_rowconfigure(0, weight=1)
        left_flow.grid_columnconfigure(0, weight=1)
        left_flow.grid_anchor("center")


        # ---------------- RIGHT PANEL ----------------

        right_stack = tk.Frame(
            terminal_root,
            bg=config.COLOR_PANEL
        )

        right_stack.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(10,20),
            pady=20
        )

        right_stack.grid_rowconfigure(0, weight=1)
        right_stack.grid_rowconfigure(1, weight=1)
        right_stack.grid_columnconfigure(0, weight=1)

        card_center = tk.Frame(left_flow, bg=config.COLOR_CARD, padx=30, pady=25, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        card_center.grid(row=0, column=0, sticky="n")

        tk.Label(card_center, text="🏁 TOURNAMENT COMPLETE", bg=config.COLOR_CARD, fg=config.COLOR_ERROR, font=(config.FONT_FAMILY, config.FONT_TITLE, "bold")).pack()
        
        champ_frame = tk.Frame(card_center, bg=config.COLOR_PANEL, padx=25, pady=15, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        champ_frame.pack(pady=15, fill="x")
        tk.Label(card_center, text=f"You finished #{fields.get('MY_RANK','4')}", bg=config.COLOR_CARD, fg=config.COLOR_PRIMARY, font=(config.FONT_FAMILY,20,"bold")).pack(pady=(10,5))
        tk.Label(champ_frame, text="👑  TOURNAMENT CHAMPION", bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY, "bold")).pack()
        tk.Label(champ_frame, text=fields.get("WINNER", "Unknown"), bg=config.COLOR_PANEL, fg=config.COLOR_GOLD, font=(config.FONT_FAMILY, 22, "bold")).pack(pady=2)
        tk.Label(champ_frame, text=f"Total Winning Score: {fields.get('CHAMPION_SCORE', '0')} pts", bg=champ_frame["bg"], fg=config.COLOR_TEXT, font=(config.FONT_FAMILY, config.FONT_BODY)).pack()

        tk.Label(card_center, text="You fought bravely!\nBetter luck in the next tournament.", bg=config.COLOR_CARD, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_HEADING, "italic"), justify="center").pack(pady=10)

        btn_shell = tk.Frame(card_center, bg=config.COLOR_CARD)
        btn_shell.pack(pady=(15, 0))
        RoundedButton(btn_shell, "PLAY AGAIN", self.dispatch_skip_payload, bg=config.COLOR_PRIMARY, width=120, height=36).pack(side="left", padx=8)
        RoundedButton(btn_shell, "EXIT", self.disconnect_and_terminate, bg=config.COLOR_PANEL, width=120, height=36).pack(side="left", padx=8)


        lb_frame = tk.Frame(right_stack, bg=config.COLOR_PANEL, padx=20, pady=20, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        lb_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 8))
        lb_frame.columnconfigure(0, weight=1)
        
        tk.Label(lb_frame, text="🏆 FINAL TOURNAMENT STANDINGS", bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold")).pack(anchor="w", pady=(0, 8))
        end_board = ModernLeaderboardWidget(lb_frame, max_width=420)
        end_board.pack(fill="x")
        end_board.populate_rankings(scoreboard_raw, self.username)

        stats_frame = tk.Frame(right_stack, bg=config.COLOR_PANEL, padx=20, pady=20, highlightthickness=1, highlightbackground=config.COLOR_BORDER)
        stats_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(8, 15))
        
        tk.Label(stats_frame, text="📊 YOUR PERFORMANCE", bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_HEADING, "bold")).pack(anchor="w", pady=(0, 6))

        def _add_stat_loser(lbl: str, val: str, col: str = config.COLOR_TEXT) -> None:
            r = tk.Frame(stats_frame, bg=config.COLOR_PANEL)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=lbl, bg=config.COLOR_PANEL, fg=config.COLOR_MUTED, font=(config.FONT_FAMILY, config.FONT_BODY)).pack(side="left")
            tk.Label(r, text=val, bg=config.COLOR_PANEL, fg=col, font=(config.FONT_FAMILY, config.FONT_BODY, "bold")).pack(side="right")

        _add_stat_loser("Final Rank:", f"#{fields.get('MY_RANK','4')}", config.COLOR_PRIMARY)
        _add_stat_loser("Final Score:", f"{fields.get('MY_SCORE','0')} pts", config.COLOR_PRIMARY)
        _add_stat_loser("Accuracy:", fields.get("ACCURACY","0%"), config.COLOR_SUCCESS)
        _add_stat_loser("Correct Guesses:", fields.get("CORRECT_GUESSES","0"))
        _add_stat_loser("Wrong Guesses:", fields.get("WRONG_GUESSES","0"), config.COLOR_ERROR)
        _add_stat_loser("Levels Won:", f"{fields.get('ROUNDS_WON','0')} / 5", config.COLOR_SUCCESS)
        _add_stat_loser("Levels Lost:", f"{fields.get('ROUNDS_LOST','0')} / 5", config.COLOR_ERROR)

    def _render_premium_trophy(self, canvas: tk.Canvas) -> None:
        g, b = config.COLOR_GOLD, config.COLOR_BORDER
        canvas.create_rectangle(60, 135, 160, 155, fill="#3A3A3A", outline=b, width=2)
        canvas.create_polygon(75, 110, 145, 110, 155, 135, 65, 135, fill=config.COLOR_PANEL, outline=b, width=2)
        canvas.create_rectangle(102, 80, 118, 110, fill=g, outline=b, width=2)
        canvas.create_oval(60, 20, 160, 85, fill=g, outline=b, width=2)
        canvas.create_rectangle(60, 20, 160, 50, fill=g, outline=g)
        canvas.create_line(60, 50, 160, 50, fill=b, width=2)
        canvas.create_oval(40, 32, 62, 62, fill=config.COLOR_CARD, outline=g, width=4)
        canvas.create_oval(158, 32, 180, 62, fill=config.COLOR_CARD, outline=g, width=4)
        canvas.create_text(110, 38, text="★", fill="#181818", font=(config.FONT_FAMILY, 14, "bold"))

    def _deploy_confetti_stream(self, canvas: tk.Canvas, stream: List[Dict[str, Any]]) -> None:
        """Animated falling confetti."""
        if not canvas.winfo_exists() or self.current_view_state != "TERMINAL":
            return
        canvas.delete("confetti")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            w = config.WINDOW_WIDTH
        if h <= 1:
            h = config.WINDOW_HEIGHT
        for dot in stream:
            dot["y"] += dot["vy"]
            # Reset confetti when it reaches the bottom
            if dot["y"] > h:
                dot["y"] = -10
                dot["x"] = random.randint(10, w - 10)
            size = dot.get("size", 6)
            canvas.create_oval(
                dot["x"] - size,
                dot["y"] - size,
                dot["x"] + size,
                dot["y"] + size,
                fill=dot["col"],
                outline="",
                tags="confetti"
            )
        # Continue animation
        self.root.after(
            20,
            lambda: self._deploy_confetti_stream(canvas, stream)
        )
    # ---------------- REFERENCE COORDINATE DRAWING MODULE ---------------- #
    def _draw_hangman_scaffold(self, target_lives: int) -> None:
        print("DRAW HANGMAN:", target_lives) 
        self.hangman_canvas.delete("all")
        w = self.hangman_canvas.winfo_width()
        h = self.hangman_canvas.winfo_height()
        print(
            self.hangman_canvas.winfo_width(),
            self.hangman_canvas.winfo_height()
        )
        if w < 20 or h < 20: return

        mid_x, floor_y, roof_y = w * 0.44, h * 0.88, h * 0.12
        hook_x, left_base = mid_x + (w * 0.16), mid_x - (w * 0.22)

        stroke_col, stroke_w = config.COLOR_BORDER, 5
        self.hangman_canvas.create_line(left_base, floor_y, mid_x + (w * 0.28), floor_y, fill=stroke_col, width=stroke_w, capstyle="round")
        self.hangman_canvas.create_line(mid_x, floor_y, mid_x, roof_y, fill=stroke_col, width=stroke_w, capstyle="round")
        self.hangman_canvas.create_line(mid_x, roof_y, hook_x, roof_y, fill=stroke_col, width=stroke_w, capstyle="round")
        self.hangman_canvas.create_line(hook_x, roof_y, hook_x, roof_y + 35, fill=stroke_col, width=2.5, capstyle="round")

        faults = config.STARTING_LIVES - target_lives
        if faults <= 0: return

        color_p, p_width = config.COLOR_PRIMARY, 5
        rad = 24
        head_cy = roof_y + 35 + rad
        body_span = 95

        if faults >= 1: 
            self.hangman_canvas.create_oval(hook_x - rad, head_cy - rad, hook_x + rad, head_cy + rad, outline=color_p, width=p_width)
        if faults >= 2: 
            self.hangman_canvas.create_line(hook_x, head_cy + rad, hook_x, head_cy + rad + body_span, fill=color_p, width=p_width, capstyle="round")
        if faults >= 3: 
            self.hangman_canvas.create_line(hook_x, head_cy + rad + 20, hook_x - 35, head_cy + rad + 50, fill=color_p, width=p_width, capstyle="round")
        if faults >= 4: 
            self.hangman_canvas.create_line(hook_x, head_cy + rad + 20, hook_x + 35, head_cy + rad + 50, fill=color_p, width=p_width, capstyle="round")
        if faults >= 5: 
            self.hangman_canvas.create_line(hook_x, head_cy + rad + body_span, hook_x - 30, head_cy + rad + body_span + 60, fill=color_p, width=p_width, capstyle="round")
        if faults >= 6: self.hangman_canvas.create_line(hook_x, head_cy + rad + body_span, hook_x + 30, head_cy + rad + body_span + 60, fill=color_p, width=p_width, capstyle="round")

    def animate_progress_bar(self, ratio_target: float) -> None:
        if not hasattr(self, "bar_canvas") or not self.bar_canvas.winfo_exists(): return
        diff = ratio_target - self.current_bar_ratio
        if abs(diff) < 0.01: self.current_bar_ratio = ratio_target
        else: self.current_bar_ratio += diff * 0.16

        total_w = self.bar_canvas.winfo_width()
        calculated_w = max(0, int(total_w * self.current_bar_ratio))
        self.bar_canvas.coords(self.bar_rect_id, 0, 0, calculated_w, 5)
        self.bar_canvas.itemconfig(self.bar_rect_id, fill=config.COLOR_SUCCESS if self.current_bar_ratio > 0.35 else config.COLOR_ERROR)
        if self.current_bar_ratio != ratio_target: self.root.after(20, lambda: self.animate_progress_bar(ratio_target))

    def trigger_shake_ui(self, iteration: int = 0, magnitude: int = 6) -> None:
        if not hasattr(self, "focus_card") or not self.center_panel.winfo_exists(): return
        if iteration >= 6:
            self.center_panel.grid_configure(padx=12)
            return
        offset = magnitude if iteration % 2 == 0 else -magnitude
        self.center_panel.grid_configure(padx=12 + offset)
        self.root.after(40, lambda: self.trigger_shake_ui(iteration + 1, magnitude))

    def append_to_stream_log(self, text: str) -> None:
        if not hasattr(self, "txt_console") or not self.txt_console.winfo_exists(): return
        self.txt_console.configure(state="normal")
        if float(self.txt_console.index("end-1c").split(".")[0]) > 150: self.txt_console.delete("1.0", "2.0")
        self.txt_console.insert("end", f"• {text}\n")
        self.txt_console.configure(state="disabled")
        self.txt_console.see("end")

    # ---------------- NETWORK INTERFACE DISPATCHERS ---------------- #

    def trigger_handshake_sequence(self) -> None:
        user, host = self.ent_user.get().strip(), self.ent_host.get().strip() or config.SERVER_IP
        if not user:
            messagebox.showwarning("Validation Fault", "Arena nickname cannot be left empty.")
            return
        self.lbl_status.configure(text="Binding stream pipes...", fg=config.COLOR_PRIMARY)
        self.root.update_idletasks()

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3.0)
            self.sock.connect((host, config.SERVER_PORT))
            self.sock.settimeout(None)

            if send_msg(self.sock, f"JOIN:{user}"):
                self.username = user
                self.connected = True
                threading.Thread(target=self._background_receive_worker, daemon=True).start()
            else: raise OSError("Pipeline handshaking error drop.")
        except Exception as err:
            self.lbl_status.configure(text="Handshake failed.", fg=config.COLOR_ERROR)
            messagebox.showerror("Network Fault", f"Could not bind link arrays to server node.\nTrace: {err}")

    def _background_receive_worker(self) -> None:
        while self.connected:
            try:
                packet = recv_msg(self.sock)
                if packet is None: break
                fields: Dict[str, str] = {}
                for bit in packet.split("|"):
                    if ":" in bit:
                        k, v = bit.split(":", 1)
                        fields[k.strip().upper()] = v.strip()
                self.root.after(0, self._process_inbound_ui_state, fields)
            except OSError: break
        self.root.after(0, self._handle_link_severed)

    def _process_inbound_ui_state(self, state: Dict[str, str]) -> None:
        if not self.connected or not state: return

        if "ERROR" in state:
            self.connected = False
            if self.sock: self.sock.close()
            self.show_login_workspace()
            messagebox.showerror("Access Revoked", state.get("MSG", "Operational fault."))
            return

        phase = state.get("PHASE", "LOBBY")
        
        if phase == "LOBBY":
            if self.set_view_layout_state("LOBBY"): 
                self.inflate_lobby_viewport()
            self.lobby_panel.sync_lobby(state.get("STATUS",""), state.get("READY_COUNT",""), state.get("PLAYERS",""))
            return
        
        champion_name = state.get("WINNER", "Unknown")
        scoreboard_raw = state.get("RANKINGS", "")

        if state.get("GAMEOVER") == "YES":
            if self.gameover_screen_loaded:
                return

            self.gameover_screen_loaded = True

            champion_name = state.get("WINNER", "Unknown")
            scoreboard_raw = state.get("RANKINGS", "")

            if champion_name.upper() == self.username.upper():
                self.present_champion_scene(
                    champion_name,
                    state.get("MY_SCORE", "0"),
                    scoreboard_raw,
                    state
                )
            else:
                self.present_game_over_scene(
                    state,
                    scoreboard_raw
                )

            return
        sub_phase = state.get("SUBPHASE", "PLAYING")

        if sub_phase == "WAITING_DEFEATED":
            if self.set_view_layout_state("DEFEAT"):
                self.inflate_round_defeat_workspace(state.get("SECRET", ""), state)
            return

        
        if sub_phase == "WAITING_COMPLETED":
            if self.set_view_layout_state("WAITING"): 
                self.inflate_waiting_for_competitors_workspace(state)
            return

        # ---------- GAMEPLAY ----------
        self.gameover_screen_loaded = False
        if self.set_view_layout_state("GAME"):
            self.assemble_game_grid()

        lives = int(state.get("LIVES", config.STARTING_LIVES))

        if lives != self.local_cached_lives:
            self.local_cached_lives = lives

            self.lbl_lives_text.configure(
                text=f"{lives}/{config.STARTING_LIVES}",
                fg=config.COLOR_SUCCESS if lives > 2 else config.COLOR_ERROR
            )

            self.animate_progress_bar(lives / config.STARTING_LIVES)

            self.root.after(
                10,
                lambda l=lives: self._draw_hangman_scaffold(l)
            )

        self.lbl_round_tag.configure(
            text=f"ROUND {state.get('ROUND', '1')}"
        )

        self.lbl_timer_tag.configure(
            text=f"Elapsed Duration: {state.get('TIMER', '00:00')}"
        )

        self.scoreboard_view.populate_rankings(
            state.get("LIVE_LEADERBOARD", ""),
            self.username
        )

        self.lbl_clue.configure(
            text=f"Hint: {state.get('HINT', '')}"
        )

        self.lbl_puzzle_string.configure(
            text=state.get("WORD", "").upper()
        )

        self.hangman_canvas.update_idletasks()

        msg = state.get("MSG", "")

        if msg and "alive" not in msg.lower():
            self.append_to_stream_log(msg)

        # Keep keyboard focus on the guess entry
        self.ent_char.focus_set()

    def dispatch_guess_payload(self) -> None:
        if not hasattr(self, "ent_char") or not self.ent_char.winfo_exists(): return
        char = self.ent_char.get().strip().upper()
        self.ent_char.delete(0, "end")
        if len(char) != 1 or not char.isalpha(): return
        if self.sock and self.connected: send_msg(self.sock, f"GUESS:{char}")

    def dispatch_skip_payload(self) -> None:
        if self.sock and self.connected: send_msg(self.sock, f"REQUEST_NEXT")

    def _handle_link_severed(self) -> None:
        if not self.connected: return
        self.connected = False
        messagebox.showwarning("Link Severed", "Host link array dropped.")
        self.show_login_workspace()

    def disconnect_and_terminate(self) -> None:
        self.connected = False
        try:
            if self.sock: self.sock.close()
        except OSError: pass
        self.root.destroy()

if __name__ == "__main__":
    app_root = tk.Tk()
    engine = HangboyClientApplication(app_root)
    app_root.protocol("WM_DELETE_WINDOW", engine.disconnect_and_terminate)
    app_root.mainloop()