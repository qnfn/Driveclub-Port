# SPDX-License-Identifier: GPL-2.0-or-later
"""Game command line, environment and frame-rate rules."""

from collections.abc import Mapping, Sequence
from pathlib import Path

from dcport.ini import read_ini
from dcport.paths import AppPaths
from dcport.patches import UPSCALES, dmem_mb, game_args, upscale_factor, window
from dcport.settings import LauncherSettings

FPS_PRESETS = (30, 60, 75, 90, 120, 144)
FPS_MIN = 30
FPS_MAX = 240
FPS_TESTED = 120


def parse_fps(text: str) -> int | None:
    text = text.strip()
    if not (text.isascii() and text.isdigit()):
        return None
    value = int(text)
    return value if FPS_MIN <= value <= FPS_MAX else None


def fps_note(fps: int) -> str:
    if fps > FPS_TESTED:
        return "DRIVECLUB was tested up to 120 FPS; above that its timing may suffer."
    return ""


def _ini_value(paths: AppPaths, key: str, default: str) -> str:
    try:
        return read_ini(paths.ini).get(key, default).strip()
    except OSError:
        return default


DEFAULT_PLAYER_NAME = "Player"


def player_name(paths: AppPaths) -> str:
    """dcport.ini player_name (SETUP > Player name): the name the game shows for the player.
    Printable characters only, at most 16 (a PSN online ID's length)."""
    raw = _ini_value(paths, "player_name", DEFAULT_PLAYER_NAME)
    name = "".join(c for c in raw if c.isprintable()).strip()[:16]
    return name or DEFAULT_PLAYER_NAME


# PS4 system language codes (SystemService parameter 1); the game picks its text from it.
# Each region's game has its own languages: other codes show English.
LANGUAGES_EU = (  # CUSA00003
    ("1", "English"), ("2", "Français"), ("4", "Deutsch"), ("5", "Italiano"), ("3", "Español"),
    ("7", "Português"), ("6", "Nederlands"), ("16", "Polski"), ("8", "Русский"),
    ("19", "Türkçe"), ("13", "Svenska"), ("14", "Dansk"), ("15", "Norsk"), ("12", "Suomi"),
)
LANGUAGES_US = (  # CUSA00093
    ("1", "English"), ("2", "Français"), ("17", "Português (Brasil)"),
    ("20", "Español (Latinoamérica)"),
)
LANGUAGES = LANGUAGES_EU + LANGUAGES_US[2:]


def languages_for(title_id: str) -> tuple[tuple[str, str], ...]:
    """The languages of this region's game (CUSA00003 EU, CUSA00093 US); both if unknown."""
    if title_id == "CUSA00003":
        return LANGUAGES_EU
    if title_id == "CUSA00093":
        return LANGUAGES_US
    return LANGUAGES


DEFAULT_LANGUAGE = "1"


def game_language(paths: AppPaths) -> str:
    """dcport.ini language (SETUP > Language): a PS4 system language code, English (US) if
    missing or unknown."""
    value = _ini_value(paths, "language", DEFAULT_LANGUAGE)
    return value if value in dict(LANGUAGES) else DEFAULT_LANGUAGE



def ui_fit(paths: AppPaths) -> str:
    """dcport.ini ui_fit (SETUP > UI): "1" fits the 16:9 menus and HUD to a 4:3 or 16:10
    screen's width (the default), "0" stretches them to the whole screen."""
    return "0" if _ini_value(paths, "ui_fit", "1") == "0" else "1"


def game_command(paths: AppPaths, game_dir: Path, fps: int,
                 extra: Sequence[str] = ()) -> list[str]:
    cmd = [str(paths.runtime), str(paths.data / "boot-linked.bin"),
           "--content-profile", str(paths.data / "content.bin")]
    patches = paths.data / "patches.bin"  # compiled for this session (dcport.patches)
    if patches.exists():
        cmd += ["--patches", str(patches)]
    cmd += ["--app0", str(game_dir), "--user", str(paths.user), "--timeout", "0"]
    cmd += list(extra)
    return cmd


def scaling(paths: AppPaths, s: LauncherSettings) -> str:
    """SETUP's Scaling (an UPSCALES key): dcport.ini preset, the runtime's preset number in
    UPSCALES order, which the in-game menu changes too; the launcher's own setting when the
    file has none."""
    value = _ini_value(paths, "preset", "")
    if value.isascii() and value.isdigit() and int(value) < len(UPSCALES):
        return UPSCALES[int(value)][0]
    return s.upscale


def scaling_ini(key: str) -> dict[str, str]:
    """The dcport.ini line for an UPSCALES key (Native for an unknown one)."""
    keys = [k for k, _, _ in UPSCALES]
    return {"preset": str(keys.index(key) if key in keys else 0)}


def session_upscale(paths: AppPaths, s: LauncherSettings, fsr: bool) -> float:
    """Output size over scene size for the session: SETUP's Upscaling, only in the FSR edition
    with FSR or DLSS on (dcport.ini upscaler, FSR 3.1 when missing, as in the runtime). Off
    keeps the game's own anti-aliasing, which would only stretch a smaller picture."""
    if not fsr or _ini_value(paths, "upscaler", "fsr3") == "off":
        return 1.0
    return upscale_factor(scaling(paths, s))


def game_env(paths: AppPaths, s: LauncherSettings, fsr: bool,
             base: Mapping[str, str]) -> dict[str, str]:
    env = dict(base)
    env.update({
        "BB_GPU_USER_DIR": str(paths.user),
        "BB_CONFIG": str(paths.ini),
        "BB_LENIENT_IMPORTS": "1",
        "BB_READBACKS": "0",
        "BB_DRAW_PIPE": "1",
        "BB_PREP_WORKERS": "0",
        "BB_FULLSCREEN": "1" if s.fullscreen else "0",
        "BB_WINDOW_SIZE": "{}x{}".format(*window(s)),
        "BB_DMEM_MB": str(dmem_mb(s)),
        "BB_USER_NAME": player_name(paths),
        "DC_LANGUAGE": game_language(paths),
    })
    # dcport.ini readbacks=2 (precise; 1 = 0.4.4's relaxed, runs precise too), SETUP > GPU readbacks
    # On, the default: the game gets GPU results exactly when it asks. 0 copies them back once per
    # frame, which loses the roadside grass (issue #3) and stretches geometry from the second event
    # on (stale GPU data).
    readbacks = _ini_value(paths, "readbacks", "2")
    if readbacks in ("1", "2"):
        env["BB_READBACKS"] = "2"
    # Older CPUs (#13): dc-prepare keeps legacy-cpu-plan.json in the data folder only when it
    # translated the game's BMI1/LZCNT/MOVBE instructions; the runtime then starts on such a CPU.
    env.pop("BB_CPU_COMPAT", None)
    if (paths.data / "legacy-cpu-plan.json").is_file():
        env["BB_CPU_COMPAT"] = "1"
    env.pop("DC_GAME_ARGS", None)
    if args := game_args(s, session_upscale(paths, s, fsr)):
        env["DC_GAME_ARGS"] = args
    # dcport.ini threaded_recording=0/1 (SETUP > Threading); Auto (anything else) lets the
    # runtime decide: off (it can crash mid-race).
    env.pop("BB_THREADED_RECORDING", None)
    threading = _ini_value(paths, "threaded_recording", "auto")
    if threading in ("0", "1"):
        env["BB_THREADED_RECORDING"] = threading
    # dcport.ini aniso=4/8/16 (SETUP > Texture filtering): anisotropic filtering forced on the
    # game's colour textures (runtime DC_ANISO); anything else keeps the game's own.
    env.pop("DC_ANISO", None)
    aniso = _ini_value(paths, "aniso", "0")
    if aniso in ("4", "8", "16"):
        env["DC_ANISO"] = aniso
    # dcport.ini overlays=block (SETUP > Overlays): other programs' implicit Vulkan layers
    # (overlays, capture tools, AMD's switchable-graphics layer) are not loaded; some crash the
    # game or leave a black window. Idea from driveclub-recomp 01b8bed.
    env.pop("VK_LOADER_LAYERS_DISABLE", None)
    if _ini_value(paths, "overlays", "allow") == "block":
        env["VK_LOADER_LAYERS_DISABLE"] = "~implicit~,VK_LAYER_AMD_switchable_graphics"
    # dcport.ini ui_fit=0 (SETUP > UI on 4:3 and 16:10: Stretch): the 16:9 menus and HUD are
    # stretched to the screen instead of fitted to its width; the 3D view stays unstretched.
    env.pop("BB_DC_UI_FIT", None)
    if ui_fit(paths) == "0":
        env["BB_DC_UI_FIT"] = "0"
    if s.fps == 30:
        env["BB_VBLANK_HZ"] = "60"
        env["BB_FPS_LIMIT"] = "0"
    else:
        env["BB_VBLANK_HZ"] = str(s.fps)
        env["BB_FPS_LIMIT"] = str(s.fps)
    # The in-game menu's "Apply and restart" (a new Scaling is a -resolutionscale and patches
    # at start): the game starts the launcher's --play again, which builds them anew.
    launcher = paths.root / "DriveClub.exe"
    if launcher.is_file():
        env["BB_RESTART_COMMAND"] = f'"{launcher}" --play'
    else:
        env.pop("BB_RESTART_COMMAND", None)
    if fsr:
        env.pop("BB_UPSCALER", None)
        env["BB_DC_UPSCALE"] = "1"
        # The 1080p frame scaled to a bigger window or screen with FSR 1 and RCAS.
        env["BB_FSR1"] = "1"
        env["BB_FSR4_DIR"] = str(paths.fsr4_dir)
        env["BB_FSR411_DIR"] = str(paths.root / "fsr4_411")  # built by SETUP (dcport.fsr411)
    else:
        env.pop("BB_FSR4_DIR", None)
        env.pop("BB_FSR1", None)
        env["BB_UPSCALER"] = "none"
        env["BB_DC_UPSCALE"] = "0"
    return env
