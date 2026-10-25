# Build a G350 QEMU runtime

[Documentation index](../README.md)

This procedure adapts an official dArkOS release image; it does not build the
whole distribution from scratch. Commands run in Ubuntu, from the repository
root, unless explicitly marked PowerShell.

## Host requirements

The recorded development environment is Ubuntu 26.04 in Windows WSL2 with WSLg.
The host kernel needs NBD, Btrfs and ARM64 binfmt support. Allow roughly 50 GB
of free space for development and preferably 16 GB of host RAM; these are
practical allowances, not measured minimums. SDKs and exports require more space.
Internet access is needed for sources, Debian packages and free test fixtures.

Keep the checkout and `WORK_DIR` on the native Linux filesystem, such as `$HOME`,
rather than `/mnt/c`. Input archives may remain on the Windows drive. WSL/kernel
installation is outside the setup script's scope.

```bash
sudo apt-get update
sudo apt-get install -y git
mkdir -p "$HOME/projects"
cd "$HOME/projects"
git clone --branch codex/qemu-arm64-v08272026 https://github.com/ja-pa/dArkOS.git darkos-g350
cd darkos-g350
sudo bash qemu/scripts/setup-host.sh
sudo modprobe nbd max_part=16
sudo modprobe btrfs
cat /proc/sys/fs/binfmt_misc/qemu-aarch64
```

The binfmt entry must exist and be enabled. The setup script installs QEMU,
ARM64 cross-compilers, build/disk tools, Python and the controls-window dependencies;
it does not replace the WSL kernel. Resolve missing kernel modules or binfmt
registration before building. Graphical tests need a working WSLg session and
`DISPLAY`. See [troubleshooting](TROUBLESHOOTING.md).

Record `git rev-parse HEAD` when reproducing a particular revision; the branch
continues to evolve. On another machine use `git checkout --detach <commit>`
after cloning if an exact source revision is required.

## Inputs and environment

Download both volumes from the [official v08272026 release](https://github.com/christianhaitian/dArkOS/releases/tag/v08272026)
into one directory:

```text
dArkOS_G350_trixie_09022026.img.7z.001
dArkOS_G350_trixie_09022026.img.7z.002
```

Leave them compressed. The pipeline checks the pinned SHA-256 values, archive
integrity and extracted image hash. A supplied raw image is accepted through
`IMAGE=/path/to/original.img` only if its hash matches the selected lock.

Start with a fresh shell, outside any previously sourced SDK environment:

```bash
unset DISK_IMAGE KERNEL_IMAGE SSH_KEY SSH_PORT ES_SYSROOT QMP_SOCKET
unset BUILD_DIR KERNEL_SRC RELEASE_LOCK SOURCE_REPO IMAGE RAW_IMAGE
export WORK_DIR="$HOME/darkos-g350-qemu-v08272026"
export ARCHIVE_DIR="/mnt/c/Users/YOUR_WINDOWS_USER/Downloads/darkos-images"
export JOBS=4
```

Replace `ARCHIVE_DIR` with the actual archive directory. Use a fresh, dedicated
`WORK_DIR` for a new input release. Exported variables override defaults, so set
them again in each new terminal. Do not reuse RG353M or previous-image overlays.

## Import and build

```bash
make qemu-import
make qemu-inspect
make qemu-prepare
make qemu-graphics
make qemu-build COMPONENT=emulationstation
make qemu-build COMPONENT=retroarch
make qemu-build COMPONENT=351files
make qemu-image
make qemu-check
make qemu-test
```

| Stage | Result |
|---|---|
| Import | Verified, read-only official raw image |
| Inspect | Partition, filesystem, package and component inventory |
| Prepare | Separate build/runtime QCOW2 overlays; ARM64 chroot, DNS and APT checks |
| Graphics | Debian SDL2/Mesa/DRM libraries and build dependencies |
| Component builds | Pinned EmulationStation, RetroArch and keyboard-enabled 351Files |
| Image | Pinned QEMU kernel and integrated runtime, including example port preparation |
| Check | Local syntax, helper compilation and host regression checks |
| Test | Guest graphical integration and repeated cold-boot checks |

Preparation automatically adds 12 GiB of virtual capacity to the build overlay
and 4 GiB to the runtime overlay before the first APT check. It backs up and
relocates EASYROMS, expands Btrfs ROOTFS and preserves partition identities.
QCOW2 storage grows as data is written. No manual `grow.sh` call is needed.
The original raw image stays unchanged.

Frontend and 351Files compilation runs inside an ARM64 chroot through QEMU
user-mode; it does not boot the full VM. The QEMU kernel uses the host ARM64
cross-compiler. Its source is obtained automatically from the release lock.
Original emulator cores remain from the input image.

After host/input setup, `make qemu` runs conversion and integration validation.
SDK creation and exports are separate. Targets verify their prerequisite stages;
missing or invalid outputs may trigger prerequisite work. Completed valid stages
are reused using fingerprints and output hashes. After a failure, fix its cause
and repeat the corresponding target. Do not terminate the pipeline with SIGKILL.

## Outputs

Paths below are relative to `WORK_DIR`:

| Path | Content |
|---|---|
| `images/dArkOS_G350_trixie_09022026.img` | Immutable official image |
| `images/build.qcow2` | Dependency and ARM64 build environment |
| `images/work.qcow2` | Development runtime |
| `build/arch/arm64/boot/Image` | QEMU kernel |
| `sources/` | Pinned component source checkouts |
| `artifacts/` | Binaries, packages, manifests and attestation |
| `sdk/` | Optional application SDK |
| `logs/` | Build and validation logs |
| `state/` | Profiles and completed-stage receipts |

The checkout and work directory are separate. Host `build/` holds the kernel
build; frontend build trees are inside `build.qcow2`.

Input images and source revisions are pinned. A fresh build still resolves Debian
packages from available repositories and records their versions and hashes;
bit-for-bit identical images across machines are not guaranteed. Completed
package stages use their recorded cache. For a deliberate dependency refresh,
use a fresh `WORK_DIR` and review its manifests.

Continue with [usage](USAGE.md), [SDK development](SDK.md) or
[user release packaging](RELEASE.md). See [maintenance](MAINTENANCE.md) before
changing the input release or source pins.
