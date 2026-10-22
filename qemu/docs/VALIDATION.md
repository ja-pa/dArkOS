# G350 local milestone validation — 2026-10-20

Host: Ubuntu WSL2 on Windows, x86-64 TCG with WSLg/VirGL.
Input: official G350 v01302026 split archive; both published SHA256 digests,
7zip integrity and the 8,301,576,192-byte raw image were verified. The raw image
remained unchanged after build, integration and cold-boot checks.

Completed checks:

- ARM64 chroot shell, DNS and APT, with private mount namespace cleanup.
- Native ARM64 ES 351v and RetroArch 1.22.2 builds; Linux 5.10.226 for QEMU virt.
- Original theme, keyboard-driven ES launch, original ARM64 core, save/load state
  and return to the same ES process for GB, GBC, NES, SNES, GBA and Mega Drive.
- Runtime maps and real GL framebuffer captures: private SDL/Mesa/DRM prefix,
  no Mali/RGA/libgo2 libraries loaded by the tested frontend/core processes.
- Two cold boots, SSH and VirtIO DRM; stopped QCOW2 and read-only Btrfs checks.
- Eight pipeline stages revalidated without rebuilding completed outputs.
- Failed read-only stage with orphan child: status preserved, child terminated,
  temporary mounts and NBD connection cleaned up.
- 34 regression unit tests, Bash syntax, ShellCheck error checks, Python compile
  and capture helper compilation with warnings treated as errors.
- Runtime export/import into a fresh directory: new SSH host identity, matching
  SDK, original ES theme rendered through KMSDRM, keyboard F4 exit.
- SDK export/import and runtime identity match; SDK cross-built SDL demo deployed
  and rendered through KMSDRM/VirGL for 30 seconds.

Machine-readable evidence lives outside Git in WORK_DIR/logs/test-results.json,
WORK_DIR/logs/roundtrip.json and WORK_DIR/artifacts/attestation.json. The latter
records the final source commit, immutable stage receipts and artifact hashes.
Source manifests distinguish historically inferred source revisions from proven
binary provenance. Checks are run locally with make qemu-check; graphical tests
require WSLg. GitHub Actions workflows have been removed by project policy.

Acceptance covers functional keyboard operation and state persistence, not
console timing or playable performance under TCG. Audio, physical gamepads,
ARM32 and additional standalone emulators remain subsequent milestones.
The original darkos_qemu checkout and its working disks were preserved.

Follow-up preparation check (2026-10-20): fresh build/runtime overlays were
expanded before the first chroot/APT check, then preparation was repeated.
Both runs passed ARM64 shell, DNS and APT; the EASYROMS backups were not
rewritten on repetition. Virtual disk sizes were 21,186,478,080 and
12,596,543,488 bytes. The immutable raw image SHA256 remained unchanged.
Evidence: WORK_DIR/logs/prepare-fresh-check.json and prepare-fresh-check.log.

351Files keyboard follow-up (2026-10-20): the pinned upstream source is rebuilt
with a QEMU-only 640x480 keyboard/OpenGL profile. The original hardware binaries
remain intact; Options selects /opt/darkos-qemu/351Files through its wrapper.
All nine local QMP checks passed: arrows, directory open/parent return, page
navigation, selection, context-menu cancellation and repeated Escape/F4 returns
to the same ES PID, including Escape from an open dialog. Runtime binary SHA256
was compared with the build artifact. All six console/state gates also passed.
The host restart probe now accepts TCP TIME_WAIT while still rejecting a live
listener; both conditions have regression coverage. Clean immediate restart,
SSH, DRM, ROM mounting, QCOW2 consistency and unchanged base SHA256 were checked.
Evidence: WORK_DIR/logs/351files-results.json and 351files-restart.json.
