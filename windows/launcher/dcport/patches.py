# SPDX-License-Identifier: GPL-2.0-or-later
"""Which of DRIVECLUB's community patches (patches/Driveclub.xml) a session runs with.

The PATCHES page picks the optional ones, SETUP's Render resolution picks a resolution
group (its internal and output patches and the memory patch it needs), and the frame rate
decides on the 60 FPS patch. data/patches.bin is compiled from that list before each start,
so a change applies on the next PLAY without preparing the game again.
"""

import struct
from dataclasses import dataclass
from pathlib import Path

from dcport.settings import LauncherSettings

DEFAULT_DMEM_MB = 5056  # the PS4's direct memory, the runtime's default


@dataclass(frozen=True)
class Toggle:
    name: str  # <Metadata Name=...> in Driveclub.xml
    label: str
    note: str


MOTION_BLUR = "Disable motion blur and depth of field"
TOGGLES = (
    Toggle(MOTION_BLUR, "No motion blur or depth of field",
           "A sharper picture in motion. The game uses one shader for both, and for its "
           "anti-aliasing: with this on, FSR cannot run."),
    Toggle("Unlock All Cars and Bikes", "All cars and bikes",
           "Every car and bike from the start: the club cars that needed the DRIVECLUB server, "
           "and the Driver Level ones too (the game's own unlockAll option). Patch by illusion."),
    Toggle("Barrier Disable", "No track barriers",
           "Drive off the track without the invisible walls."),
    Toggle("Reset Disable", "No reset to track",
           "The car is not put back on the track when you leave it."),
    Toggle("Disable Photomode Free Camera Collision", "Photo mode: free camera",
           "The camera passes through cars, so you can look inside them."),
    Toggle("Disable Photomode Processing", "Photo mode: no processing",
           "Photo mode shows the frame as it is, without its filters."),
)
DEFAULT_TOGGLES = ()

# The frame-rate patch above 30 FPS; "fixed" is the engine's own 60 Hz tick, which keeps the
# few features that the deltatime version breaks.
TIMING = {
    "deltatime": "60 FPS with deltatime",
    "fixed": "60 FPS with fixed tickrate",
}
DEFAULT_TIMING = "deltatime"


@dataclass(frozen=True)
class Resolution:
    key: str
    label: str
    size: tuple[int, int]
    patches: tuple[str, ...]
    extra_dmem_mb: int
    game_args: str = ""  # the game's own command-line switches (runtime: DC_GAME_ARGS)


# The game renders at its own 1920x1080. The community "Internal resolution" patches only
# change the engine's scene-size table and leave some passes at 1080p (a square at x 1920 /
# y 1080). Above 1080p the engine is asked instead through its own -resolutionscale switch,
# which sizes every render target itself; the Output patch sizes the display buffers and the
# Memory patch grows the game's video-memory budget (SETUP > Render).
RESOLUTIONS = (
    Resolution("1080p", "1080p", (1920, 1080), (), 0),
    Resolution("1440p", "1440p", (2560, 1440),
               ("1440p [2560x1440] Output resolution", "Memory for up to 1440p"), 3000,
               "-resolutionscale 1.3333"),
    Resolution("2160p", "4K", (3840, 2160),
               ("4K [3840x2160] Output resolution", "Memory for up to 4K"), 5000,
               "-resolutionscale 2"),
)
DEFAULT_RESOLUTION = "1080p"

# Ultrawide (SETUP > Aspect ratio): the game's camera aspect, a wider field of view, its scene
# rendered at the wide size and display buffers to match, written straight into the 01.28
# eboot. After rafidwayne's Driveclub_Widescreen and the Driveclub-PC wrapper's extension of
# it (both GPL-2.0-or-later). The HUD stays in the centred 16:9 area.
ASPECTS = ("16:9", "21:9", "32:9")
DEFAULT_ASPECT = "16:9"
# The output of a wide shape at the render resolution's lines (common monitor sizes); the
# memory budget holds up to 1440 wide lines, so 4K falls back to them.
WIDE_OUTPUTS = {
    ("21:9", 1080): (2560, 1080), ("21:9", 1440): (3440, 1440),
    ("32:9", 1080): (3840, 1080), ("32:9", 1440): (5120, 1440),
}
# The game's field-of-view factor is 0.5 at 16:9; the value of the community "FOV fix for wide
# resolutions" (0.65625) is the default for both wide shapes, tested on 32:9 by players. Hor+
# (the 16:9 view widened to the screen) is 0.5 * aspect / (16 / 9): 0.67 at 21:9, 1.0 at 32:9.
DEFAULT_FOV = 0.65625
FOV_MIN, FOV_MAX = 0.5, 1.0

# Image offsets in the 01.28 eboot (patch address minus 0x400000).
_ASPECT = 0x729978  # f32 camera aspect, 16/9
_FOV = 0x12efac4  # f32 field-of-view factor, 0.5
_VIDEO_OUT = (0x754c1b, 0x754c21)  # u32 immediates of the display buffer size, 1920 / 1080
# Scene-size table read when the render targets are created, indexed by the engine's mode.
_SCENE_WIDTHS = 0x12d0540
_TABLE_WIDTHS = (1280, 1920, 2560, 4096)
# With -resolutionscale the engine makes the scene height width * 9 / 16 (lea ecx, [rcx+rcx*8];
# shr ecx, 4; mov [rbp-0xac], ecx). Rewritten in place to width * k >> n for the output's
# aspect: imul ecx, ecx, k; shr ecx, n; the same mov. (The runtime maps no free code to jump to.)
_HEIGHT_SITE = 0x4dc37a


@dataclass(frozen=True)
class Display:
    size: tuple[int, int]  # the game's output (display buffers)
    lines: int  # render lines: 1080, 1440 or 2160
    wide: bool

# The window in windowed mode; fullscreen always covers the monitor.
WINDOW_SIZES = ((1280, 720), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160))
DEFAULT_WINDOW = "1920x1080"


def resolution(key: str) -> Resolution:
    for r in RESOLUTIONS:
        if r.key == key:
            return r
    return RESOLUTIONS[0]


def window_size(text: str) -> tuple[int, int]:
    for w, h in WINDOW_SIZES:
        if text == f"{w}x{h}":
            return w, h
    return 1920, 1080


def aspect(s: LauncherSettings) -> str:
    return s.aspect if s.aspect in ASPECTS else DEFAULT_ASPECT


def fov(s: LauncherSettings) -> float:
    return min(max(float(s.fov), FOV_MIN), FOV_MAX)


def display(s: LauncherSettings) -> Display:
    r = resolution(s.render_res)
    lines = r.size[1]
    shape = aspect(s)
    if shape == DEFAULT_ASPECT:
        return Display(r.size, lines, False)
    lines = max(n for s, n in WIDE_OUTPUTS if s == shape and n <= lines)
    return Display(WIDE_OUTPUTS[shape, lines], lines, True)


def screen_aspect(w: int, h: int) -> str:
    """The Aspect ratio setting for a screen: 32:9 from 3:1 up, 21:9 from 2.2:1, else 16:9
    (16:10 and narrower show the 16:9 picture with bars)."""
    ratio = w / h
    return "32:9" if ratio >= 3.0 else "21:9" if ratio >= 2.2 else "16:9"


def screen_hint(screen: "tuple[int, int] | None", s: LauncherSettings) -> "tuple[str, str] | None":
    """(text, "ok" | "warn") about the Aspect ratio for this screen; None on an ordinary 16:9
    screen with the 16:9 setting (nothing to say)."""
    if not screen:
        return None
    w, h = screen
    wanted, chosen = screen_aspect(w, h), aspect(s)
    if wanted == chosen:
        return (f"Screen {w}x{h}: aspect ratio {chosen}", "ok") if chosen != DEFAULT_ASPECT else None
    if wanted == DEFAULT_ASPECT:
        return (f"Screen {w}x{h} is not ultrawide: set SETUP > Aspect ratio to 16:9", "warn")
    return (f"Ultrawide screen {w}x{h}: set SETUP > Aspect ratio to {wanted} for the full "
            "picture", "warn")


def window(s: LauncherSettings) -> tuple[int, int]:
    """The windowed-mode size: the chosen lines at the output's aspect."""
    w, h = window_size(s.window_size)
    d = display(s)
    if d.wide:
        w = round(h * d.size[0] / d.size[1] / 2) * 2
    return w, h


def hor_plus(s: LauncherSettings) -> float:
    """The field-of-view factor that keeps the 16:9 view's height (Hor+)."""
    w, h = display(s).size
    return 0.5 * (w / h) / (16 / 9)


def _scene_width(table_width: int, w: int, h: int) -> int:
    # Rounded to a multiple of 128 like the engine's own -resolutionscale widths.
    wide = int((table_width * (w / h) / (16 / 9) + 64) // 128) * 128
    return max(wide, table_width)


def _height_code(w: int, h: int) -> bytes:
    """The scene height as width * h / w: k / 2^n with the largest n that keeps k an imm8."""
    n = 0
    while n < 16 and round(h / w * (1 << (n + 1))) <= 127:
        n += 1
    k = round(h / w * (1 << n))
    return bytes((0x6B, 0xC9, k, 0xC1, 0xE9, n)) + bytes.fromhex("898d54ffffff")


def wide_writes(s: LauncherSettings) -> list[tuple[int, bytes]]:
    """The ultrawide writes (image offset, bytes) for the session; none at 16:9."""
    d = display(s)
    if not d.wide:
        return []
    w, h = d.size
    writes = [
        (_ASPECT, struct.pack("<f", w / h)),
        (_FOV, struct.pack("<f", fov(s))),
        (_VIDEO_OUT[0], struct.pack("<I", w)),
        (_VIDEO_OUT[1], struct.pack("<I", h)),
        (_SCENE_WIDTHS, struct.pack("<4I", *(_scene_width(t, w, h) for t in _TABLE_WIDTHS))),
    ]
    if d.lines != 1080:  # the engine's -resolutionscale
        writes.append((_HEIGHT_SITE, _height_code(w, h)))
    return writes


def _memory_patch(w: int, h: int) -> tuple[str, int]:
    if w * h <= 2560 * 1440:
        return "Memory for up to 1440p", 3000
    return "Memory for up to 4K", 5000


def patch_names(s: LauncherSettings) -> list[str]:
    """The patches of a session, in Driveclub.xml's own names."""
    names: list[str] = []
    if s.fps != 30:  # 30 FPS is the game's original timing
        names.append(TIMING.get(s.patch_timing, TIMING[DEFAULT_TIMING]))
    known = {t.name for t in TOGGLES}
    names += [n for n in s.patches if n in known]
    d = display(s)
    if d.wide:  # the display buffers are in wide_writes
        names.append(_memory_patch(*d.size)[0])
    else:
        names += resolution(s.render_res).patches
    return names


def game_args(s: LauncherSettings) -> str:
    d = display(s)
    if d.wide:
        return "-resolutionscale 1.3333" if d.lines == 1440 else ""
    return resolution(s.render_res).game_args


def dmem_mb(s: LauncherSettings) -> int:
    d = display(s)
    if d.wide:
        return DEFAULT_DMEM_MB + _memory_patch(*d.size)[1]
    return DEFAULT_DMEM_MB + resolution(s.render_res).extra_dmem_mb


def build(game_dir: Path, xml: Path, out: Path, names: list[str],
          extra: "list[tuple[int, bytes]]" = ()) -> None:
    """Compile data/patches.bin (the named patches, then the extra writes); rewritten only
    when its bytes change."""
    import dcport.prepare_state  # noqa: F401  (puts the prepare tool on sys.path in dev)
    import dc_patches  # from the bundled prepare tool (launcher-app/prepare)

    tmp = out.with_suffix(".new")
    try:
        dc_patches.compile_patches(game_dir, xml, tmp, names, extra)
    except SystemExit as e:  # its error for a name missing from the xml
        tmp.unlink(missing_ok=True)
        raise ValueError(str(e.code)) from None
    data = tmp.read_bytes()
    if out.exists() and out.read_bytes() == data:
        tmp.unlink()
        return
    tmp.replace(out)


def build_for_session(paths, game_dir: Path, s: LauncherSettings) -> "str | None":
    """data/patches.bin for the settings; returns an error to show, the game still starts
    with the previous patches.bin."""
    try:
        build(game_dir, paths.patches_xml, paths.data / "patches.bin", patch_names(s),
              wide_writes(s))
    except (OSError, ValueError, ImportError) as e:
        return f"Could not apply the patches: {e}"
    return None
