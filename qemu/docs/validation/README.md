# Validation records

[Documentation index](../../README.md)

These are dated observations, not guarantees about every later checkout or image.
Use [Maintenance](../MAINTENANCE.md#local-validation) to run current checks. Keep
new results tied to their input image, source revision, runtime and evidence.

| Record | Scope |
|---|---|
| [G350, 2026-10-20](G350-2026-10-20.md) | Previous v01302026 input; initial build, consoles, SDK and 351Files |
| [Audio, 2026-10-21](AUDIO-2026-10-21.md) | Previous input; stereo/mute, listening report and serial-mode limitations |
| [PortMaster, 2026-10-22](PORTMASTER-2026-10-22.md) | SDLPoP QEMU tests and separately identified handheld user report |
| [Triangle, 2026-10-23](TRIANGLE-2026-10-23.md) | Installed launchers, paths with spaces and return to ES |
| [v08272026 upgrade](UPGRADE-v08272026.md) | Input inspection, chosen source mapping and migration findings |
| [G350 v08272026, 2026-10-23](G350-v08272026-2026-10-23.md) | Development runtime, SDK/audio and independent standalone-package tests |
| [PICO-8, 2026-10-24](../evidence/pico8/README.md) | Original FAKE-08 core, cartridges, persistence and standalone checks |

Compact JSON, screenshots and original logs stay under [evidence](../evidence/).
Historical data is retained unchanged. Older image results do not establish
acceptance of v08272026. The PICO-8 record captures guest audio through QEMU WAV;
it explicitly reports a failed host audio preflight and unverified speaker output.
Do not merge that observation with earlier listening reports.
