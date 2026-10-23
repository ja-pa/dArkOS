# G350 v08272026 QEMU validation — 23 October 2026

The new official image was imported into a separate native WSL work directory.
All original input hashes match `locks/g350-v08272026.json`; the raw base remains
read-only. The old branch, runtime and parent Windows working tree were preserved.

## Verified development runtime

- 80 local syntax/helper/Python regression tests pass.
- Cold graphical boots reach SSH on localhost:2232 with the explicit
  `QEMU VirtIO Ethernet` DHCP connection, DRM device and mounted EASYROMS.
- GB, GBC, NES, SNES, GBA and Mega Drive launch their original ARM64 cores through
  ES, save and load states, and return to the same ES process. Runtime library
  maps confirm the private SDL/Mesa stack and exclude Mali, RGA and libgo2.
- 351Files passes arrows, directory open/parent, paging, selection, context menu,
  and repeated Escape/F4 returns from main and nested dialogs to the same ES.
- PortMaster returns to the same ES. SDLPoP runs twice, saves/loads and returns;
  another cold boot repeats PortMaster and SDLPoP successfully.
- HDA playback at the WSLg output monitor detects independent left/right markers
  (11 windows each), silence while muted, and both channels again after unmute.
- The G350 keyboard diagram was opened and visually checked in WSLg.
- The new SDK validates against the runtime; a clean host cross-build of its
  SDL/OpenGL demo succeeds after fixing private graphics linker precedence.
- Guest shutdown through SSH is clean and `qemu-img check` reports no errors.

Compact machine-readable evidence and clean guest screenshots are in
[evidence/v08272026](evidence/v08272026/summary.json). Full logs, maps and frames
remain under `$HOME/darkos-g350-qemu-v08272026/logs/`.

## Problems found and handled

The first development boot started SSH but did not answer forwarded connections.
A diagnostic reboot worked. The runtime now provisions an explicit wired DHCP
profile, checked on subsequent cold boots; the initial failed attempt is retained
in the work logs. No kernel version upgrade was necessary.

The SDK demo initially linked the image's vendor GBM instead of private Mesa;
private library search precedence fixes the clean build. PortMaster's first UI
capture also needed to wait for offline pilot installation. Its pinned first-run
disclaimer has a 15-second timer, which the test now respects explicitly.

## Limits and standalone release

Audio samples verify the WSLg software route; physical loudspeaker audibility and
crackling were not assessed by listening. Console timing/playability, physical
controllers, hardware G350 and the full PortMaster catalogue are not established
by these tests. Historical evidence folders still refer to earlier images.

Standalone export provenance identifies its exact clean packaging commit. Its
separate copied-release acceptance results live in the new WORK_DIR logs and are
reported when the finished release is handed over; development tests alone do
not establish standalone acceptance.
