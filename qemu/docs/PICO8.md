# PICO-8 hry v QEMU

Položka PICO-8 v EmulationStation spouští původní ARM64 jádro FAKE-08
přes QEMU RetroArch. Cartridge patří do `/roms/pico-8/carts/` a mohou mít
příponu `.p8`, `.png` nebo `.p8.png` (také velkými písmeny).
Obyčejný obrázek PNG není herní cartridge.

Ovládání: šipky, Z/X pro herní tlačítka, Escape pro návrat do EmulationStation.
F1 otevírá RetroArch, F2 ukládá stav a F4 jej načítá; podpora stavů závisí na jádru.
Umístění uložených dat a stavů zachovává původní nastavení dArkOS.
V ověřeném obrazu se pro PICO-8 ukládají vedle cartridgí do `/roms/pico-8/carts/`.

FAKE-08 nenabízí editor ani Splore a kompatibilita her není úplná.
Při sestavení se případné zástupce `zzzsplore.p8`, `zzzsplore.png` a
`zzzsplore.p8.png` zachovají s příponou `.qemu-disabled`, aby je menu nenabízelo.
Původní skripty pro fyzický handheld se při spuštění nepoužívají.

Prohlížeč obrázků se vypíná pouze pro tento systém prostřednictvím
`/opt/darkos-qemu/pico8.cfg`; společná konfigurace RetroArchu se nemění.
Stejná podpora je součástí exportovaného standalone release.

Export release zachovává cartridge i uložená data uvnitř `/roms/pico-8/`.
