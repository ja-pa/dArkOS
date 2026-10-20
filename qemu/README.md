# dArkOS G350 on ARM64 QEMU

Release-to-QEMU conversion in `ja-pa/darkos`, branch `codex/qemu-arm64`.
The branch starts at upstream `v01302026`, commit
`4518be7d0a665fb03619b840ce6015775d88765a`. Existing handheld builds are unchanged.

## Build

Run on the native Linux filesystem inside Ubuntu WSL2 with WSLg. Install host
prerequisites with `sudo bash qemu/scripts/setup-host.sh`. On Ubuntu 26.04,
`qemu-user` + `qemu-user-binfmt` provide the statically linked user emulator;
verify `/proc/sys/fs/binfmt_misc/qemu-aarch64` before building.

```bash
export WORK_DIR="$HOME/darkos-g350-qemu"
export ARCHIVE_DIR=/mnt/c/Users/japa1/Documents/ChatGPT/darkos_qemu/images
make qemu-inspect
make qemu-prepare
make qemu-graphics
make qemu-build COMPONENT=emulationstation
make qemu-build COMPONENT=retroarch
make qemu-image
make qemu-test
make qemu-sdk
```

`make qemu` performs conversion and validation. `IMAGE=/path/to/original.img`
accepts a raw image only when its hash is pinned in the selected `RELEASE_LOCK`.
Do not run this target against an existing RG353M work directory.

`build_emulationstation-qemu.sh` and `build_retroarch-qemu.sh` are small variations
of the corresponding upstream recipes. Sources and submodules are pinned;
EmulationStation uses historical `351v`, and RetroArch uses the version from the
historical `rk3326_core_builds` recipe. Exact correspondence to binaries in the
release is unverified. No upstream image/bootstrap script is executed.

The original archive hashes come from GitHub release asset metadata. The base
image stays read-only. Build and runtime use separate QCOW2 overlays, and the
runtime receives runtime libraries and rebuilt binaries rather than the build
rootfs. The G350 working overlays expand ROOTFS after backing up and relocating
EASYROMS; original partition identities and its contents are preserved.

Stages use an exclusive work lock, content fingerprints and verified output
hashes. A receipt is written only after a successful command. Mounts and NBD
attachments live in a private namespace with cleanup traps. Do not kill the
pipeline with SIGKILL. Interrupted imports are retained separately; a retry
cannot mistake a partial extraction for the base image. APT packages, exact
versions and hashes are cached under `artifacts/graphics`; changing repository
contents does not silently refresh a completed graphics stage. For a deliberate
dependency refresh, use a new WORK_DIR and review the new manifests.

## Run and develop

```bash
bash qemu/vm.sh es
bash qemu/vm.sh controls
bash qemu/vm.sh ssh 'uname -a'
bash qemu/vm.sh stop
bash qemu/sdk.sh prepare
bash qemu/app.sh build qemu/demos/sdk-app
```

SSH is key-only on `127.0.0.1:2232` by default, separate from the old port's 2222.
The serial console logs in as ark for development. Export `SSH_PORT` explicitly
when using a second VM. Graphics require WSLg; the tested path is VirtIO GPU,
Mesa and SDL2 KMSDRM. Audio uses the dummy/null drivers.

ES: arrows navigate, Enter confirms, Escape returns, Space opens the menu,
Tab opens options, F4 exits. RetroArch: arrows, Z/X = A/B, S/A = X/Y,
Q/W = L/R, Enter = Start, Right Shift = Select, F1 = menu, F2/F4 = save/load
state, Escape = exit to ES. Original themes and ROM paths are retained.
The QEMU menu initially exposes GB/GBC, NES, SNES, GBA and Mega Drive only.

The SDK is derived offline from the same build environment and tied to the
runtime fingerprint. Source `"$WORK_DIR/sdk/environment.sh"` for host GCC 12
cross builds; native chroot builds remain the default for the two frontends.

## Export and import

```bash
bash qemu/vm.sh stop
bash qemu/vm.sh export /path/to/new-runtime-bundle
bash qemu/sdk.sh export /path/to/new-sdk-bundle
# On a prepared host, with a fresh WORK_DIR:
bash qemu/setup.sh import /path/to/new-runtime-bundle
bash qemu/sdk.sh import /path/to/new-sdk-bundle
bash qemu/vm.sh es
```

Runtime exports are standalone QCOW2 copies with checksums, kernel, image
profile and provenance. Export copies are sanitized and receive a fresh SSH
identity at import. Original bundles and the working disk are preserved.
No image is publicly published by these commands.

## Validation and evidence

`make qemu-test` checks the base hash, boots QEMU, launches each original core
through ES using QMP keyboard events, exercises save/load and return to ES,
captures screenshots/runtime library maps, and performs a second cold boot.
VirGL scanout has no QMP CPU surface on the tested QEMU: the test runner enables
`capture.so` only during validation to read back the client EGL framebuffer.
Normal launches do not preload this diagnostic helper. Its source is `capture.c`.
It records `logs/test-results.json`; packaging alone is not milestone success.
Free fixture licenses and source links are in `test-roms-LICENSES.md`, with
exact hashes in `test-roms.json`. Tests do not claim console timing accuracy
or playable performance on an x86 TCG host.

`artifacts/delta.json` records the release lock, source commit, dirty-worktree
status, exact runtime packages, component hashes and added/removed/changed files.
The immutable source lock is `releases/g350-v01302026.json`. Historical audit
material under `reference/` describes RG353M and must not be treated as G350
validation. The original `darkos_qemu` checkout and disks remain the reference.

For the privileged interruption/failure check, run
`sudo env WORK_DIR="$WORK_DIR" bash qemu/tests/cleanup.sh` with the conversion
pipeline stopped. It deliberately fails a read-only stage with an orphan child,
then verifies the error status, child termination and mount cleanup.
`qemu/check-filesystem.sh` runs a read-only Btrfs consistency check on a stopped
working disk; it never repairs the original image.

Sound, physical gamepads, ARM32, other standalone alternatives, Kodi and
PortMaster-wide compatibility are deferred. When upgrading a release, add a new
input lock, inspect it afresh, review upstream changes and run the full gate.
Record why each QEMU patch exists; remove renderer/build compatibility changes
when the relevant upstream branch incorporates them.

After committing the verified source, `make qemu-attest` records the final Git
commit, stage fingerprints, SDK/component hashes and integration results in
`artifacts/attestation.json`. It refuses stale or incomplete validation and
does not rebuild or modify the guest. This avoids embedding a commit SHA in
the commit that defines it.
