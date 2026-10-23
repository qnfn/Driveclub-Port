# SPDX-License-Identifier: GPL-2.0-or-later
"""SETUP page: game folder, frame rate, window, FPS counter, anti-aliasing, prepare again."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from dcport import fsr411, patches
from dcport.game import game_info, ready_checks
from dcport.prepare_state import is_prepared
from dcport.runtime import (FPS_PRESETS, LANGUAGES, fps_note, game_language, languages_for,
                            parse_fps, player_name)
from dcport.ui import theme

FPS_ERROR = "Enter a whole number from 30 to 240"
FSR4_MISSING = "FSR 4 needs the fsr4_shaders folder next to DriveClub.exe"
HINT = "Changes save at once. Game not starting after an update? Prepare its files again."
UPSCALERS = (("off", "Off"), ("fsr3", "FSR 3.1"), ("fsr4", "FSR 4"), ("fsr411", "FSR 4.1.1"),
             ("dlss", "DLSS"))
# NVIDIA DLSS: the bridge and NVIDIA's runtime next to the game (bin/), GeForce RTX only.
DLSS_FILES = ("dcport_dlss.dll", "nvngx_dlss.dll")
DLSS_NOTE = ("NVIDIA DLSS: DRIVECLUB's anti-aliasing at 1080p (DLAA) on GeForce RTX cards. "
             "If DLSS cannot start, the game uses FSR 3.1.")
DLSS_MISSING = "DLSS needs an NVIDIA GeForce RTX card and its files in the bin folder"
FSR411_HINT = ("FSR 4.1.1 is built once from your own amd_fidelityfx_upscaler_dx12.dll "
               "(Set up…). DCport does not include it.")
GLYPHS = {"ok": "✓", "warn": "⚠", "bad": "✕"}
DEFAULT_SHARPNESS = 0.30  # the runtime's value when dcport.ini has none
WINDOW_CHOICES = tuple((f"{w}x{h}", "4K" if h == 2160 else f"{h}p")
                       for w, h in patches.WINDOW_SIZES)
RENDER_CHOICES = tuple((r.key, r.label + (" (best)" if r.key == patches.DEFAULT_RESOLUTION
                                           else "")) for r in patches.RESOLUTIONS)
ASPECT_CHOICES = tuple((a, a) for a in patches.ASPECTS)
TIMING_CHOICES = (("deltatime", "Deltatime"), ("fixed", "Fixed tick"))
TIMING_NOTES = {
    "deltatime": "Smooth at any frame rate. Its authors note that it breaks a few things; "
                 "switch to the fixed tick if something misbehaves.",
    "fixed": "The engine's own 60 Hz tick: everything works, but it is not as smooth above "
             "60 FPS.",
}
THREADING_CHOICES = (("auto", "Auto"), ("1", "On"), ("0", "Off"))
THREADING_NOTE = ("Threading: the game's GPU work is prepared on extra threads. It gives more FPS "
                  "but can crash mid-race, so Auto keeps it off (as Off does); On turns it on. "
                  "Applies on the next PLAY.")
AA_NOTE = ("FSR and DLSS are DRIVECLUB's anti-aliasing at 1080p (native AA), not upscalers: "
           "the game's effects and HUD after it stay at 1080p, so there are no Quality, "
           "Balanced or Performance modes.")
BLUR_NOTE = ("FSR and DLSS do not run with the PATCHES page's 'No motion blur or "
             "depth of field': the game's anti-aliasing is in that shader.")


READBACKS_CHOICES = (("2", "On"), ("0", "Off"))
READBACKS_NOTE = ("GPU readbacks: the game gets the GPU's results back exactly when it needs "
                  "them. It keeps the roadside grass on the ground and stops stretched "
                  "geometry from the second event on. Costs some FPS. On by default. Applies "
                  "on the next PLAY.")


def readbacks_value(ini: dict) -> str:
    """dcport.ini readbacks: "2" (precise) is On, the default; "1" (0.4.4 relaxed) counts as On."""
    return "2" if ini.get("readbacks", "2").strip() in ("1", "2") else "0"


FRAME_GEN_CHOICES = (("off", "Off"), ("fsr3", "FSR 3.1"))
FRAME_GEN_NOTE = ("Frame generation (not fully tested yet, so try it): a generated frame between "
                  "two of the game's frames, so 60 FPS looks like 120. Needs an FSR mode above "
                  "and a display with twice the frame rate (Frame rate 60 on a 120 Hz screen). "
                  "Adds a little input lag. If a race crashes, turn it off. Also in the game's "
                  "menu.")


def frame_gen_value(ini: dict) -> str:
    """dcport.ini frame_gen: "fsr3" (or "dlss", which runs as FSR 3.1 here) is On."""
    return "fsr3" if ini.get("frame_gen", "off").strip() in ("fsr3", "dlss") else "off"


def threading_value(ini: dict) -> str:
    """dcport.ini threaded_recording: "1", "0", or anything else (or missing) for Auto."""
    value = ini.get("threaded_recording", "auto").strip()
    return value if value in ("0", "1") else "auto"


RENDER_NOTE = ("The game renders at 1080p; on a bigger window or screen the picture is scaled "
               "up to it with FSR 1 and sharpened (FSR edition).")
RENDER_HIGH_NOTE = ("Warning: {label} uses the community resolution patches, and they have "
                    "visual errors DCport cannot fix (for example broken clouds in the sky). "
                    "1080p is recommended: it looks best and is the most stable. {label} also "
                    "needs a strong GPU and more video memory. Applies on the next PLAY.")


WIDE_NOTE = ("Ultrawide {w}x{h}: the game renders its scene at the full width and the HUD "
             "stays in the middle 16:9 area. Field of view: {fov:.2f} (0.50 is the 16:9 view, "
             "{hor:.2f} keeps its height on this screen; higher shows more at the sides but "
             "stretches the edges). Applies on the next PLAY.")
NARROW_NOTE = ("{shape} {w}x{h}: the game shows the 16:9 view with more above and below. The "
               "menus and HUD stay 16:9 wide, so their left and right edges are cut off. "
               "Applies on the next PLAY.")
WIDE_HIGH_NOTE = " A higher Render is not available at this aspect ratio: it renders {lines} lines."


class SetupPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        app.paint(self, bg="bg")
        self._build_bottom()
        # the cards scroll when the window is too small for them (as on GARAGE)
        self.view = tk.Canvas(self, highlightthickness=0, bd=0, yscrollincrement=app.px(24))
        app.paint(self.view, bg="bg")
        self.view.pack(fill="both", expand=True)
        self.board = theme.CardBoard(self.view, app, columns=2)
        self._board_item = self.view.create_window(0, 0, anchor="nw", window=self.board)
        self.scroll = theme.ThinScrollbar(self, app, self.view.yview, bg_role="bg")
        self.view.configure(yscrollcommand=self._scrolled)
        self.view.bind("<Configure>", lambda e: self._fit_board())
        self.board.bind("<Configure>", lambda e: self._fit_board(), add="+")
        app.bind("<MouseWheel>", self._wheel, add="+")
        self._build_game(self.board.add(0, 0, title="Game folder"))
        self._build_fps(self.board.add(0, 1, title="Frame rate"))
        self._build_display(self.board.add(1, 0, title="Display"))
        self.upscaler_choice = None
        if app.fsr:
            self._build_upscaling(self.board.add(1, 1, title="Anti-aliasing"))
        self._error = ""
        self._phase = app.phase
        self._checks: list[tuple[tk.Label, str]] = []
        # runs now and after every theme switch, which repaints the state colours
        app.on_theme(lambda pal: self._repaint())

    # ------------------------------------------------------------ building

    def _fit_board(self) -> None:
        w = self.view.winfo_width()
        if w > 1:
            self.view.itemconfigure(self._board_item, width=w)
        self.view.configure(scrollregion=(0, 0, max(1, w), self.board.winfo_reqheight()))

    def _scrolled(self, first, last) -> None:
        self.scroll.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.scroll.place_forget()
        else:
            self.scroll.place(relx=1.0, x=-self.app.px(4), y=self.app.px(4), relheight=1.0,
                              height=-self.app.px(8), anchor="ne")
            tk.Misc.lift(self.scroll)  # Canvas.lift raises canvas items instead

    def _wheel(self, event):
        """The mouse wheel anywhere on this page scrolls it (when it doesn't fit)."""
        if self.app.current != "setup" or not str(event.widget).startswith(str(self)):
            return None
        first, last = self.view.yview()
        if first <= 0.0 and last >= 1.0:
            return None
        self.view.yview_scroll(-3 if event.delta > 0 else 3, "units")
        return None

    def _row(self, master) -> tk.Frame:
        row = tk.Frame(master)
        self.app.paint(row, bg="panel")
        return row

    def _settings_grid(self, card) -> tk.Frame:
        """Label | control rows, with the same label width in every card."""
        grid = self._row(card)
        grid.pack(fill="x")
        grid.columnconfigure(0, minsize=self.app.px(112))
        grid.columnconfigure(1, weight=1)
        return grid

    def _wrapping(self, label: tk.Label, master: tk.Misc) -> tk.Label:
        """Wrap the label's text at the card's width."""
        master.bind("<Configure>", lambda e: label.configure(wraplength=max(1, e.width)),
                    add="+")
        return label

    def _build_bottom(self) -> None:
        app = self.app
        bar = tk.Frame(self)
        app.paint(bar, bg="bg")
        bar.pack(side="bottom", fill="x", padx=app.px(24), pady=(app.px(16), app.px(20)))
        self.prepare_button = theme.PillButton(bar, app, "Prepare game files again",
                                               self.prepare_again, kind="secondary",
                                               font=app.fonts["button"], height=app.px(40),
                                               padx=app.px(22))
        self.prepare_button.pack(side="right")
        self.update_check_button = theme.PillButton(bar, app, "Check for updates",
                                                    self.check_updates, kind="secondary",
                                                    font=app.fonts["button"], height=app.px(40),
                                                    padx=app.px(22))
        self.update_check_button.pack(side="right", padx=(0, app.px(10)))
        self.status = theme.text_label(bar, app, HINT, fg="muted", bg="bg")
        self.status.pack(side="left", fill="x", expand=True)

    def _build_game(self, card) -> None:
        app = self.app
        row = self._row(card)
        row.pack(fill="x")
        change = theme.PillButton(row, app, "Change…", self._change_folder, kind="secondary",
                                  font=app.fonts["button"], height=app.px(32),
                                  padx=app.px(18), bg_role="panel")
        change.pack(side="right", padx=(app.px(10), 0))
        self.folder = theme.Field(row, app, width=app.px(160), editable=False)
        self.folder.pack(side="left", fill="x", expand=True)
        self.game_check = theme.text_label(card, app)
        self.game_check.pack(fill="x", pady=(app.px(12), 0))
        self.files_check = theme.text_label(card, app)
        self.files_check.pack(fill="x", pady=(app.px(4), 0))
        row = self._row(card)
        row.pack(fill="x", pady=(app.px(14), 0))
        theme.text_label(row, app, "Player name").pack(side="left")
        self.player_name = theme.Field(row, app, width=app.px(160))
        self.player_name.pack(side="left", padx=(app.px(12), app.px(8)))
        theme.text_label(row, app, "shown in the game, then Enter", font="small",
                         fg="muted").pack(side="left", padx=(app.px(6), 0))
        entry = self.player_name.entry
        for key in ("<Return>", "<KP_Enter>", "<FocusOut>"):
            entry.bind(key, lambda e: self.set_player_name(entry.get()), add="+")
        row = self._row(card)
        row.pack(fill="x", pady=(app.px(10), 0))
        theme.text_label(row, app, "Language").pack(side="left")
        self.language_box = theme.Dropdown(row, app, self._open_language_menu)
        self.language_box.configure(width=app.px(220))
        self.language_box.pack(side="left", padx=(app.px(12), app.px(8)))
        theme.text_label(row, app, "the game's text", font="small",
                         fg="muted").pack(side="left", padx=(app.px(6), 0))
        self._language_menu = None

    def _build_fps(self, card) -> None:
        app = self.app
        options = [(fps, str(fps)) for fps in FPS_PRESETS] + [("custom", "Custom")]
        self.fps_choice = theme.Segmented(card, app, options, self._pick_fps, min_label="000",
                                          pad=app.px(12))
        self.fps_choice.pack(anchor="w")
        row = self._row(card)
        row.pack(fill="x", pady=(app.px(14), 0))
        theme.text_label(row, app, "Custom").pack(side="left")
        self.custom = theme.Field(row, app, width=app.px(64), justify="center")
        self.custom.pack(side="left", padx=(app.px(12), app.px(8)))
        theme.text_label(row, app, "FPS").pack(side="left")
        theme.text_label(row, app, "30 to 240, then Enter", font="small", fg="muted").pack(
            side="left", padx=(app.px(14), 0))
        entry = self.custom.entry
        for key in ("<Return>", "<KP_Enter>"):
            entry.bind(key, lambda e: self.apply_custom_fps(entry.get()))
        entry.bind("<FocusOut>", self._custom_left, add="+")
        entry.bind("<Escape>", lambda e: self._custom_cancel())
        self.fps_error = theme.text_label(card, app, font="small_bold", fg="bad")
        self.fps_note = theme.text_label(card, app, font="small", fg="warn")
        self._wrapping(self.fps_note, card)
        # The frame-rate patch (above 30 FPS); the error and note above go in before it.
        self.timing_box = tk.Frame(card)
        app.paint(self.timing_box, bg="panel")
        self.timing_box.pack(fill="x", pady=(app.px(18), 0))
        row = self._row(self.timing_box)
        row.pack(fill="x")
        theme.text_label(row, app, "Patch").pack(side="left")
        self.timing_choice = theme.Segmented(row, app, TIMING_CHOICES, self.set_timing,
                                             min_label="Fixed tick")
        self.timing_choice.pack(side="left", padx=(app.px(12), 0))
        self.timing_note = theme.text_label(self.timing_box, app, font="small", fg="muted")
        self._wrapping(self.timing_note, self.timing_box).pack(fill="x", pady=(app.px(10), 0))

    def _build_display(self, card) -> None:
        app = self.app
        grid = self._settings_grid(card)
        theme.text_label(grid, app, "Window").grid(row=0, column=0, sticky="w")
        self.window_choice = theme.Segmented(
            grid, app, (("windowed", "Windowed"), ("fullscreen", "Fullscreen")),
            lambda v: self.set_fullscreen(v == "fullscreen"), min_label="Fullscreen")
        self.window_choice.grid(row=0, column=1, sticky="w")
        theme.text_label(grid, app, "Window size").grid(row=1, column=0, sticky="w",
                                                        pady=(app.px(10), 0))
        self.size_choice = theme.Segmented(grid, app, WINDOW_CHOICES, self.set_window_size,
                                           min_label="1080p")
        self.size_choice.grid(row=1, column=1, sticky="w", pady=(app.px(10), 0))
        theme.text_label(grid, app, "Render").grid(row=2, column=0, sticky="w",
                                                   pady=(app.px(10), 0))
        self.render_choice = theme.Segmented(grid, app, RENDER_CHOICES, self.set_render_res,
                                             min_label="1440p")
        self.render_choice.grid(row=2, column=1, sticky="w", pady=(app.px(10), 0))
        theme.text_label(grid, app, "Aspect ratio").grid(row=3, column=0, sticky="w",
                                                         pady=(app.px(10), 0))
        self.aspect_choice = theme.Segmented(grid, app, ASPECT_CHOICES, self.set_aspect,
                                             min_label="1440p")
        self.aspect_choice.grid(row=3, column=1, sticky="w", pady=(app.px(10), 0))
        theme.text_label(grid, app, "Field of view").grid(row=4, column=0, sticky="w",
                                                          pady=(app.px(10), 0))
        row = self._row(grid)
        row.grid(row=4, column=1, sticky="we", pady=(app.px(10), 0))
        self.fov_value = theme.text_label(row, app, "0.66", font="body_bold", width=4,
                                          anchor="e")
        self.fov_value.pack(side="right")
        self.fov = theme.Slider(row, app, length=app.px(140), from_=patches.FOV_MIN,
                                to=patches.FOV_MAX, on_change=self._fov_moved,
                                on_commit=self.set_fov)
        self.fov.pack(side="left", fill="x", expand=True, padx=(0, app.px(10)))
        theme.text_label(grid, app, "FPS counter").grid(row=5, column=0, sticky="w",
                                                        pady=(app.px(10), 0))
        self.counter_choice = theme.Segmented(grid, app, ((True, "On"), (False, "Off")),
                                              self.set_fps_counter, min_label="Fullscreen")
        self.counter_choice.grid(row=5, column=1, sticky="w", pady=(app.px(10), 0))
        theme.text_label(grid, app, "Threading").grid(row=6, column=0, sticky="w",
                                                      pady=(app.px(10), 0))
        self.threading_choice = theme.Segmented(grid, app, THREADING_CHOICES, self.set_threading,
                                                min_label="Fullscreen")
        self.threading_choice.grid(row=6, column=1, sticky="w", pady=(app.px(10), 0))
        theme.text_label(grid, app, "GPU readbacks").grid(row=7, column=0, sticky="w",
                                                          pady=(app.px(10), 0))
        self.readbacks_choice = theme.Segmented(grid, app, READBACKS_CHOICES, self.set_readbacks,
                                                min_label="Fullscreen")
        self.readbacks_choice.grid(row=7, column=1, sticky="w", pady=(app.px(10), 0))
        self.threading_note = theme.text_label(card, app, THREADING_NOTE, font="small",
                                               fg="muted")
        self._wrapping(self.threading_note, card).pack(fill="x", pady=(app.px(12), 0))
        self.readbacks_note = theme.text_label(card, app, READBACKS_NOTE, font="small",
                                               fg="muted")
        self._wrapping(self.readbacks_note, card).pack(fill="x", pady=(app.px(12), 0))
        self.render_note = theme.text_label(card, app, RENDER_NOTE, font="small", fg="muted")
        self._wrapping(self.render_note, card).pack(fill="x", pady=(app.px(12), 0))
        self.display_hint = theme.text_label(card, app, "More settings in game: press Insert, "
                                             "or L3 + R3 on a controller.", font="small",
                                             fg="muted")
        self._wrapping(self.display_hint, card).pack(fill="x", pady=(app.px(14), 0))

    def _build_upscaling(self, card) -> None:
        app = self.app
        grid = self._settings_grid(card)
        theme.text_label(grid, app, "Mode").grid(row=0, column=0, sticky="w")
        self.upscaler_choice = theme.Segmented(grid, app, UPSCALERS, self.set_upscaler,
                                               min_label="FSR 4.1.1", pad=app.px(10))
        self.upscaler_choice.grid(row=0, column=1, sticky="w")
        theme.text_label(grid, app, "Sharpness").grid(row=1, column=0, sticky="w",
                                                      pady=(app.px(10), 0))
        row = self._row(grid)
        row.grid(row=1, column=1, sticky="we", pady=(app.px(10), 0))
        self.sharpness_value = theme.text_label(row, app, "0.30", font="body_bold", width=4,
                                                anchor="e")
        self.sharpness_value.pack(side="right")
        self.sharpness = theme.Slider(row, app, length=app.px(140),
                                      on_change=self._sharpness_moved,
                                      on_commit=self.set_sharpness)
        self.sharpness.pack(side="left", fill="x", expand=True, padx=(0, app.px(10)))
        theme.text_label(grid, app, "Frame gen.").grid(row=2, column=0, sticky="w",
                                                       pady=(app.px(10), 0))
        self.frame_gen_choice = theme.Segmented(grid, app, FRAME_GEN_CHOICES, self.set_frame_gen,
                                                min_label="FSR 4.1.1", pad=app.px(10))
        self.frame_gen_choice.grid(row=2, column=1, sticky="w", pady=(app.px(10), 0))
        self.frame_gen_note = theme.text_label(card, app, FRAME_GEN_NOTE, font="small",
                                               fg="muted")
        self._wrapping(self.frame_gen_note, card).pack(fill="x", pady=(app.px(12), 0))
        self.upscaler_note = theme.text_label(card, app, font="small", fg="muted")
        self._wrapping(self.upscaler_note, card)
        row = self._row(card)
        row.pack(fill="x", pady=(app.px(14), 0))
        self.fsr411_button = theme.PillButton(row, app, "Set up FSR 4.1.1…", self.setup_fsr411,
                                              kind="secondary", font=app.fonts["button"],
                                              height=app.px(30), padx=app.px(16),
                                              bg_role="panel")
        self.fsr411_button.pack(side="left")
        self.fsr411_status = theme.text_label(card, app, FSR411_HINT, font="small", fg="muted")
        self._wrapping(self.fsr411_status, card).pack(fill="x", pady=(app.px(8), 0))
        self._fsr411_progress = ""
        self._fsr411_busy = False

    # ------------------------------------------------------------ showing

    def on_show(self) -> None:
        self._show_checks()
        self.refresh_session()

    def on_hide(self) -> None:
        if self._typing():  # leaving the page leaves the Custom field: apply what it holds
            self._custom_left(None)
            self.focus_set()

    def _repaint(self) -> None:
        self._paint_checks()
        self.refresh_session()

    def _typing(self) -> bool:
        """True while the Custom FPS field has the focus (its text may be half-typed)."""
        try:
            return self.focus_lastfor() is self.custom.entry
        except (KeyError, tk.TclError):
            return False

    def refresh_session(self) -> None:
        """Show the saved values (App's settings and dcport.ini); RACE's card shows the same.

        Runs after every settings save, so it only reads files that are cheap to read; the
        folder checks (is_prepared) wait for show(), a folder change or a process ending.
        """
        app, s = self.app, self.app.settings
        self.folder.set(s.game_dir or "No folder chosen")
        try:
            typing_name = self.focus_get() is self.player_name.entry
        except (KeyError, tk.TclError):
            typing_name = False
        if not typing_name:
            self.player_name.set(player_name(app.paths))
        self.language_box.set(dict(LANGUAGES)[game_language(app.paths)])
        if not self._typing():
            if s.fps in FPS_PRESETS:
                self.fps_choice.set(s.fps)
                self.custom.set("")
            else:
                self.fps_choice.set("custom")
                self.custom.set(str(s.fps))
            self._show_fps_error("")
        note = fps_note(s.fps) or ("The game's original timing (no frame-rate patches)."
                                   if s.fps == 30 else "")
        self.fps_note.configure(text=note, fg=app.palette["warn" if s.fps > 120 else "muted"])
        self._pack_if(self.fps_note, bool(note), pady=(app.px(10), 0), before=self.timing_box)
        timing = s.patch_timing if s.patch_timing in patches.TIMING else patches.DEFAULT_TIMING
        self.timing_choice.set(timing)
        at_30 = s.fps == 30
        for value, _ in TIMING_CHOICES:
            self.timing_choice.set_enabled(value, not at_30)
        self.timing_note.configure(
            text="Off at 30 FPS, the game's original timing." if at_30 else TIMING_NOTES[timing])
        self.window_choice.set("fullscreen" if s.fullscreen else "windowed")
        w, h = patches.window_size(s.window_size)
        self.size_choice.set(f"{w}x{h}")
        for value, _ in WINDOW_CHOICES:  # fullscreen covers the monitor
            self.size_choice.set_enabled(value, not s.fullscreen)
        render = patches.resolution(s.render_res)
        self.render_choice.set(render.key)
        high = render.key != patches.DEFAULT_RESOLUTION
        note = RENDER_HIGH_NOTE.format(label=render.label) if high else RENDER_NOTE
        self.aspect_choice.set(patches.aspect(s))
        display = patches.display(s)
        self.fov.set(patches.fov_factor(s))
        self.fov.set_enabled(display.wide)
        self._fov_moved(self.fov.value)
        if display.custom:
            w, h = display.size
            note = (WIDE_NOTE.format(w=w, h=h, fov=patches.fov(s), hor=patches.hor_plus(s))
                    if display.wide else NARROW_NOTE.format(shape=patches.aspect(s), w=w, h=h)) + \
                (WIDE_HIGH_NOTE.format(lines=display.lines) if render.size[1] > display.lines else "") + \
                ("\n\n" + note if high else "")
        hint = patches.screen_hint(app.screen, s)
        if hint and hint[1] == "warn":
            note = hint[0] + ".\n\n" + note
        self.render_note.configure(text=note, fg=app.palette["warn" if high or hint and
                                                             hint[1] == "warn" else "muted"])
        self.counter_choice.set(app.fps_counter_on())
        self.threading_choice.set(threading_value(app.game_ini()))
        self.readbacks_choice.set(readbacks_value(app.game_ini()))
        if self.upscaler_choice is not None:
            self._refresh_upscaling()
        self._show_status()
        self.set_phase(app.phase)

    def _show_checks(self) -> None:
        app = self.app
        folder = Path(app.settings.game_dir) if app.settings.game_dir else \
            app.paths.root / "(no game folder)"
        gd = app.game_dir()
        prepared = False
        if gd is not None:
            try:
                prepared = is_prepared(app.paths, gd)
            except (OSError, ValueError):
                prepared = False
        game, _, _, files = ready_checks(folder, app.paths, app.gpu, prepared)
        for label, check in ((self.game_check, game), (self.files_check, files)):
            label.configure(text=f"{GLYPHS.get(check.state, '')} {check.label}")
        self._checks = [(self.game_check, game.state), (self.files_check, files.state)]
        self._paint_checks()
        self._pack_if(self.files_check, gd is not None, pady=(app.px(4), 0))

    def _paint_checks(self) -> None:
        for label, state in self._checks:
            label.configure(fg=self.app.palette[state])

    def _pack_if(self, widget: tk.Misc, show: bool, **pack) -> None:
        if show:
            widget.pack(fill="x", **pack)
        else:
            widget.pack_forget()

    def _show_status(self, error: "str | None" = None) -> None:
        """The bottom line: the last save error, else the hint."""
        if error is not None:
            self._error = error
        role = "bad" if self._error else "muted"
        self.status.configure(text=self._error or HINT, fg=self.app.palette[role])

    def status_text(self) -> str:
        return self._error

    def set_phase(self, phase: str) -> None:
        ended = phase == "idle" and self._phase != "idle"
        self._phase = phase
        self.prepare_button.set("Prepare game files again", enabled=phase == "idle")
        if ended:
            self._show_checks()  # a prepare may have changed the game files

    # ------------------------------------------------------------ game folder

    def _change_folder(self) -> None:
        if self.app.ask_game_folder():
            self._show_checks()
            self.refresh_session()

    def prepare_enabled(self) -> bool:
        return self.prepare_button.enabled

    def prepare_again(self) -> bool:
        """Delete data/source.txt and run the prepare tool; never starts the game."""
        if self.app.phase != "idle":
            return False
        return self.app.prepare(start_game=False)

    # ------------------------------------------------------------ frame rate

    def _saved(self, ok: bool) -> None:
        self._show_status("" if ok else "Could not save the settings file (dcport-launcher.json)")

    def set_fps(self, fps: int) -> None:
        self.app.settings.fps = int(fps)
        self._saved(self.app.save_settings())  # also refreshes this page and RACE's card

    def _pick_fps(self, value) -> None:
        if value == "custom":
            self.focus_custom()
            return
        if self._typing():  # a preset replaces whatever was being typed
            self.custom.set("")
            self.focus_set()
        self.set_fps(value)

    def focus_custom(self) -> None:
        """Ready for typing a custom frame rate (also from RACE's Custom… menu item)."""
        self.fps_choice.set("custom")
        self.custom.entry.focus_set()
        self.custom.entry.select_range(0, "end")

    def apply_custom_fps(self, text: str) -> bool:
        fps = parse_fps(text)
        if fps is None:
            self._show_fps_error(FPS_ERROR)
            self.fps_choice.set("custom")
            return False
        self._show_fps_error("")
        self.set_fps(fps)
        return True

    def _custom_left(self, event) -> None:
        text = self.custom.get().strip()
        if not text:
            if not self.fps_error.cget("text"):
                self.refresh_session()
        elif text != str(self.app.settings.fps):
            self.apply_custom_fps(text)

    def _custom_cancel(self) -> None:
        self.refresh_session()
        self.focus_set()

    def _show_fps_error(self, text: str) -> None:
        self.fps_error.configure(text=text)
        place = {"before": self.fps_note if self.fps_note.winfo_manager() else self.timing_box}
        self._pack_if(self.fps_error, bool(text), pady=(self.app.px(10), 0), **place)

    def fps_note_text(self) -> str:
        return self.fps_note.cget("text") if self.fps_note.winfo_manager() else ""

    def fps_error_text(self) -> str:
        return self.fps_error.cget("text")

    def selected_fps(self) -> "int | None":
        value = self.fps_choice.value
        return value if isinstance(value, int) else parse_fps(self.custom.get())

    # ------------------------------------------------------------ display

    def set_timing(self, value: str) -> None:
        self.app.settings.patch_timing = value
        self._saved(self.app.save_settings())

    def set_fullscreen(self, on: bool) -> None:
        self.app.settings.fullscreen = bool(on)
        self._saved(self.app.save_settings())

    def selected_window(self) -> str:
        return self.window_choice.value

    def set_window_size(self, value: str) -> None:
        self.app.settings.window_size = value
        self._saved(self.app.save_settings())

    def set_render_res(self, value: str) -> None:
        self.app.settings.render_res = value
        self._saved(self.app.save_settings())
        self.refresh_session()

    def set_aspect(self, value: str) -> None:
        self.app.settings.aspect = value
        self._saved(self.app.save_settings())
        self.refresh_session()
        self.app.refresh_checks()

    def _fov_moved(self, value: float) -> None:
        self.fov_value.configure(text=f"{value:.2f}")

    def set_fov(self, value: float) -> None:
        self.app.settings.fov = round(float(value), 3)
        self._saved(self.app.save_settings())
        self.refresh_session()

    def set_fps_counter(self, on: bool) -> None:
        self._show_status(self.app.update_game_ini({"show_fps": "1" if on else "0"}) or "")
        self.refresh_session()

    def selected_fps_counter(self) -> bool:
        return bool(self.counter_choice.value)

    # ------------------------------------------------------------ upscaling (FSR edition)

    def has_upscaler_controls(self) -> bool:
        return self.upscaler_choice is not None

    def fsr4_available(self) -> bool:
        try:
            return any(self.app.paths.fsr4_dir.glob("fsr4_model_*.spv"))
        except OSError:
            return False

    def dlss_available(self) -> bool:
        """The DLSS files are installed and the GPU is NVIDIA (or not known yet)."""
        try:
            files = all((self.app.paths.bin / name).is_file() for name in DLSS_FILES)
        except OSError:
            return False
        gpu = self.app.gpu
        return files and (gpu is None or "nvidia" in gpu.lower())

    def _refresh_upscaling(self) -> None:
        ini = self.app.game_ini()
        current = ini.get("upscaler", "fsr3").strip()  # the runtime's default is FSR 3
        self.upscaler_choice.set(current)
        fsr4 = self.fsr4_available()
        self.upscaler_choice.set_enabled("fsr4", fsr4)
        dlss = self.dlss_available()
        self.upscaler_choice.set_enabled("dlss", dlss)
        ready411 = fsr411.available(self.app.paths)
        self.upscaler_choice.set_enabled("fsr411", ready411)
        if not self._fsr411_busy:
            self.fsr411_button.set("Rebuild FSR 4.1.1…" if ready411 else "Set up FSR 4.1.1…",
                                   enabled=fsr411.tools_present(self.app.paths))
            self.fsr411_status.configure(
                text="FSR 4.1.1 is set up." if ready411 else FSR411_HINT,
                fg=self.app.palette["muted"])
        known = {value for value, _ in UPSCALERS}
        if current == "dlss":
            note, role = (DLSS_NOTE, "muted") if dlss else (DLSS_MISSING, "warn")
        elif not fsr4:
            note, role = FSR4_MISSING, "warn" if current == "fsr4" else "muted"
        elif current not in known:
            note, role = f"Chosen in the game's menu: {current}", "muted"
        else:
            note, role = "", "muted"
        blur = current != "off" and patches.MOTION_BLUR in self.app.settings.patches
        if blur and not note:
            note, role = BLUR_NOTE, "warn"
        if current != "off" and not note:
            note = AA_NOTE
        self.upscaler_note.configure(text=note, fg=self.app.palette[role])
        self._pack_if(self.upscaler_note, bool(note), pady=(self.app.px(12), 0))
        try:
            sharpness = float(ini.get("sharpness", DEFAULT_SHARPNESS))
        except ValueError:
            sharpness = DEFAULT_SHARPNESS
        self.sharpness.set(sharpness)
        self.sharpness.set_enabled(current != "off")  # as in the game's menu
        self._sharpness_moved(self.sharpness.value)
        # Frame generation takes its depth and motion from the FSR anti-aliasing pass.
        self.frame_gen_choice.set(frame_gen_value(ini))
        for value, _ in FRAME_GEN_CHOICES:
            self.frame_gen_choice.set_enabled(value, value == "off" or current != "off")

    def setup_fsr411(self) -> None:
        """Builds fsr4_411/ from the player's DLL (dcport.fsr411), then selects FSR 4.1.1."""
        if self._fsr411_busy:
            return
        path = filedialog.askopenfilename(
            parent=self, title="Your amd_fidelityfx_upscaler_dx12.dll (FSR 4.1.1)",
            filetypes=[("FidelityFX upscaler", "amd_fidelityfx_upscaler_dx12.dll"),
                       ("DLL", "*.dll")])
        if not path:
            return
        self._fsr411_busy = True
        self._fsr411_progress = "Starting…"
        self.fsr411_button.set(enabled=False)

        def report(text: str) -> None:  # worker thread: only a string, the UI polls it
            self._fsr411_progress = text

        def poll() -> None:
            if self._fsr411_busy:
                self.fsr411_status.configure(text=self._fsr411_progress,
                                             fg=self.app.palette["muted"])
                self.app.after(300, poll)

        def done(result, error) -> None:
            self._fsr411_busy = False
            if error is None:
                self._show_status(self.app.update_game_ini({"upscaler": "fsr411"}) or "")
                self._refresh_upscaling()
                self.fsr411_status.configure(text="FSR 4.1.1 is set up and selected.",
                                             fg=self.app.palette["ok"])
            else:
                self._refresh_upscaling()
                text = str(error) if isinstance(error, fsr411.SetupError) else \
                    f"FSR 4.1.1 could not be set up: {error}"
                self.fsr411_status.configure(text=text, fg=self.app.palette["bad"])

        self.app.run_task(lambda: fsr411.build(self.app.paths, Path(path), report), done)
        poll()

    def fsr411_status_text(self) -> str:
        return self.fsr411_status.cget("text")

    def check_updates(self) -> None:
        """SETUP > Check for updates: the result shows in the status line."""
        def report(text: str, role: str) -> None:
            self.status.configure(text=text, fg=self.app.palette[role])
        report("Checking for updates…", "muted")
        self.app.check_for_updates(report)

    def set_threading(self, value: str) -> None:
        self._show_status(self.app.update_game_ini({"threaded_recording": value}) or "")
        self.threading_choice.set(threading_value(self.app.game_ini()))

    def set_readbacks(self, value: str) -> None:
        self._show_status(self.app.update_game_ini({"readbacks": value}) or "")
        self.readbacks_choice.set(readbacks_value(self.app.game_ini()))

    def set_player_name(self, text: str) -> None:
        name = "".join(c for c in text if c.isprintable()).strip()[:16]
        if not name or name == player_name(self.app.paths):
            self.player_name.set(player_name(self.app.paths))
            return
        self._show_status(self.app.update_game_ini({"player_name": name}) or
                          f"Player name: {name} (from the next start)")
        self.player_name.set(name)

    def _open_language_menu(self) -> None:
        if self._language_menu is not None:  # the previous popup; its command has run by now
            self._language_menu.destroy()
        menu = self._language_menu = theme.styled_menu(self, self.app)
        var = tk.StringVar(menu, value=game_language(self.app.paths))
        game_dir = self.app.settings.game_dir
        info = game_info(Path(game_dir)) if game_dir else None
        for code, name in languages_for(info.title_id if info else ""):
            menu.add_radiobutton(label=name, variable=var, value=code,
                                 command=lambda c=code: self.set_language(c))
        menu.update_idletasks()
        box = self.language_box
        try:
            menu.tk_popup(box.winfo_rootx(), box.winfo_rooty() + box.winfo_height() +
                          self.app.px(4))
        finally:
            menu.grab_release()

    def set_language(self, code: str) -> None:
        name = dict(LANGUAGES).get(code)
        if name is None or code == game_language(self.app.paths):
            return
        self._show_status(self.app.update_game_ini({"language": code}) or
                          f"Language: {name} (from the next start)")
        self.language_box.set(name)

    def language_text(self) -> str:
        return self.language_box.text

    def upscaler_note_text(self) -> str:
        if self.upscaler_choice is None or not self.upscaler_note.winfo_manager():
            return ""
        return self.upscaler_note.cget("text")

    def set_upscaler(self, value: str) -> None:
        # DCport runs DRIVECLUB's upscalers without subpixel jitter: it goes with every change
        self._show_status(self.app.update_game_ini({"upscaler": value, "jitter": "0"}) or "")
        self._refresh_upscaling()

    def set_frame_gen(self, value: str) -> None:
        self._show_status(self.app.update_game_ini({"frame_gen": value}) or "")
        self._refresh_upscaling()

    def _sharpness_moved(self, value: float) -> None:
        self.sharpness_value.configure(text=f"{value:.2f}")

    def sharpness_text(self) -> str:
        return self.sharpness_value.cget("text")

    def set_sharpness(self, value: float) -> None:
        value = min(1.0, max(0.0, float(value)))
        self._show_status(self.app.update_game_ini({"sharpness": f"{value:.2f}"}) or "")
        self._refresh_upscaling()
