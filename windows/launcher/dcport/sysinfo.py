# SPDX-License-Identifier: GPL-2.0-or-later
import subprocess

_CMD = (
    "Get-CimInstance Win32_VideoController | "
    "Where-Object { $_.Name -and $_.Name -notlike '*Microsoft Basic*' } | "
    "Sort-Object AdapterRAM -Descending | "
    "Select-Object -First 1 -ExpandProperty Name"
)


def gpu_name() -> str | None:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
             "-Command", _CMD],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            return None
        name = r.stdout.strip()
        return name or None
    except Exception:
        return None


def screen_size() -> "tuple[int, int] | None":
    """The primary monitor's current mode in real pixels (not scaled by Windows' DPI)."""
    try:
        import ctypes
        from ctypes import wintypes

        class DEVMODEW(ctypes.Structure):
            _fields_ = [("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
                        ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
                        ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
                        ("dmPosition", wintypes.LONG * 2),
                        ("dmDisplayOrientation", wintypes.DWORD),
                        ("dmDisplayFixedOutput", wintypes.DWORD), ("dmColor", ctypes.c_short),
                        ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
                        ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short),
                        ("dmFormName", wintypes.WCHAR * 32), ("dmLogPixels", wintypes.WORD),
                        ("dmBitsPerPel", wintypes.DWORD), ("dmPelsWidth", wintypes.DWORD),
                        ("dmPelsHeight", wintypes.DWORD), ("dmDisplayFlags", wintypes.DWORD),
                        ("dmDisplayFrequency", wintypes.DWORD)]

        mode = DEVMODEW()
        mode.dmSize = ctypes.sizeof(DEVMODEW)
        if not ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(mode)):
            return None  # -1: ENUM_CURRENT_SETTINGS
        if mode.dmPelsWidth and mode.dmPelsHeight:
            return int(mode.dmPelsWidth), int(mode.dmPelsHeight)
    except (AttributeError, OSError, ValueError):
        pass
    return None
