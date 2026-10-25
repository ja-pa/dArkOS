# PortMaster and SDLPoP on G350 QEMU

## Install and play

In EmulationStation, choose **Ports -> PortMaster**. On first launch,
HarbourMaster installs the pinned SDLPoP pilot from the local autoinstall ZIP,
then loads the online catalogue. Accept the upstream notice; its first-run timer
is 15 seconds. Quit and restart ES after installing games to refresh the list.
The QEMU adapter does not restart a physical-board service.

| Application | Controls |
|---|---|
| PortMaster | Arrows; Z/Space confirm; X back; Escape exit |
| SDLPoP | Arrows move; Shift action/careful steps; Escape game menu; F6/F9 quicksave/load; Ctrl+Q return to ES |

SDLPoP saves live in `/home/ark/.SDLPoP`. Both control profiles appear in the host
keyboard help window. If the prince stays crouched while menus still work, see
the WSLg recovery instructions in the standalone README or
[troubleshooting](https://github.com/ja-pa/dArkOS/blob/codex/qemu-arm64-v08272026/qemu/docs/TROUBLESHOOTING.md#sdlpop-remains-crouched-or-audio-startup-fails).

The adapter uses private Mesa/SDL2 and bypasses board library rewrites, gptokeyb
and oga_events for the bundled examples. Installed `.sh` and `.SH` launchers inside
`/roms/ports` run with the QEMU graphics environment and their own directory as
the working directory. Filenames with spaces are supported. PortMaster and SDLPoP
keep their dedicated adapters. Other games still need compatible launchers and
libraries; catalogue access does not establish game compatibility.
[dArkOS Triangle](https://github.com/ja-pa/darkos-portmaster-template) is another
example launched through **Ports -> DarkOS Triangle** from its existing ZIP.

Automatic PortMaster self-update is suppressed while catalogue refresh stays
online. An explicit update changes the pinned runtime. Repackaging preserves
installed ports and saves.

## Prepare or upgrade a development runtime

These commands require the source checkout and prepared development work directory,
not the extracted standalone package. Run from the repository root:

```bash
export WORK_DIR="$HOME/darkos-g350-qemu-v08272026"
bash qemu/scripts/portmaster.sh prepare
```

Normal `make qemu-image` preparation includes this step and queues the pilot for
first launch. Downloads are pinned in `qemu/locks/portmaster.lock.json`:
PortMaster 2026.10.21-1534 (upstream alpha channel) and SDLPoP port 2025-07-16_2108.
When changing pins, use a fresh work directory and review the resulting manifest.

For an existing prepared image:

```bash
bash qemu/vm.sh stop
bash qemu/scripts/portmaster.sh upgrade
make qemu-image
make qemu-test
bash qemu/vm.sh es
```

Offline upgrade needs sudo for disk mounting and invalidates the old image receipt.
Refresh image provenance and validation before exporting a user release.

## One SDLPoP archive for QEMU and handhelds

Preparation produces:

- `$WORK_DIR/artifacts/portmaster/portable/sdlpop.zip`
- `$WORK_DIR/artifacts/portmaster/manifest.json` and `SHA256SUMS`

The archive retains upstream `prince.aarch64` byte-for-byte, game data, metadata
and the handheld launcher. The wrapper selects the QEMU path only when
`/etc/darkos-qemu-profile` exists; otherwise it invokes the upstream handheld path.
It is an example adaptation, not a guarantee for every game or handheld.

For a physical device:

1. Back up any existing SDLPoP installation and saves.
2. Copy the generated archive to PortMaster's `autoinstall/` directory, retaining
   its basename `sdlpop.zip`, then open PortMaster.
3. Launch SDLPoP from Ports; check display, gamepad actions, audio and exit.
4. Save/load, relaunch and reboot to check persistence.
5. Record device model, firmware/PortMaster versions, ZIP SHA-256 and results.

The 2026-10-22 user report covers gameplay, sound and controls on a handheld
described as R36xx with a related dArkOS base. Exact model, firmware and tested
ZIP hash were not supplied; save/load and return to ES were not established.
Physical G350 acceptance remains unperformed. See the
[dated PortMaster record](https://github.com/ja-pa/dArkOS/blob/codex/qemu-arm64-v08272026/qemu/docs/validation/PORTMASTER-2026-10-22.md)
and [validation index](https://github.com/ja-pa/dArkOS/blob/codex/qemu-arm64-v08272026/qemu/docs/validation/README.md)
for QEMU tests and their limits.

## Sources and licenses

- [SDLPoP source](https://github.com/NagyD/SDLPoP)
- [PortsMaster port packages](https://github.com/PortsMaster/PortMaster-New)
- [PortMaster GUI and licenses](https://github.com/PortsMaster/PortMaster-GUI)

Upstream metadata/references are retained. Installed PortMaster includes its
upstream `licenses/` directory. This guide is also copied into standalone releases;
repository links above provide development details and historical evidence.
