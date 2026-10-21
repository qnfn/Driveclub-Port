# SPDX-License-Identifier: GPL-2.0-or-later
import xml.etree.ElementTree as ET
from pathlib import Path

from dcport import patches
from dcport.settings import LauncherSettings

XML = Path(__file__).resolve().parents[2] / "patches" / "Driveclub.xml"


def xml_names() -> set[str]:
    return {m.get("Name") for m in ET.parse(XML).getroot().iter("Metadata")
            if m.get("AppVer") == "01.28"}


def test_every_name_is_in_the_xml():
    names = xml_names()
    wanted = [t.name for t in patches.TOGGLES] + list(patches.TIMING.values())
    wanted += [p for r in patches.RESOLUTIONS for p in r.patches]
    assert [w for w in wanted if w not in names] == []


def test_default_session_is_the_60_fps_patch():
    assert patches.patch_names(LauncherSettings()) == ["60 FPS with deltatime"]
    assert patches.dmem_mb(LauncherSettings()) == patches.DEFAULT_DMEM_MB


def test_30_fps_has_no_frame_rate_patch_but_keeps_toggles():
    s = LauncherSettings(fps=30, patches=["Barrier Disable"])
    assert patches.patch_names(s) == ["Barrier Disable"]


def test_unknown_names_and_keys_are_ignored():
    s = LauncherSettings(patches=["Barrier Disable", "Run without sysmodules", "bogus"],
                         patch_timing="weird", render_res="16k")
    assert patches.patch_names(s) == ["60 FPS with deltatime", "Barrier Disable"]


def test_render_above_1080p_uses_the_engine_scale_not_the_internal_patch():
    s = LauncherSettings(patch_timing="fixed", render_res="1440p")
    assert patches.patch_names(s) == ["60 FPS with fixed tickrate",
                                      "1440p [2560x1440] Output resolution",
                                      "Memory for up to 1440p"]
    assert patches.dmem_mb(s) == 5056 + 3000
    assert patches.game_args(s) == "-resolutionscale 1.3333"
    assert patches.game_args(LauncherSettings(render_res="2160p")) == "-resolutionscale 2"
    assert patches.game_args(LauncherSettings()) == ""
    assert not any("Internal" in p for r in patches.RESOLUTIONS for p in r.patches)


def test_window_size():
    assert patches.window_size("2560x1440") == (2560, 1440)
    assert patches.window_size("1234x567") == (1920, 1080)


def test_16_9_has_no_wide_writes():
    assert patches.wide_writes(LauncherSettings()) == []
    assert patches.wide_writes(LauncherSettings(aspect="bogus")) == []


def test_32_9_at_1080p_matches_the_community_patches():
    s = LauncherSettings(aspect="32:9")
    writes = dict(patches.wide_writes(s))
    # Values of "Resolution patch (3840x1080)" and "FOV fix for wide resolutions".
    assert writes[0xB29978 - 0x400000].hex() == "398e6340"
    assert writes[0xB54C1B - 0x400000].hex() == "000f0000"
    assert writes[0xB54C21 - 0x400000].hex() == "38040000"
    assert writes[0x16EFAC4 - 0x400000].hex() == "0000283f"
    assert patches.display(s).size == (3840, 1080)
    assert patches.game_args(s) == ""
    assert patches.patch_names(s) == ["60 FPS with deltatime", "Memory for up to 4K"]
    assert patches.dmem_mb(s) == 5056 + 5000
    assert len(writes) == 5  # no -resolutionscale stub at 1080 lines


def test_fov_is_configurable_and_clamped():
    import struct
    fov = lambda v: struct.unpack("<f", dict(patches.wide_writes(
        LauncherSettings(aspect="21:9", fov=v)))[0x12EFAC4])[0]
    assert fov(0.8) == struct.unpack("<f", struct.pack("<f", 0.8))[0]
    assert fov(5) == 1.0 and fov(0.1) == 0.5
    assert round(patches.hor_plus(LauncherSettings(aspect="32:9")), 4) == 1.0


def test_wide_1440p_and_4k_rewrite_the_scale_height():
    s = LauncherSettings(aspect="21:9", render_res="2160p")
    assert patches.display(s).size == (3440, 1440)  # 4K falls back to 1440 lines
    assert patches.game_args(s) == "-resolutionscale 1.3333"
    code = dict(patches.wide_writes(s))[0x4DC37A]
    assert len(code) == 12 and code[:2] == b"\x6b\xc9" and code[3:5] == b"\xc1\xe9"
    assert code[6:] == bytes.fromhex("898d54ffffff")  # the engine's own store
    assert abs(3456 * code[2] / (1 << code[5]) - 3456 * 1440 / 3440) < 4
    s = LauncherSettings(aspect="32:9", render_res="1440p")
    code = dict(patches.wide_writes(s))[0x4DC37A]
    assert 5120 * code[2] >> code[5] == 1440


def test_wide_window_follows_the_aspect():
    s = LauncherSettings(aspect="32:9", window_size="1280x720")
    assert patches.window(s) == (2560, 720)
    assert patches.window(LauncherSettings(window_size="1280x720")) == (1280, 720)


def test_screen_hint():
    wide = LauncherSettings(aspect="32:9")
    assert patches.screen_aspect(3840, 1080) == "32:9"
    assert patches.screen_aspect(5120, 1440) == "32:9"
    assert patches.screen_aspect(2560, 1080) == "21:9"
    assert patches.screen_aspect(3440, 1440) == "21:9"
    assert patches.screen_aspect(1920, 1200) == "16:10"
    assert patches.screen_aspect(1920, 1080) == "16:9"
    assert patches.screen_aspect(1600, 1200) == "4:3"
    assert patches.screen_aspect(1280, 1024) == "4:3"
    assert patches.screen_hint(None, wide) is None
    assert patches.screen_hint((1920, 1080), LauncherSettings()) is None
    text, state = patches.screen_hint((3840, 1080), LauncherSettings())
    assert state == "warn" and "32:9" in text
    assert patches.screen_hint((3840, 1080), wide)[1] == "ok"
    assert patches.screen_hint((1920, 1080), wide)[1] == "warn"


def test_4_3_narrows_the_scene_and_keeps_the_16_9_view():
    import struct
    s = LauncherSettings(aspect="4:3", fov=0.9)
    d = patches.display(s)
    assert d.size == (1440, 1080) and d.narrow and not d.wide
    writes = dict(patches.wide_writes(s))
    assert struct.unpack("<f", writes[0x729978])[0] == struct.unpack("<f", struct.pack("<f", 4 / 3))[0]
    assert struct.unpack("<f", writes[0x12EFAC4])[0] == 0.5  # the slider is for wide shapes
    assert struct.unpack("<II", writes[0x754C1B][:4] + writes[0x754C21][:4]) == (1440, 1080)
    assert struct.unpack("<4I", writes[0x12D0540]) == (960, 1440, 1920, 3072)
    assert len(writes) == 5
    assert patches.game_args(s) == ""
    assert patches.patch_names(s) == ["60 FPS with deltatime"]  # fewer pixels than 1080p
    assert patches.dmem_mb(s) == 5056
    assert patches.window(LauncherSettings(aspect="4:3", window_size="1920x1080")) == (1440, 1080)


def test_narrow_1440_lines():
    s = LauncherSettings(aspect="4:3", render_res="1440p")
    assert patches.display(s).size == (1920, 1440)
    assert patches.game_args(s) == "-resolutionscale 1.3333"
    assert patches.patch_names(s)[-1] == "Memory for up to 1440p"
    code = dict(patches.wide_writes(s))[0x4DC37A]
    assert 1920 * code[2] >> code[5] == 1440  # 1440 x 1.3333 = 1920 wide
    s = LauncherSettings(aspect="16:10", render_res="1440p")
    assert patches.display(s).size == (2304, 1440)
    widths = struct_widths(s)
    assert widths[1] == 1728 and round(widths[1] * 4 / 3) == 2304


def struct_widths(s):
    import struct
    return struct.unpack("<4I", dict(patches.wide_writes(s))[0x12D0540])


def test_narrow_screen_hint():
    text, state = patches.screen_hint((1600, 1200), LauncherSettings())
    assert state == "ok" and "4:3" in text and "cut off" in text
    assert patches.screen_hint((1600, 1200), LauncherSettings(aspect="4:3"))[1] == "ok"
    assert patches.screen_hint((1600, 1200), LauncherSettings(aspect="32:9"))[1] == "warn"
    assert patches.screen_hint((1920, 1080), LauncherSettings(aspect="4:3"))[1] == "warn"
