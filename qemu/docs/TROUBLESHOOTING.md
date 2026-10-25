# Troubleshooting

[Documentation index](../README.md)

Development commands run from the repository root; standalone commands run from
the extracted release folder. Check `WORK_DIR` before changing a development VM.

## Wrong runtime or inherited environment

An exported `WORK_DIR`, disk/kernel path, SSH setting or SDK sysroot from an older
session overrides defaults. Use a fresh shell or launch explicitly:

```bash
env -u DISK_IMAGE -u KERNEL_IMAGE -u SSH_KEY -u SSH_PORT -u ES_SYSROOT -u QMP_SOCKET WORK_DIR="$HOME/darkos-g350-qemu-v08272026" bash qemu/vm.sh es
```

A fresh work directory needs `make qemu-image` or a runtime import before startup.
Do not point a new release at old overlays or receipts. For SDK mismatches,
prepare or import the SDK matching that runtime; see [SDK](SDK.md).

## NBD, Btrfs or ARM64 chroot failure

```bash
sudo modprobe nbd max_part=16
sudo modprobe btrfs
cat /proc/sys/fs/binfmt_misc/qemu-aarch64
```

Missing modules require host kernel support; installing QEMU cannot supply an
absent WSL kernel module. An absent/disabled ARM64 binfmt entry needs working
`qemu-user-binfmt` registration. Run `sudo bash qemu/scripts/setup-host.sh` for
host packages. Resolve prerequisites before repeating the failed build step.

Keep build/work directories on the native Linux filesystem. Space checks cover
the Linux destination and Windows backing drive where applicable. Free space
or choose a new destination yourself; tools do not remove previous runtimes.

## Invisible WSLg windows

A taskbar entry containing `[WARN:COPY MODE]` with transparent or invisible windows
may indicate the WSLg shared-memory failure recorded in
[microsoft/wslg #1456](https://github.com/microsoft/wslg/issues/1456).
The launcher checks for the known log signature before boot.

First stop the VM (`bash qemu/vm.sh stop` for development, `bash stop.sh` for a
standalone package) and save other WSL GUI work. Restarting Weston closes those
applications. Run in Windows PowerShell, replacing `Ubuntu` if needed:

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
without sound devices, use `QEMU_AUDIO=none bash start.sh` or
`QEMU_AUDIO=none bash qemu/vm.sh es` from a stopped state.

An SDL application can use `SDL_AUDIODRIVER=dummy` inside the guest through
`/opt/darkos-qemu/env.sh`; setting it only on the host is not a guest override.
SDLPoP validation checks movement after a held arrow: menu operation or a quicksave
alone does not establish working gameplay input.

## Audio diagnostics

The route is SDL/RetroArch -> guest ALSA -> PCI HDA -> QEMU PulseAudio -> WSLg ->
Windows. A Linux desktop needs a PulseAudio-compatible session. The launcher uses
`PULSE_SERVER`, normally `unix:/mnt/wslg/PulseServer`, and does not start another
sound server. It checks HDA and `pa` availability. Stop before switching
`QEMU_AUDIO=auto`, `pa` or `none`.

For a running development guest:

```bash
bash qemu/vm.sh ssh 'cat /proc/asound/cards; aplay -l; amixer -c Intel sget Master'
bash qemu/vm.sh ssh 'speaker-test -D default -c 2 -t sine -l 1'
```

For an objective stereo test, install host FFmpeg and select an **output monitor**
listed by `ffmpeg -sources pulse`. With no other audio playing, use its actual name:

```bash
export DISK_IMAGE="$WORK_DIR/images/work.qcow2"
python3 qemu/scripts/validate-audio.py --monitor RDPSink.monitor
```

The validator checks VM identity, plays separate left/right markers and records
channel isolation under `$WORK_DIR/logs/audio/`. `--expect-muted` checks silence
while muted. It never chooses a microphone. Captures prove the software route;
listening is needed to assess physical channels, crackling and latency. TCG
scheduling/graphics load can produce ALSA underruns even when tone checks pass.

## Updating an older audio profile

Fresh images include the audio profile. For an older prepared G350 runtime,
back up its kernel, stop the VM, and build the selected lock's kernel with
`bash qemu/scripts/kernel.sh`. The config fragment requires built-in HDA controller
and generic codec support. With no frontend/game running:

```bash
bash qemu/vm.sh start gtk-gl
bash qemu/vm.sh audio
bash qemu/vm.sh es
```

Migration discovers the HDA card/mixer and waits for permissions. It sets initial
volume to 50%, enables ES menu sounds once, and preserves later choices. One-time
`.before-qemu-audio` backups and `/var/lib/darkos-qemu/audio-v1.json` record changes.
A dedicated service restores HDA mixer state; board `audiostate`/`audiopath` hooks
stay masked. Serial boots without HDA do not erase saved volume/mute.

Wrappers use ALSA and RetroArch `alsathread` with the shared default device;
explicit guest `SDL_AUDIODRIVER=dummy` is respected. The mixer uses 2048-frame
periods and an 8192-frame buffer at 44.1 kHz. No runtime library ABI changes, so
the SDK identity remains valid, but old exports retain their old kernel/profile.
Preserve previous attestations and run acceptance before exporting again. Do not
apply historical rollback paths to another work directory.

## SSH, shutdown and logs

Development SSH uses `127.0.0.1:2232` and the work directory's key. Check
`bash qemu/vm.sh status`, `bash qemu/vm.sh logs` and `$WORK_DIR/logs/workflow/`.
The runtime provisions an explicit VirtIO Ethernet DHCP profile; check networking
on repeated cold boots. Historical serial-only failures are in
[validation](validation/README.md). Standalone packages forward no SSH port.

Stop through the launcher before disk checks. A timed-out shutdown leaves the
guest running for diagnosis; closing QEMU is not a clean shutdown. Standalone
logs are `.runtime/logs/qemu.log` and `.runtime/logs/workflow/controls.log`.
Do not delete locks while the VM is running.
