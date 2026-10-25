# Run dArkOS QEMU

[Documentation index](../README.md)

## Downloaded standalone package

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

## Prepared development runtime

First complete [the build](BUILD.md) or import a [development bundle](SDK.md).
From the repository root:

```bash
export WORK_DIR="$HOME/darkos-g350-qemu-v08272026"
bash qemu/vm.sh es
bash qemu/vm.sh controls
bash qemu/vm.sh ssh 'uname -a'
bash qemu/vm.sh stop
```

`es` opens QEMU, the G350 keyboard diagram and EmulationStation. After exiting ES,
it can be invoked again while the guest is running. Development SSH is key-only,
bound to `127.0.0.1:2232`; the key is in `WORK_DIR`. The serial console logs in as
`ark`. Use an explicit `SSH_PORT` for a second VM and a separate work directory.
`bash qemu/vm.sh start serial` starts a serial-only development guest.

For a shell previously used with another port, clear inherited launch overrides:

```bash
env -u DISK_IMAGE -u KERNEL_IMAGE -u SSH_KEY -u SSH_PORT -u ES_SYSROOT -u QMP_SOCKET WORK_DIR="$HOME/darkos-g350-qemu-v08272026" bash qemu/vm.sh es
```

Development logs live under `$WORK_DIR/logs/`; `bash qemu/vm.sh logs` shows the
serial log and `bash qemu/vm.sh diagnose` records graphics diagnostics.

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

Stop the VM before changing `QEMU_AUDIO`. The default `auto` uses HDA/PulseAudio
for graphical launches and disables sound in serial mode. `pa` explicitly enables
playback; `none` omits audio devices:

```bash
QEMU_AUDIO=none bash start.sh                 # standalone folder
QEMU_AUDIO=none bash qemu/vm.sh es            # development checkout
```

The route is guest ALSA -> PCI HDA -> QEMU PulseAudio -> WSLg -> Windows.
No microphone is exposed. For silent playback, preflight failures or SDLPoP
stuck in its opening pose, see [troubleshooting](TROUBLESHOOTING.md).

[Dated validation records](validation/README.md) distinguish software audio
capture, listening reports and untested hardware/performance behavior.
