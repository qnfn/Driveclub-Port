# SPDX-License-Identifier: GPL-2.0-or-later
"""Legacy CPU profile (prepare/cpu_compat.py, issue #13): the plan is built on the player's PC
(dc_prepare -> cpu_plan) and passed in BB_LEGACY_CPU_PLAN; none ships with DCport."""
import dcport.prepare_state  # noqa: F401  (puts prepare/ on sys.path)
import cpu_compat


def test_plan_comes_from_the_path_dc_prepare_sets(tmp_path, monkeypatch):
    monkeypatch.setenv("BB_LEGACY_CPU_PLAN", str(tmp_path / "legacy-cpu-plan.json"))
    assert cpu_compat.plan_path() == tmp_path / "legacy-cpu-plan.json"


def test_missing_plan_leaves_image_untranslated(tmp_path, monkeypatch):
    monkeypatch.setenv("BB_LEGACY_CPU_PLAN", str(tmp_path / "none.json"))
    image = bytes(range(256)) * 16
    segments = [(0, len(image), 5)]
    result, new_segments, report = cpu_compat.patch_image(
        image, segments, {"sha256": "0" * 64}, [], [], active=True)
    assert bytes(result) == image
    assert new_segments == segments
    assert report["enabled"] is True
    assert report["patched_sites"] == 0
    assert "no legacy CPU translation plan" in report["skipped"]


def test_module_names_from_the_game_folder_match_the_plan():
    """Driveclub links ../libtbb.prx and others from the game folder: the plan names them
    libtbb.prx, so the module check must not reject the path."""
    import pytest
    modules = [{"file": "../libtbb.prx", "base": 0x100, "size": 0x100, "sha256": "1" * 64}]
    plan = {"version": 4, "modules": {"eboot.bin": "0" * 64, "libtbb.prx": "1" * 64},
            "sites": [], "unhandled": []}
    image = bytes(0x200)
    _, _, report = cpu_compat.patch_image(image, [(0, 0x200, 5)], {"sha256": "0" * 64},
                                          modules, [], plan=plan, active=True)
    assert report["source_hashes"]["libtbb.prx"] == "1" * 64
    plan["modules"]["libtbb.prx"] = "2" * 64
    with pytest.raises(ValueError, match="does not match the plan"):
        cpu_compat.patch_image(image, [(0, 0x200, 5)], {"sha256": "0" * 64}, modules, [],
                               plan=plan, active=True)
