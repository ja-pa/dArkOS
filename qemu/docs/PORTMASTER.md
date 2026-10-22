# PortMaster and SDLPoP on G350 QEMU

Run from `~/projects/darkos-g350` in Ubuntu WSL2. Normal preparation is part
of `make qemu-image`; host downloads have exact SHA-256 pins in
`qemu/locks/portmaster.lock.json`. The pinned PortMaster release is 2026.10.21-1534
(upstream channel alpha); the SDLPoP port release is 2025-07-16_2108.

For an existing prepared runtime, stop the VM and run:

```bash
export WORK_DIR="$HOME/darkos-g350-qemu"
bash qemu/vm.sh stop
bash qemu/scripts/portmaster.sh upgrade
bash qemu/vm.sh es
```

The upgrade needs sudo for the offline disk mount and invalidates the old
image receipt. Run `make qemu-image` and `make qemu-test` to refresh the full
image provenance and validation before creating a standalone release.

Choose Ports -> PortMaster. On first launch the pinned pilot is installed by
HarbourMaster from the local autoinstall ZIP, then the normal online catalogue
loads. Accept the upstream first-run notice. After installing ports, quit and
restart ES to refresh its list (the adapter never restarts a board service).
PortMaster uses arrows, Z/Space to confirm, X to go back, Escape to exit.
SDLPoP uses arrows, Shift for action/careful steps, Escape for the game menu,
F6/F9 for quicksave/load, and Ctrl+Q to return to ES. Saves live in
`/home/ark/.SDLPoP`. Both profiles are in the host keyboard help window.

The QEMU adapter uses private Mesa/SDL2 and skips board-specific library
rewrites, gptokeyb and oga_events. The Ports adapter currently enables only PortMaster and SDLPoP. Other
catalogue ports can be installed, but their board launch scripts are blocked
until adapted; some rewrite physical-device graphics links.
Automatic PortMaster self-update is suppressed while catalogue refresh stays
online. An explicit update changes the pinned runtime; use a fresh work dir
when changing source pins. Repackaging preserves installed ports and saves.

## SDLPoP example: one archive for dArkOS handhelds and QEMU

`bash qemu/scripts/portmaster.sh prepare` creates:

- `$WORK_DIR/artifacts/portmaster/portable/sdlpop.zip`
- `$WORK_DIR/artifacts/portmaster/manifest.json` and `SHA256SUMS`

The archive keeps the original `prince.aarch64` byte-for-byte. Its launcher
selects the QEMU adapter only when `/etc/darkos-qemu-profile` exists; otherwise
it runs the untouched upstream handheld launcher. This is a pilot adaptation,
not a claim that every PortMaster game is portable or that QEMU measures G350
performance. The original port and data remain from PortsMaster, with upstream
metadata and references retained. SDLPoP source: https://github.com/NagyD/SDLPoP
PortMaster source and licences: https://github.com/PortsMaster/PortMaster-GUI
The installed PortMaster includes its upstream `licenses/` directory.

## Physical dArkOS: user-reported result

On 2026-10-22, the user reported that the same SDLPoP ZIP produced for QEMU
worked on a physical handheld running dArkOS from a similar base image to the
QEMU source image. Gameplay, sound and controls were tested successfully.
Save/load was not tested; return to the frontend was not explicitly reported.

The device was described as R36xx, without an exact model. The relevant result
for this example is portability of the same archive across related dArkOS base
images. This is a user report, not an independently observed hardware run, and
does not establish compatibility with all handhelds or other PortMaster games.
The exact firmware version and tested ZIP hash were not supplied.
See [hardware.json](evidence/portmaster/hardware.json).

SDLPoP is included as the first example port, alongside the separate console
validation suites. See [example preparation and installation](../ports/README.md).

## Physical G350 acceptance (not yet performed)

1. Back up an existing SDLPoP installation and saves before installing the pilot.
2. Copy `portable/sdlpop.zip` to the physical device's PortMaster `autoinstall/`
   folder. Keep its basename `sdlpop.zip`, then open PortMaster to install it.
3. Start SDLPoP from Ports. Check display, gamepad actions, sound and exit hotkey.
4. Save and load, relaunch, reboot, and confirm the save persists.
5. Record dArkOS version, PortMaster version, archive SHA-256 and results.

A successful QEMU run does not validate the physical device. The same ZIP is
ready for this manual test; physical G350 compatibility remains unverified.

## Local validation, 2026-10-22

`make qemu-image`, `make qemu-check` (65 tests), and `make qemu-test` passed.
All six original consoles and 351Files passed their existing checks.
PortMaster and SDLPoP resumed the same ES process, with two game runs and a
repeat after cold boot. Quicksave/quickload and the unchanged game binary were
verified. The online catalogue cache contained 1,461 ports; HarbourMaster
installed the original catalogue SDLPoP package successfully. This does not
claim compatibility for those other ports.

The WSLg output monitor detected separate stereo markers and SDLPoP audio.
ALSA underruns remain under TCG; physical listening and G350 hardware testing
were not performed. The kernel was rebuilt with the same configuration. Its
previous audio attestation is preserved under
`$WORK_DIR/artifacts/audio-upgrade-history/`; the current attestation records
new monitor checks without carrying forward the old physical-listening claim.

Compact evidence: [validation.json](evidence/portmaster/validation.json).
Detailed screenshots, maps and audio captures are in
`$WORK_DIR/logs/portmaster/` and `$WORK_DIR/logs/portmaster-cold/`.

Shared ZIP SHA-256:
`ad9da66a3a89f31aa08c377cd395127041581418766316fadcc6273ed2c3cd66`.
