# QEMU audio

The playback path is SDL/RetroArch → guest ALSA → PCI HDA → QEMU PulseAudio →
WSLg → Windows. No microphone is exposed. QEMU, ES, RetroArch and SDL do not
need rebuilding; the Linux 5.10 kernel needs built-in HDA controller and generic
codec support. `build-kernel.sh` verifies the required built-in dependencies.

## Start and migrate

Run inside Ubuntu WSL as the normal user, from the G350 checkout. Keep a backup
of the old kernel and stop the VM before replacing it. Build with
`bash qemu/scripts/kernel.sh`; `qemu/config/kernel/qemu-arm64.fragment` is the source
configuration. Use the image-aware launcher:

```bash
cd "$HOME/projects/darkos-g350"
export WORK_DIR="$HOME/darkos-g350-qemu"
bash qemu/vm.sh start gtk-gl
bash qemu/vm.sh audio
bash qemu/vm.sh es
```

`QEMU_AUDIO=auto` (default) enables PulseAudio for `gtk-gl` and disables audio in
`serial`. `QEMU_AUDIO=pa` explicitly enables playback in either display mode;
`QEMU_AUDIO=none` omits the sound devices. Stop the VM before changing audio
mode. The launcher checks HDA device support, the `pa` backend and an actual
PulseAudio connection. It uses `PULSE_SERVER`, normally
`unix:/mnt/wslg/PulseServer`; it does not start another sound server.

Audio migration discovers the HDA ALSA card ID and mixer, configures shared
stereo playback, enables ES menu sounds on first migration, and sets initial
hardware volume to 50%. It preserves music/video settings and subsequent user
choices for menu sounds and volume. Existing files receive a one-time
`.before-qemu-audio` backup. Migration state lives in
`/var/lib/darkos-qemu/audio-v1.json`. `darkos-qemu-audio.service` restores a
separate HDA mixer state after ALSA restore, so a serial boot without sound
hardware does not erase the saved volume/mute. Board `audiostate` and G350 `audiopath` stay masked; the latter can mute
the virtual card during boot. Migration waits for udev sound-device permissions.

The migration upgrades existing G350, ES, Peanut-GB and SDK demo wrappers.
It also replaces the old G350 RetroArch QEMU profile's disabled/null audio with
`alsathread`, enabled playback and the shared `default` device on first migration.
The shared mixer uses a 2048-frame period and 8192-frame buffer at 44.1 kHz;
the former 1024/4096 configuration produced repeated ES underruns under TCG.
New wrappers default to `SDL_AUDIODRIVER=alsa`; an explicitly supplied
`SDL_AUDIODRIVER=dummy` is retained. For a diagnostic application run without
audio, pass that variable **inside the guest**, e.g. with `sudo -n env
SDL_AUDIODRIVER=dummy bash /opt/darkos-qemu/env.sh ...` on G350.

## Checks

```bash
python3 qemu/tests/test_launcher.py
python3 qemu/tests/test_audio_profile.py
bash qemu/vm.sh ssh 'cat /proc/asound/cards; aplay -l; amixer -c Intel sget Master'
bash qemu/vm.sh ssh 'speaker-test -D default -c 2 -t sine -l 1'
```

For an objective end-to-end stereo check, install/use host FFmpeg, select the
**output monitor** shown by `ffmpeg -sources pulse`, and run while no application
is playing audio:

```bash
export DISK_IMAGE="$WORK_DIR/images/work.qcow2"
python3 qemu/scripts/validate-audio.py --monitor RDPSink.monitor
```

The validator verifies the local VM identity, sends separate left/right tones
to guest `aplay`, captures the WSLg output monitor, and checks channel isolation.
It never selects a microphone. Evidence goes to `$WORK_DIR/logs/audio/`.
Monitor samples confirm the software route; a listening check must confirm
physical output, channel placement and absence of audible crackling.
The validator also accepts `--expect-muted` for checking mixer mute.

Test ES → game → ES repeatedly, verify menu volume/mute and inspect application
logs for ALSA xruns. TCG audio is sensitive to host scheduling and graphics load;
do not infer playability or latency from a successful tone test.

No runtime packages or libraries are changed by this migration, so the SDK ABI
and library runtime ID remain valid. Preserve audio-upgrade evidence separately
from previous image attestations. Export a new runtime only after acceptance;
old exported bundles retain their previous kernel and audio configuration.

QEMU audio options: [official invocation reference](https://www.qemu.org/docs/master/system/invocation.html).

## Local G350 validation, 2026-10-21

The upgraded kernel is `5.10.226-darkos-qemu`, Image SHA-256
`de28ea079c8cbcf327cfcd5b0f224a3fafe06ef5342e35fa59399931e682c0d6`.
The upgrade is installed in `$HOME/darkos-g350-qemu`; the prior disk and build
are retained as `images/work.before-qemu-audio.qcow2` and
`build.before-qemu-audio/`.

- All 34 shared-repository tests and 48 G350 tests pass.
- WSLg stereo monitor: left and right markers detected independently; mute
  produces silence, unmute restores both channels.
- ES theme menu sounds and RetroArch/Gambatte game audio were captured at the
  host output monitor. Game exit resumed the same ES process.
- Existing Peanut-GB binary played Tobu Tobu Girl with captured audio and exit 0.
- Serial boot without sound reached systemd `running`; qcow2 checks passed.
- A later serial reboot reached multi-user but SSH timed out. QMP powerdown
  was ignored; recovery used QMP quit, followed by a successful qcow2 check,
  GTK reboot and stereo test. Repeated serial-mode networking remains an open
  limitation; graphical starts and SSH on port 2232 were verified repeatedly.
- Four ES underrun messages remained during the post-tuning graphics test.
  The final normal ES menu session also logged repeated underruns while idle.
  The user confirmed clean audible output in Windows. Longer gameplay and
  latency were not measured.

The local audio runtime export is
`$HOME/darkos-g350-qemu/exports/runtime-g350-audio-20261021`. It includes the new
kernel, updated guest profile, audio attestation and stereo validation; the
library runtime ID and SDK remain unchanged.

Small evidence files are in [evidence/audio](evidence/audio/validation.json).
Detailed logs and captures remain under `$HOME/darkos-g350-qemu/logs/audio/`
and `$HOME/darkos-g350-audio-test/logs/audio/`. The installed upgrade attestation
is separate from the original image provenance.

To use the previous runtime while preserving its backup, stop the current VM
and create a new overlay (the command refuses an already-existing destination):

```bash
cd "$HOME/projects/darkos-g350"
export WORK_DIR="$HOME/darkos-g350-qemu"
bash qemu/vm.sh stop
test ! -e "$WORK_DIR/images/rollback-audio.qcow2" || exit 1
qemu-img create -f qcow2 -F qcow2 \
  -b "$WORK_DIR/images/work.before-qemu-audio.qcow2" \
  "$WORK_DIR/images/rollback-audio.qcow2"
DISK_IMAGE="$WORK_DIR/images/rollback-audio.qcow2" \
KERNEL_IMAGE="$WORK_DIR/build.before-qemu-audio/arch/arm64/boot/Image" \
QEMU_AUDIO=none bash qemu/vm.sh es
```
