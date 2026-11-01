# FreeBuds Client

[![CI](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml/badge.svg)](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[**English**](README.md) | [**Português (Brasil)**](README.pt-BR.md)

An **unofficial** Windows desktop client to manage HUAWEI FreeBuds earbuds, inspired by the ergonomics of Galaxy Buds Client. Its goal is to provide battery levels, noise control, equalizer presets, gestures, multipoint status, and hardware tests without a Huawei account and without HUAWEI AI Life.

---

## ⚡ Quick Summary (TL;DR)

If you're just passing by and want the essentials:

- **What it is:** A lightweight Windows application (featuring a modern HarmonyOS-inspired GUI and a CLI) to check battery levels and configure HUAWEI FreeBuds directly from your PC.
- **What it does:**
  - Displays real-time battery percentages for both earbuds (L/R) and the charging case.
  - Switches noise control modes (ANC: Cancellation, Off, Awareness/Transparency) and Adaptive Recognition (11 levels).
  - Configures audio profiles (HUAWEI SOUND), spatial audio, wear detection, and touch/head movement gestures.
  - Minimizes seamlessly to the system tray.
  - Supports multiple languages (Portuguese and English with auto-detection and language selector in preferences).
- **What it DOES NOT do:** It does not replace the official mobile app (it cannot update firmware, provide advanced custom EQ, or find lost earbuds).
- **Quick start:** Download the ready-to-run executable (`.exe`) from the [Releases](https://github.com/hrbtnog/freebuds-client/releases) page or run from source with Python 3.10+ (`pip install -e ".[ui]"` and then `freebuds-ui`).
- **Personal project:** A non-profit project developed by an enthusiast with AI assistance. Feedback, issues, and PRs are warmly welcome!

---

## About Me and Why This Project Exists

I am **not a programmer** and have never worked in software development. This is a personal learning project: I wanted a way to check battery levels and control active noise cancellation on my FreeBuds Pro 5 from my PC without relying on my phone or HUAWEI AI Life.

It's worth highlighting that this application is not intended to fully replace a smartphone with Huawei AI Life or Huawei Audio Connect for comprehensive earbud management. Features such as custom parametric equalizers, charging case sound settings, "Find My Earbuds", ear tip fit tests, and other advanced configurations do not exist here yet (and some may never be implemented due to technical constraints).

The initial goal is simply to complement the user experience by offering quick, convenient access to primary controls directly within Windows, filling a gap Huawei does not provide natively on the desktop.

This is not a commercial product. It comes with no official support, roadmap, or warranty. The code was written with AI assistance and tested on the hardware I own. If you encounter bugs or glitches, feel free to report them so I can try to fix them. Suggestions, constructive feedback, issues, and pull requests are very welcome!

## Important Notice

- **Use at your own risk.** This software communicates with your earbuds over Bluetooth and can modify device settings. There is no guarantee it will work on other models, firmware versions, or hardware revisions.
- **Unofficial project.** Not affiliated with, sponsored by, or endorsed by Huawei, HONOR, or any manufacturer. Trademarks and images belong to their respective owners; see [`NOTICE.md`](NOTICE.md).
- **No firmware updates:** It does not flash firmware and does not attempt to bypass Windows pairing, PIN, passkey, or security confirmations.
- **Do not share personal data.** Avoid posting full Bluetooth MAC addresses, serial numbers, HCI packet dumps, or device names in issues, screenshots, and PRs.

## Project Status

> **Status:** Core phases implemented. The communication core, diagnostic CLI, and reverse engineering docs were validated on hardware on **2026-10-21** with a FreeBuds Pro 5 on channel `1`: enumeration, handshake, battery levels, and all three ANC modes responded as expected. Transparency level `4` was identified as **Adaptive Recognition** with 11 steps; ANC status changes arrive via `0x2B2A` push notifications. On **2026-10-23**, the PySide6 tray UI was validated while connected simultaneously to a PC and smartphone. ANC writes (`0x2B04`) and advanced settings (HUAWEI SOUND, spatial audio, adaptive volume, voice boost/conversation detection, head gestures, wear detection, sound quality priority, low latency, and single-bud ANC) were integrated with readback confirmations. On **2026-10-28**, the UI was redesigned following the HUAWEI Audio Connect design language with a HarmonyOS side rail, cards, segment controls, battery pills, and internationalization (EN/PT). The test suite includes **89 automated tests passing**. Multipoint connection and swipe gestures currently remain read-only for safety.

## Documentation

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — Frame structure, CRC16, TLVs, and known command IDs.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Architectural layers, threading model, CLI probe, and UI workers.
- [`docs/CAPTURE_GUIDE.md`](docs/CAPTURE_GUIDE.md) — Guide to capturing Android Bluetooth HCI traffic and correlating commands.
- [`CHECKPOINT.md`](CHECKPOINT.md) — Development state, hardware milestones, and technical notes.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — How to test, suggest features, and submit pull requests.
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — Community guidelines.
- [`SECURITY.md`](SECURITY.md) — Privacy policies and responsible disclosure.
- [`NOTICE.md`](NOTICE.md) — Third-party trademarks, visual assets, and licenses.
- [`LICENSE`](LICENSE) — Project MIT license.
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — Publishing checklist for releases and forks.

## Interface Design

The UI adapts the design language from modern mobile interfaces into a comfortable desktop layout:

- Fixed side rail navigation with branding and device switching;
- Centered max-width content column so cards don't stretch excessively on ultrawide monitors;
- Rounded cards (24px radius), hero card (28px), and subtle 1px dividers;
- Clear typography hierarchy with low-contrast uppercase section titles;
- Segmented controls with icons for ANC modes, level chips, and status switches;
- HUAWEI Blue `#0A59F7` reserved for active states, links, and primary actions;
- High-definition SVG icons within colored circular avatars for features and shortcuts;
- Battery pills with rings, earbuds/case icons, and centered percentages;
- Separate tabs for **Overview**, **Audio**, **Gestures**, **Connection**, and **Diagnostics** (keeping logs and preferences neatly organized).

![FreeBuds Client Overview](docs/ui/visao-geral.png)

Other screens: [Audio](docs/ui/audio.png), [Gestos](docs/ui/gestos.png), [Connection](docs/ui/conexao.png), [Diagnostics](docs/ui/diagnostico.png), [Adaptive Mode](docs/ui/adaptavel.png), and [Disconnected state](docs/ui/desconectado.png).

## Features

- Bluetooth Classic discovery and enumeration using native Windows APIs.
- Assisted Windows pairing (`BluetoothAuthenticateDeviceEx`) without bypassing security prompts.
- RFCOMM/SPP transport with fallback to known channels (`1` and `16`) and persistent channel caching.
- Robust Huawei protocol codec: `0x5A` frames, TLVs, CRC16/XMODEM, and stream parser handling fragmentation and noise.
- Device identification handshake (`0x0107`), battery polling (`0x0108`), and ANC state reading (`0x2B2A`).
- Complete ANC control via `0x2B04`: Off, Cancellation (Standard, Comfort, Ultra, Dynamic), Transparency, and Adaptive Recognition slider (1 to 11).
- High-level client API (`core/client.py`) with background workers, auto-reconnection, and snapshot notifications.
- Powerful CLI with human-readable and `--json` outputs, raw hex inspection (`--raw`), and live listener (`--listen`).
- Modern desktop GUI in PySide6 with system tray integration, battery monitoring, and custom theme.
- Advanced Audio controls: HUAWEI SOUND presets, spatial audio, adaptive volume, and voice enhancement.
- Gesture customization: Pinch/press and hold, double tap, triple tap, head movement control (nod/shake), and swipe status.
- Connection management: Codec quality priority, low-latency gaming mode, intelligent wear detection, and multipoint overview.
- Full internationalization support (Portuguese and English).
- Persistent user settings stored in `%APPDATA%\FreeBudsClient\settings.json`.

### Hardware Validation

Real runs on channel `1` with FreeBuds Pro 5 reporting internal model `BTFT0023` and firmware HarmonyOS 7.0.0.350 (F003H003C91):

| Item | Result |
|---|---|
| SPP listing & connection | OK — device already paired, connected on channel `1` |
| Handshake `0x0107` | OK — 14 fields returned |
| Battery `0x0108` | OK — global, L/R, charging case, and flags |
| ANC `0x2B2A` | OK in normal mode (`00 00`) |
| ANC Cancellation | OK — `03 01` = dynamic/cancellation |
| ANC Transparency | OK — `04 02` = Adaptive Recognition; position in parameter `2` |
| Adaptive Recognition | OK on 2026-10-23 — 11 levels (`0x00..0x0A`), selection, write, and restore confirmed |
| ANC Write `0x2B04` | OK on 2026-10-23 — modes `00 00`, `01 FF`, `02 02`, `02 04` and cancellation/adaptive levels; state confirmed |
| Advanced features (Audio/Gestures/Connection) | OK on 2026-10-23 — HUAWEI SOUND, spatial audio, adaptive, head gestures, wear detection, quality, latency, and gestures confirmed and restored |
| Spontaneous notifications | OK — ANC `0x2B2A` pushes wake up worker immediately; `0x2BAC` preserved |
| PySide6 UI with tabs + tray | OK on 2026-10-23 with earbuds connected to PC and phone: hero, tabs, switches, chips, combos, reconnection, and tray |
| HarmonyOS Redesign (rail, pages) | OK on 2026-10-28 in offscreen rendering at 1320×880 and 1100×760, in connected, disconnected, and adaptive states; to be repeated with hardware |
| Assisted pairing from scratch | Not yet re-executed (earbuds were already paired) |
| Battery `0x0127` and `0x2BAC` | `0x0127` pending; `0x2BAC` observed but semantics unconfirmed |

### Pending Hardware Validation

- High DPI and Windows sleep/resume cycles with the UI connected.
- Spontaneous notification of adaptive level when adjusted via mobile slider.
- Battery layouts, charging flags, and notifications on other FreeBuds models.

## Why Bluetooth Classic instead of BLE?

FreeBuds expose their proprietary control channel over **SPP/RFCOMM** (Service UUID `00001101-0000-1000-8000-00805F9B34FB`), using `0x5A` frames. While BLE is used by some accessories, it is not the primary control channel for these earbuds. The RFCOMM channel varies across models/firmware (e.g., Pro/Pro 2/Pro 3/Pro 5 and 6i use `1`; 4i and 5i use `16`). The CLI automatically tries known channels and accepts `--channel`.

## Requirements

- Windows 10/11 with Bluetooth.
- Earbuds paired to Windows, powered on, and out of the charging case.

## For Non-Programmers

An official `.exe` is available to download under [Releases](https://github.com/hrbtnog/freebuds-client/releases). You can also build an executable locally following [Build an executable (.exe)](#building-a-standalone-executable-exe). To run the project from source, install Python and follow the steps below.

## Local Installation

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ui]"
```

To use only the CLI without GUI packages:
```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\freebuds.exe list
```

## Building a Standalone Executable (.exe)

On Windows, with your virtual environment activated:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui]" pyinstaller
```

Create an entry launcher:

```powershell
@'
from freebuds.ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
'@ | Set-Content -Encoding utf8 .\freebuds_ui_launcher.py
```

Bundle into an executable:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name FreeBudsClient --paths .\src --collect-all freebuds .\freebuds_ui_launcher.py
```

The executable will be generated at `dist\FreeBudsClient.exe`.

## CLI Usage

```powershell
# Installed version
freebuds --version

# List devices paired/known by Windows
freebuds list
freebuds list --json

# Scan for non-paired devices (Bluetooth Classic inquiry)
freebuds scan --seconds 8

# Scan all Bluetooth devices, not just Huawei/HONOR
freebuds scan --seconds 8 --all

# Assisted pairing
freebuds pair AA:BB:CC:DD:EE:FF

# Handshake + Battery + ANC (tries channels 1 and 16 automatically)
freebuds probe --name "FreeBuds"

# Force specific channel, show raw TX/RX bytes, and format output as JSON
freebuds probe --address AA:BB:CC:DD:EE:FF --channel 1 --json --raw

# Listen to incoming notifications for 15 seconds after initial snapshot
freebuds probe --name FreeBuds --listen 15

# Decode raw hex byte string or text file
freebuds decode "5A0006002B03080100A79D"
freebuds decode --file capturas/spp.txt
```

## UI Usage

The GUI uses PySide6 (extra `ui`) and can be launched in three ways:

```powershell
# CLI command
freebuds ui

# Dedicated launcher
freebuds-ui

# As Python module
python -m freebuds ui
```

To directly target an address:

```powershell
freebuds ui --address AA:BB:CC:DD:EE:FF
```

## Tests & Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m compileall -q src tests
```

The test suite covers frames, parser, command decoders, mock RFCOMM sessions, high-level client flows, and offscreen GUI checks (**89 passing tests**).

GitHub Actions runs Ruff, compileall, and pytest on Windows across Python 3.11 and 3.12 for every push and pull request via [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Project Structure

```text
src/freebuds/
  core/
    protocol.py      # Frame, TLV, CRC, incremental parser
    commands.py      # Command IDs, requests, and semantic decoding
    client.py        # High-level client and snapshots for CLI/UI
    transport.py     # RFCOMM/SPP socket transport
    session.py       # Request/response correlation & reader thread
    windows_bt.py    # Windows Bluetooth Classic enumeration & inquiry
    models.py        # State dataclasses
  config/
    settings.py      # Persistent user settings
  cli/
    app.py           # CLI commands
  ui/
    app.py           # QApplication entry point
    main_window.py   # Main window, navigation rail, and page layouts
    worker.py        # Connection, polling, and background threads
    widgets.py       # Hero view, battery pills, ANC cards, controls, and logs
    tray.py          # System tray icon and context menu
    theme.py         # HarmonyOS dark stylesheet
    icons.py         # Branding, tray, and navigation icons
    svg_icons.py     # SVG rendering and tinting
    assets/          # Visual assets and icons/*.svg
docs/
  ARCHITECTURE.md
  PROTOCOL.md
  CAPTURE_GUIDE.md
  PUBLISHING.md
  ui/                # UI screenshots used in README
tests/
```

## Known Limitations

- Protocol and IDs were reverse-engineered from public research (OpenFreebuds, LibreBuds, mmk.pw, Gadgetbridge) and validated on FreeBuds Pro 5. Field availability varies across models/firmware.
- Battery reading via `0x0108` is primary; some firmware versions send `0x0127` push notifications instead.
- Component charging status (`param 3` of `0x0108`) is only displayed when payload format matches expected specifications.
- Fields `0x02`, `0x19`, `0x1B`, `0x1D`, `0x1E`, `0x21`, and `0x22` from `0x0107`, parameters `4`–`6` of battery response, and notification `0x2BAC` do not have confirmed semantics yet; they are stored as raw bytes.
- ANC modes, cancellation levels, and 11 Adaptive Recognition steps were tested in hardware. Adaptive position uses TLV `4` (`0x00..0x0A`) displayed in UI as `1..11` (raw `0x05` = default `6`).
- Pairing relies on Windows native UI/SSP; security prompts are not bypassed.
- RFCOMM channel is currently fixed per model; SDP lookup would be more resilient.
- UI writes ANC, audio, gesture, and connection settings confirmed on Pro 5.
- Default safety polling interval is 30 seconds, though changes arrive via immediate notifications. Reconnection retries every 12 seconds.
- Spatial audio, HUAWEI SOUND, adaptive volume, gestures, and connection priority were implemented on Pro 5; multipoint and swipe remain read-only.
- Firmware updating is not supported and will not be reverse-engineered.

## How to Contribute

This project welcomes suggestions, fixes, and pull requests!

- **Found an issue?** Open a bug report including earbud model, firmware revision, Windows version, and logs.
- **Have an idea?** Submit a feature suggestion; no programming knowledge is required.
- **Want to contribute code?** Check [`CONTRIBUTING.md`](CONTRIBUTING.md), run tests, and open a PR.
- **Do not share personal data** in issues, screenshots, or PRs.

## Security & Scope

- Use only with hardware you own.
- Never publish complete Bluetooth addresses or serial numbers without redacting.
- Always start with read-only commands. Any write command must be verified by packet captures and tested with a safe revert path.
- Review [`SECURITY.md`](SECURITY.md) before submitting logs.

## Next Steps

1. Validate High DPI, Windows sleep/resume cycles, and reconnects with the UI open.
2. Observe spontaneous adaptive level notification when moved by smartphone.
3. Observe battery notifications and test `--listen` on other firmware versions.
4. Expand hardware validation to other models/firmware and update `docs/PROTOCOL.md`.

## License

This project's original code is licensed under the **MIT License** — see [`LICENSE`](LICENSE). Product photos, third-party icons, and manufacturer trademarks belong to their respective owners; see [`NOTICE.md`](NOTICE.md).

## References & Acknowledgments

- OpenFreebuds — https://github.com/melianmiko/OpenFreebuds
- LibreBuds — https://github.com/librebuds/librebuds
- FreeBuds 4i Protocol — https://mmk.pw/en/posts/freebuds-4i-proto/
- Freebuds playground — https://gist.github.com/melianmiko/02f7c6a550808e38d9b6760fb688e125
- Gadgetbridge (FreeBuds) — https://codeberg.org/Freeyourgadget/Gadgetbridge
- GalaxyBudsClient — https://github.com/timschneeb/GalaxyBudsClient

Thank you to everyone who tested, reported issues, and shared protocol research!
