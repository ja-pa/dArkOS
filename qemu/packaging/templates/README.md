# dArkOS QEMU standalone release

A user package includes the kernel, writable disk, launchers and controls window.
It needs no source checkout, SDK, compiler or original image. On Windows, run it
inside Ubuntu WSL2 with WSLg; native Windows QEMU launchers are not provided.
A Linux desktop needs working GTK/OpenGL and PulseAudio or a compatible service.

```bash
sudo apt-get update
sudo apt-get install qemu-system-arm qemu-system-gui qemu-utils python3 python3-tk python3-pil python3-pil.imagetk libpulse0 libpulse-mainloop-glib0
```

Download all archive parts and `SHA256SUMS` into one directory. Follow the exact
archive name in the release's generated instructions; verify parts before
extracting, and verify the extracted folder before its first boot. Keep the
package in a writable Linux directory, for example `~/qemu-release`.

From the extracted folder:

```bash
sha256sum -c SHA256SUMS
bash start.sh
bash controls.sh
bash stop.sh
```

ES starts automatically; the first boot can take several minutes. Scripts also
work from another current directory. `bash start.sh --no-controls` hides the
keyboard helper. Closing the helper leaves the VM running. Missing Tkinter does
not prevent VM startup. The package forwards no SSH or other host network port.

Stop through `stop.sh` or the ES shutdown command. Closing the QEMU window may
terminate the emulator without clean guest shutdown. If `stop.sh` times out,
the VM remains available for diagnosis. F4 exits ES but leaves the guest running;
stop and start the standalone package to reopen ES.

Settings and saves are written into `darkos.qcow2`. Back up or move the package
only while stopped; do not share one disk between simultaneous VMs. Its published
checksum changes after boot. Restore the original package for a clean reset.
Logs are `.runtime/logs/qemu.log` and `.runtime/logs/workflow/controls.log`;
locks and process state are in `.runtime/state/`.

## Keyboard and games

Send keys to the QEMU window, not the controls window. The G350 photograph and
profile selector show mappings for ES, RetroArch, 351Files and example ports.

| Application | Keys |
|---|---|
| EmulationStation | Arrows; Enter confirm; Escape back; Space menu; Tab options; F4 exit |
| RetroArch games | Arrows; Z/X = A/B; S/A = X/Y; Q/W = L/R; Enter = Start; Right Shift = Select |
| RetroArch actions | F1 menu; F2 save state; F4 load state; Escape return to ES |
| 351Files | Arrows; Enter open; Backspace parent/cancel; X context menu; Insert select; Page Up/Down scroll; Escape/F4 exit |

351Files is under **Options -> 351Files**. The QEMU rebuild uses the G350
640x480 layout and Mesa/OpenGL; original hardware files remain under
`/opt/351Files`. Escape/F4 also exits nested dialogs. DinguxCommander is unchanged.

The menu exposes GB/GBC, NES, SNES, GBA, Mega Drive, PICO-8 and Ports. Original
ROM paths and themes are retained. Save/state behavior depends on the core and
original dArkOS settings. [PortMaster](PORTMASTER.md) covers installing SDLPoP
and other ports.

## SDLPoP example

Open **Ports -> PortMaster** once to install the prepared SDLPoP example. Accept
the first-run notice, quit and restart ES to refresh the game list, then select
**Ports -> SDLPoP**. See [PortMaster](PORTMASTER.md) for controls, additional
ports, the shared handheld ZIP, sources and compatibility limits.

## PICO-8

Put cartridges in `/roms/pico-8/carts/`. Supported extensions are `.p8`, `.png`
and `.p8.png`, including uppercase variants. An ordinary PNG image is not a game
cartridge. The original ARM64 FAKE-08 core runs through RetroArch: arrows move,
Z/X are game buttons, Escape returns to ES, F1 opens RetroArch and F2/F4 save/load
states where supported. In the inspected image, PICO-8 save data and states are
stored beside cartridges in that directory.

FAKE-08 has no editor or Splore, and game compatibility is incomplete. Build
preparation renames any `zzzsplore.p8`, `zzzsplore.png` or `zzzsplore.p8.png`
placeholder with `.qemu-disabled`. `/opt/darkos-qemu/pico8.cfg` disables the image
viewer only for this system. Hardware launch scripts are bypassed. Standalone
exports retain PICO-8 cartridges and saved data.

## Sound

The default `QEMU_AUDIO=auto` uses PCI HDA through the host PulseAudio service.
`QEMU_AUDIO=pa` explicitly enables playback; `none` omits sound devices. Stop the
VM before changing audio mode:

```bash
QEMU_AUDIO=none bash start.sh
```

The software route is guest ALSA -> HDA -> QEMU PulseAudio -> WSLg -> Windows.
No microphone is exposed. TCG scheduling can affect sound and game performance.

## Invisible WSLg windows

A taskbar entry containing `[WARN:COPY MODE]` with transparent or invisible windows
may indicate the WSLg shared-memory failure recorded in
[microsoft/wslg #1456](https://github.com/microsoft/wslg/issues/1456).
The launcher checks for the known log signature before boot.

First stop the VM with `bash stop.sh` and save other WSL GUI work. Restarting
Weston closes those applications. Run in Windows PowerShell, replacing `Ubuntu`
if needed:

```powershell
wsl.exe -d Ubuntu --system -- pkill -TERM -x weston
```

Weston restarts automatically. Then start the VM again.

## SDLPoP remains crouched or audio startup fails

If menus work but the prince stays crouched and arrows do not move him, playback
may be stalled. In the first level, SDLPoP waits for the introductory sound to
finish (`control_crouched` in [upstream source](https://github.com/NagyD/SDLPoP/blob/master/src/seg005.c)).
This was reproduced with the original PortMaster binary. Dummy audio allowed the
intro to finish; after WSLg recovery, movement worked with normal ALSA/HDA audio.

The audio preflight connects to PulseAudio, plays 100 ms of silence and waits
for drain with an eight-second limit. It uses no microphone and cannot repair a
VM whose host audio stalls later.

Stop the VM and save other WSL GUI work first. In Windows PowerShell:

```powershell
wsl.exe -d Ubuntu --system -- pkill -TERM -x weston
Start-Sleep -Seconds 5
wsl.exe -d Ubuntu --system -- pkill -KILL -x pulseaudio
```

Restart PulseAudio after Weston has recovered so it reconnects to the new socket.
Both services restart automatically. Start the VM afterward. For a temporary run
without sound devices, use `QEMU_AUDIO=none bash start.sh` from a stopped state.

An SDL application can use `SDL_AUDIODRIVER=dummy` inside the guest through
`/opt/darkos-qemu/env.sh`; setting it only on the host is not a guest override.
Check that the character moves after recovery; working menus alone do not prove
that gameplay input is working.

## Provenance and licenses

`config/image.json` identifies the guest profile, root partition and VM memory.
`provenance.json` records the official image, available input hashes, upstream
release, kernel, runtime build and packaging source identity. Unavailable values
are explicit. See `LICENSES.txt`, `G350-ROM-NOTICES.md` and `/usr/share/doc` inside
the guest for license notices and source references.

For build, SDK and maintainer workflows, see the
[QEMU documentation](https://github.com/ja-pa/dArkOS/blob/codex/qemu-arm64-v08272026/qemu/README.md).
