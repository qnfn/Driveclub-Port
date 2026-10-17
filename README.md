# Driveclub Native — Windows (DCport)

**DRIVECLUB** (PS4, CUSA00003, v1.28) running natively on **Windows 10/11**. The game's own x86-64 code runs directly on the PC; its graphics are translated to Vulkan (shadPS4's renderer), with FSR 3.1 / FSR 4.

This is the Windows backend of [Driveclub Native](https://github.com/BlackLineInteractive/Driveclub-Port). The macOS (Metal) port is [BlackLineInteractive](https://github.com/BlackLineInteractive)'s work and lives in his repository; its source is kept here unchanged in `src/`.

![DCport launcher](windows/media/launcher.png)
![DRIVECLUB BIKES on Windows, FSR 4](windows/media/ingame-bike.png)
![Event preview on Windows, FSR 4](windows/media/ingame-track.png)

## Features

- **Up to 120 FPS and beyond**: frame rate unlocked (30, 60, 75, 90, 120, 144 or any value 30–240; tested up to 120), with the community "60 FPS with deltatime" patch so the game runs at the right speed
- **FSR 4 / FSR 3.1** as native anti-aliasing for a clean image (FSR edition)
- **FPS counter** and an in-game settings menu (Insert or L3+R3)
- **Save profiles**: separate careers for different players, switch any time
- **Save backups**: dated backups per profile with one-click restore (the current save is backed up first)
- **All DLC**: tours, cars and DRIVECLUB BIKES from your own DLC dumps
- **Launcher**: light and dark theme, keyboard and controller rebinding, desktop shortcut and Add to Steam (start the launcher or the game directly, great for Big Picture)
- **Native**: the game's own code runs directly on your CPU; no emulator, no console window

## Download

[**Latest Windows release**](https://github.com/qnfn/Driveclub-Port/releases/latest)

- `DCport-<version>-windows-fsr.zip`: FSR 3.1 and FSR 4 (FSR 4 needs a recent AMD or NVIDIA GPU)
- `DCport-<version>-windows.zip`: no upscaler

## Playing

1. Unzip anywhere and start `DriveClub.exe`.
2. Choose your own decrypted dump of DRIVECLUB 1.28 (the folder with `eboot.bin`). The first PLAY prepares the game files on your PC (once, under a minute).
3. Launcher tabs: **RACE** (play, quick settings), **SETUP** (frame rate 30–240, tested up to 120; window; FPS counter; upscaler), **CONTROLS**, **GARAGE** (save profiles, backups, shader cache, desktop shortcut, Add to Steam), **LOG**.
4. DLC: put your own dumped DLC folders (each with its own `sce_sys`) inside your game folder.
5. In game, Insert (or L3+R3) opens the settings menu.

Requirements: Windows 10/11 64-bit, a CPU with AVX, a Vulkan 1.3 GPU. More details and the source layout: [`windows/README.md`](windows/README.md).

## How it was made

The Windows port was directed and tested by [qnfn](https://github.com/qnfn); most of its code (runtime changes, launcher, tools) was written with **Claude** (Anthropic's AI, in Claude Code).

## Credits

DCport (the Windows backend) is a modified version of other people's work; almost all of it is theirs.

- **Native PS4 runtime:** deadinside28 ([bloodborne_pc](https://github.com/deadinside28/bloodborne_pc)) and the Windows port by Supermedo ([bloodborne_pc](https://github.com/Supermedo/bloodborne_pc)).
- **[shadPS4](https://github.com/shadps4-emu/shadPS4):** renderer, shader recompiler and libraries the runtime is built on.
- **[BlackLineInteractive](https://github.com/BlackLineInteractive/Driveclub-Port):** Driveclub Native for macOS; reference for Driveclub's system library behaviour (fonts and others).
- **[akitaonrails](https://github.com/akitaonrails/shadPS4):** shadPS4 investigation of Driveclub (MSAA depth resolve).
- **Also used:** [FSR-Vulkan](https://github.com/FireBurn/FSR-Vulkan) and the AMD FidelityFX SDK (FSR), FSR 4 assets from [FireBurn/Q2RTX](https://github.com/FireBurn/Q2RTX); FreeType, SDL3, FFmpeg and the other libraries listed in `licenses/`.
- **Community patches** ([shadps4-emu/ps4_cheats](https://github.com/shadps4-emu/ps4_cheats)): illusion, u/Charlie_Muggins, kalaposfos.
- Windows port by **qnfn**; the Driveclub-specific changes (system functions, fonts, readbacks, upscaler integration, launcher) were written with the help of Claude (Anthropic).

- macOS backend and the original Driveclub Native project: [BlackLineInteractive](https://github.com/BlackLineInteractive/Driveclub-Port).
- [OpenGNM](https://ps4-opengnm.github.io/opengnm/): documentation on PS4 Gnm and GCN shaders.

## Legal disclaimer

- **No Proprietary Game Files:** This project does not distribute, host, or link to any copyrighted material, proprietary game assets, PKG dumps, ROMs, executables (eboot.bin), libraries (.prx), engine archives (.dat), audio, or textures. Users must provide their own legitimately acquired copy of Driveclub (CUSA00003) and of any DLC. On Windows, DCport reads it from your folder and builds its working files on your own PC; nothing from the game is ever uploaded or shared. Please do not ask for, or share, game files anywhere in this project.
- **Intellectual Property:** Driveclub is a registered trademark of Sony Interactive Entertainment LLC. All trademarks, service marks, game titles, and copyrighted assets belong to Sony Interactive Entertainment and Evolution Studios. PlayStation and PS4 are trademarks of Sony Interactive Entertainment Inc.
- **Educational and Preservation Purpose:** This repository is an independent reverse-engineering project conducted strictly for interoperability, software preservation, and educational purposes. It is not affiliated with, endorsed by, or sponsored by Sony Interactive Entertainment, Evolution Studios, or any associated entities.
- **Free:** DCport is free and always will be. If someone sold it to you, ask for your money back.
- **FSR (Windows):** AMD, FidelityFX and FSR are trademarks of Advanced Micro Devices, Inc.; DCport is not affiliated with AMD. The FSR edition's download includes FSR 4 assets from [FireBurn/Q2RTX](https://github.com/FireBurn/Q2RTX) under AMD's MIT license (`fsr4_shaders/LICENSE-FSR4-v07.txt`). They are not part of this repository.
- **No Warranty:** DCport is provided "as is", without warranty of any kind (see the GPL). Use it at your own risk and keep a backup of your saves.
- Rights holders with a concern can open an issue on this repository; we will respond promptly.

## License

GPL-2.0-or-later (see [LICENSE](LICENSE)). Third-party components keep their own licenses.

## Problems and bug reports

Report problems on Discord: message **qnfn** — please include the LOG tab's "Copy for bug report".
