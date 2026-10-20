# SPDX-License-Identifier: GPL-2.0-or-later
"""PATCHES page: the community game patches (patches/Driveclub.xml) to start with."""

import tkinter as tk

from dcport import patches
from dcport.ui import theme

HINT = "Applies on the next PLAY. Patches by the PS4 and shadPS4 DRIVECLUB community."
CARDS = (
    ("Garage", ("Unlock All Cars and Bikes",)),
    ("Driving", ("Barrier Disable", "Reset Disable")),
    ("Picture", ("Disable motion blur and depth of field",)),
    ("Photo mode", ("Disable Photomode Free Camera Collision", "Disable Photomode Processing")),
)


class PatchesPage(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        app.paint(self, bg="bg")
        bar = tk.Frame(self)
        app.paint(bar, bg="bg")
        bar.pack(side="bottom", fill="x", padx=app.px(24), pady=(app.px(16), app.px(20)))
        self.status = theme.text_label(bar, app, HINT, fg="muted", bg="bg")
        self.status.pack(side="left", fill="x", expand=True)
        self.board = theme.CardBoard(self, app, columns=2)
        self.board.pack(fill="x")
        toggles = {t.name: t for t in patches.TOGGLES}
        self.choices: dict[str, theme.Segmented] = {}
        for i, (title, names) in enumerate(CARDS):
            card = self.board.add(i // 2, i % 2, title=title)
            for j, name in enumerate(names):
                self._build_toggle(card, toggles[name], first=j == 0)
        app.on_theme(lambda pal: self.refresh_session())

    def _wrapping(self, label: tk.Label, master: tk.Misc) -> tk.Label:
        master.bind("<Configure>", lambda e: label.configure(wraplength=max(1, e.width)),
                    add="+")
        return label

    def _build_toggle(self, card, toggle: patches.Toggle, first: bool) -> None:
        app = self.app
        row = tk.Frame(card)
        app.paint(row, bg="panel")
        row.pack(fill="x", pady=(0 if first else app.px(14), 0))
        choice = theme.Segmented(row, app, ((True, "On"), (False, "Off")),
                                 lambda on, n=toggle.name: self.set_toggle(n, on),
                                 min_label="Off")
        choice.pack(side="right", anchor="n", padx=(app.px(12), 0))
        text = tk.Frame(row)
        app.paint(text, bg="panel")
        text.pack(side="left", fill="x", expand=True)
        theme.text_label(text, app, toggle.label, font="body_bold").pack(fill="x")
        note = theme.text_label(text, app, toggle.note, font="small", fg="muted")
        self._wrapping(note, text).pack(fill="x", pady=(app.px(2), 0))
        self.choices[toggle.name] = choice

    # ------------------------------------------------------------ showing

    def on_show(self) -> None:
        self.refresh_session()

    def refresh_session(self) -> None:
        """Runs after every settings save (App.save_settings)."""
        s = self.app.settings
        for name, choice in self.choices.items():
            choice.set(name in s.patches)

    def _saved(self, ok: bool) -> None:
        if ok:
            self.status.configure(text=HINT, fg=self.app.palette["muted"])
        else:
            self.status.configure(text="Could not save the settings file (dcport-launcher.json)",
                                  fg=self.app.palette["bad"])

    def set_toggle(self, name: str, on: bool) -> None:
        chosen = [n for n in self.app.settings.patches if n != name]
        if on:
            chosen.append(name)
        self.app.settings.patches = chosen
        self._saved(self.app.save_settings())

    def enabled_patches(self) -> list[str]:
        return [n for n, c in self.choices.items() if c.value]
