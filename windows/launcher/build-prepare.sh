#!/usr/bin/env bash
# Usage: build-prepare.sh   Builds dist/prepare/dc-prepare.exe (bin\dc-prepare.exe in a release) with
# PyInstaller: prepare/dc_prepare.py, capstone (red-zone analysis, legacy CPU plan) and
# keystone (legacy CPU plan, prepare/cpu_plan.py; built on the player's PC, never shipped).
set -euo pipefail
cd "$(dirname "$0")"
python -m PyInstaller --noconfirm --onefile --console --name dc-prepare \
    --paths prepare --collect-all capstone --exclude-module numpy \
    --collect-all keystone \
    --distpath dist/prepare --workpath build/prepare prepare/dc_prepare.py
ls -l dist/prepare/dc-prepare.exe
