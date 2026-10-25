# dArkOS G350 on ARM64 QEMU

Convert an official G350 release image into an ARM64 QEMU development runtime
or a standalone user package. The pipeline retains the original cores, themes
and ROM layout, replaces hardware integration, and rebuilds selected components
against a private SDL/Mesa graphics stack. Physical-device build recipes remain
unchanged.

## Guides

| Task | Guide |
|---|---|
| Run a downloaded package or prepared development VM | [Usage](docs/USAGE.md) |
| Build from the official image on a new computer | [Build](docs/BUILD.md) |
| Build applications and transfer development environments | [SDK and development bundles](docs/SDK.md) |
| Export, test and archive a user release | [Release](docs/RELEASE.md) |
| Install or adapt PortMaster games | [PortMaster](docs/PORTMASTER.md) |
| Diagnose host, graphics, audio or startup problems | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Understand the architecture, upgrade inputs and validate changes | [Maintenance](docs/MAINTENANCE.md) |
| Find dated test results and their limits | [Validation records](docs/validation/README.md) |

The default input is upstream `v08272026`, G350 image
`dArkOS_G350_trixie_09022026.img`, selected by
[`locks/g350-v08272026.json`](locks/g350-v08272026.json).
The default work directory is `$HOME/darkos-g350-qemu-v08272026`.
The documented development host is Ubuntu WSL2 with WSLg; QEMU uses ARM64 TCG
on the tested x86-64 host. Successful launches do not establish handheld timing
or playable performance. Hardware controllers and the full PortMaster catalogue
are not covered by the recorded acceptance tests.

## Source layout

- `scripts/`: pipeline stages and host helpers; `runtime/`: development guest scripts.
- `locks/`: input image identities, source revisions and checksums.
- `config/`, `assets/`, `patches/`: configuration, static assets and source patches.
- `packaging/`: exporter, archive builder, user templates and export-only guest setup.
- `ports/`, `demos/`: example launchers and SDK application sources.
- `tests/`: host regression tests, guest integration, diagnostic helpers and fixture licenses.
- `docs/`: maintained guides, dated validation records and saved evidence.

Run repository commands from the repository root. `qemu/vm.sh`, `qemu/sdk.sh`,
`qemu/app.sh` and `qemu/setup.sh` are public entry points. Root Make targets and
release scripts wrap them. Disks, caches, builds and logs belong in the external
`WORK_DIR`; generated user packages go to ignored `dist/qemu/` by default.
