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
make qemu-build COMPONENT=351files
make qemu-image
make qemu-test
make qemu-sdk
```

`make qemu` performs conversion and validation. `IMAGE=/path/to/original.img`
accepts a raw image only when its hash is pinned in the selected `RELEASE_LOCK`.
Do not run this target against an existing RG353M work directory.

`build_emulationstation-qemu.sh`, `build_retroarch-qemu.sh` and
`build_351files-qemu.sh` are small variations
of the corresponding upstream recipes. Sources and submodules are pinned;
EmulationStation uses historical `351v`, and RetroArch uses the version from the
historical `rk3326_core_builds` recipe. Exact correspondence to binaries in the
release is unverified. No upstream image/bootstrap script is executed.

The original archive hashes come from GitHub release asset metadata. The base
image stays read-only. Build and runtime use separate QCOW2 overlays, and the
runtime receives runtime libraries and rebuilt binaries rather than the build
rootfs.

`qemu-prepare` automatically provisions disk capacity before the first chroot/APT
check, dependency installation and component compilation. The official ROOTFS
has insufficient free space for this work. `grow.sh` adds 12 GiB to the build
overlay and 4 GiB to the runtime overlay, relocates EASYROMS with a verified
backup, and expands the Btrfs ROOTFS. Partition identities and EASYROMS contents
are preserved. These are increases in virtual capacity, not preallocation;
QCOW2 files consume host space as writes occur. Keep sufficient free space on
the WSL filesystem for the base image, both overlays, sources, caches and SDK.
No manual `grow.sh` invocation is needed in a fresh build: every Make target
from `qemu-prepare` onward runs the prerequisite preparation stage. Repeating
preparation does not move partitions again once the growth marker is present.
The call in `image.sh` is a defensive check for direct script invocation.

Stages use an exclusive work lock, content fingerprints and verified output
hashes. A receipt is written only after a successful command. Mounts and NBD
attachments live in a private namespace with cleanup traps. Do not kill the
pipeline with SIGKILL. Interrupted imports are retained separately; a retry
cannot mistake a partial extraction for the base image. APT packages, exact
versions and hashes are cached under `artifacts/graphics`; changing repository
contents does not silently refresh a completed graphics stage. For a deliberate
dependency refresh, use a new WORK_DIR and review the new manifests.

## Review a release upgrade

```bash
make qemu-components
RELEASE_LOCK=qemu/releases/new-release.json make qemu-components \
  PREVIOUS_LOCK=qemu/releases/g350-v01302026.json
```

This command only reads metadata and any matching original-image inventory; it
never imports an image, mounts a disk, compiles or starts a VM. The same table
is printed after inspection, before preparation/build, and saved to
`$WORK_DIR/logs/components.md`. It lists replaced versions, source URLs and full
commits, retained content, and changed/unchanged selections between two locks.
The report does not automatically approve an unchanged or older selection.

`replacements` in the release lock records original and target versions. Original
ES and RetroArch version strings were inspected statically in the read-only G350
image and are tied to its image and binary hashes. An image upgrade invalidates
that version evidence until reviewed; unknown versions stay explicit. Embedded
version strings do not prove the original source commit. 351Files and the original
hardware kernel currently have no established version. Debian library versions
are resolved separately by APT and recorded in the graphics package manifests.

All kernel builds, including direct `scripts/build-kernel.sh` invocation, read
`sources.kernel.repo` and `sources.kernel.commit` from `RELEASE_LOCK`. There is no
second SHA in shell code. `SOURCE_REPO` may supply a local mirror containing that
same commit; an existing checkout at another revision fails without resetting it.
Successful builds record the actual commit, transport repository and binary hash
in `artifacts/kernel-source.json`; image manifests verify these against the lock.

For a new release, copy the lock, review the image identity, source pins, target
version labels and original-version evidence, then use a fresh `WORK_DIR`.
Lock changes invalidate pipeline receipts; the next conversion rechecks stages
and may rebuild components. Existing runtime launch commands do not rebuild it.

## Run and develop

```bash
bash qemu/vm.sh es
bash qemu/vm.sh controls  # reopen the G350 keyboard diagram
bash qemu/vm.sh ssh 'uname -a'
bash qemu/vm.sh stop
bash qemu/sdk.sh prepare
bash qemu/app.sh build qemu/demos/sdk-app
```

If this shell was used for the original port, its exported `WORK_DIR` and
other path overrides still apply. Inspect the exported variables with `env`.
To select the prepared G350 runtime independently of those overrides:

```bash
env -u DISK_IMAGE -u KERNEL_IMAGE -u SSH_KEY -u SSH_PORT -u ES_SYSROOT -u QMP_SOCKET \
  WORK_DIR="$HOME/darkos-g350-qemu" bash qemu/vm.sh es
```

`vm.sh es` also opens the keyboard help window with the supplied G350 photo.
Switch between EmulationStation and RetroArch to see the actual per-profile
keys at the physical buttons; closing help leaves QEMU running. `vm.sh stop`
also closes help. It requires `python3-tk` and `python3-pil.imagetk`.
The photo is a user-supplied reference under `qemu/config/g350_picture.jpg`.

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
cross builds; native chroot builds remain the default for the frontends and 351Files.

### 351Files

Options -> 351Files uses a pinned rebuild with the G350 640x480 layout,
Mesa/OpenGL renderer and the upstream keyboard input branch. The original
hardware binary and resources remain under /opt/351Files; the QEMU binary is
/opt/darkos-qemu/351Files. The launcher selects it explicitly.

Keys: arrows navigate, Enter opens, Backspace goes back/cancels, X opens the
context menu, Insert selects, Page Up/Down scroll. Escape or F4 exits even from
a nested dialog, releases SDL and returns to the same ES process. The host
help window has a separate 351Files profile. DinguxCommander is unchanged.

`make qemu-test` also exercises Options launch, navigation, selection, context
menu and repeated Escape/F4 returns. Evidence is logs/351files-results.json.

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

This branch has no GitHub Actions workflow. All checks are explicitly local:

```bash
make qemu-check  # syntax, small host C helper, Python and regression checks
make qemu-test   # local ARM64 VM / graphical integration, using WSLg
```

`qemu-check` does not invoke APT, build the kernel/frontends or boot a guest.
Install host prerequisites first; Tk rendering tests run when DISPLAY is available.

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

## Audio

HDA playback through WSLg is configured by `qemu/vm.sh audio` and on ES startup.
Rebuild the kernel with the current fragment before upgrading an older image.
See [AUDIO.md](AUDIO.md) for migration, diagnostics and acceptance limits.
## Standalone release

Run `./make_qemu_release.sh` from the repository root to package a stopped,
prepared runtime. See [release creation and validation](RELEASE.md).
