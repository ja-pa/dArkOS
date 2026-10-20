# Přiblížení QEMU EmulationStation původnímu dArkOS

Průzkum ze dne 20. 10. 2026. Cílem je odhadnout práci nutnou k tomu, aby
EmulationStation a programy spouštěné z jeho nabídky v našem QEMU prostředí
odpovídaly původnímu dArkOS. Nejde o implementační plán schválený k provedení.
Při průzkumu se nic nekompilovalo a neměnila se konfigurace ani disky VM.

## Hlavní závěr

Pro první použitelnou sadu běžných retro systémů dává smysl začít **jedním novým
sestavením RetroArchu ARM64** a původní libretro jádra nejprve vyzkoušet.
Desítky systémů v ES sdílejí stejný frontend a neznamenají desítky samostatných
portů.

Pro širší zachování původních ARM64 variant bylo identifikováno **19 výstupních
souborů s přímou vazbou na Mali, RGA nebo libgo2**, případně 18 při vynechání
Retrorunu. Jde o kandidáty na překompilování nebo náhradu, nikoli o 19 samostatných
projektů ani o zaručený konečný počet buildů. Počet nezahrnuje již vyřešený ES,
ARM32 ani případné další problémy zjištěné při skutečném spuštění.

## Podklady a způsob ověření

- Aktuální [dArkOS](https://github.com/christianhaitian/dArkOS), commit
  `daecf488075f0194c164578b90617fa7002ce8bd`.
- [rk3566_core_builds](https://github.com/christianhaitian/rk3566_core_builds),
  commit `bbea3a603fce1bf24432e341b72dafeb88ea267d`.
- Náš původní obraz `dArkOS_RG353m_trixie_01312026.img` z vydání v01302026,
  připojený přes read-only loop a Btrfs `ro,rescue=nologreplay`.
- Konfigurace systémů ES, build skripty a přímé ELF závislosti přes `readelf`.
  U RetroArchu, Retrorunu a audio pluginu Mupen64Plus byly zkontrolovány také
  importované hardwarové symboly.
- Dosavadní výsledky projektu: [grafika](graphics.md),
  [EmulationStation](emulationstation.md), [Game Boy](gameboy.md).

Repozitáře jsou lokálně v `repos/dArkOS` a `repos/rk3566_core_builds`.
Pomocná evidence je v `repos/darkos-elf-audit.json`, `repos/darkos-audit.txt`
a `repos/darkos-image-es_systems.cfg`. Celé `repos/` je ignorováno Gitem;
tyto lokální podklady se s dokumentem automaticky nepřenášejí.

Aktuální upstream a náš lednový obraz nejsou totožné. Například aktuální seznam
ARM32 jader má 20 položek, ale v obrazu bylo nalezeno 19 ELF jader. Následující
počty binárek se vztahují k obrazu, nikoli k příslibu obsahu budoucího buildu.

## Inventura původního obrazu

| Položka | Počet |
| --- | ---: |
| Systémy v konfiguraci EmulationStation | 129 |
| Libretro jádra ARM64 | 130 |
| Libretro jádra ARM32 | 19 |
| Systémy s přímým spuštěním nebo nabízenou volbou ARM64 RetroArchu | 113 |
| ARM64 jádra s přímou závislostí na `libmali.so.1` | 7 |

Počet systémů je počet definic v konfiguraci. Neznamená, že jsou všechny viditelné
bez ROM, že jsou jejich alternativy kompletně nainstalované nebo že všechny
fungují. Nabídka RetroArchu u 113 systémů také neznamená, že je tam vždy výchozí.

## Základ: RetroArch bez Rockchip backendu

Původní ARM64 RetroArch přímo závisí na `libmali.so.1` a `librga.so.2`.
Importuje funkce `c_RkRgaBlit` a `c_RkRgaColorFill`, takže pouhé přesměrování
standardních EGL/GLES knihoven na Mesu tento problém neřeší.

Potřebujeme sestavení s běžným grafickým backendem použitelným nad naším
DRM/KMS a Mesa prostředím, bez Rockchip RGA a OdroidGo2 specifik.
Výchozí upstream recept zapíná `--enable-odroidgo2` a používá hardwarové patche:
[recept RetroArchu](https://github.com/christianhaitian/rk3566_core_builds/blob/bbea3a603fce1bf24432e341b72dafeb88ea267d/scripts/retroarch.sh).

Naše soukromé SDL2/Mesa prostředí již funguje. Dosavadní testy nevyžadovaly
kompilaci SDL2: distribuční SDL2 obsahuje KMSDRM. Nové sestavení SDL2 proto není
automatickou součástí tohoto odhadu.

U 123 ze 130 ARM64 jader nebyla nalezena přímá závislost na Mali. První postup
má být zkusit původní jádra s novým RetroArchem, zejména pro NES, SNES, GB/GBC,
GBA, Mega Drive, starší Atari, počítače a arkády.

**Absence přímé závislosti není důkaz funkčnosti.** Kontrola nepokrývá všechny
tranzitivní závislosti, dynamické načítání grafiky, podporované backendy,
ovládání ani chování za běhu. Některá jádra mohou potřebovat jiné starší
knihovny nebo další úpravy.

## Identifikované ARM64 komponenty k řešení

| Komponenta | Počet výstupů | Nalezená překážka |
| --- | ---: | --- |
| RetroArch ARM64 | 1 | Mali a skutečné použití RGA |
| Flycast a Flycast Rumble, libretro | 2 | Přímá závislost na Mali |
| Mupen64Plus Next, libretro | 1 | Mali |
| ParaLLEl N64, libretro | 1 | Mali |
| PPSSPP, libretro | 1 | Mali |
| VecX, libretro | 1 | Mali; týká se i Vectrexu |
| YabaSanshiro, libretro | 1 | Mali |
| PPSSPP standalone a varianta 2021 | 2 | Mali |
| DuckStation standalone | 1 | Mali |
| YabaSanshiro standalone | 1 | Mali |
| AppleWin standalone | 1 | Mali |
| Dolphin standalone | 1 | Mali, také přibalená vendor knihovna |
| Mupen64Plus standalone, pluginy | 4 | Tři video pluginy používají Mali, audio plugin libgo2 |
| Retrorun | 1 | Mali a skutečné použití RGA |
| **Celkem** | **19** | **18 při vynechání Retrorunu** |

Sedm dotčených ARM64 jader má názvy `flycast`, `flycast_rumble`,
`mupen64plus_next`, `parallel_n64`, `ppsspp`, `vecx` a `yabasanshiro`.
Starší jádro `mupen64plus` používá standardně pojmenované `libEGL.so`
a `libGLESv2.so`; není zahrnuto do sedmi přímých závislostí na Mali.

U standalone Mupen64Plus jsou problémem video pluginy GLideN64, Glide64mk2
a Rice a audio plugin SDL. Audio plugin přímo volá `go2_audio_create`,
`go2_audio_submit` a `go2_audio_destroy`. Samotný spouštěč a všechny další
pluginy tedy není nutné automaticky počítat jako další nové buildy.

Retrorun lze v první etapě vynechat a použít RetroArch nebo standalone emulátor.
Přesné zachování všech původních voleb emulátoru by naopak vyžadovalo řešit
i tuto alternativu. Počty v tabulce představují kandidáty pro čisté sestavení
bez vendor knihoven; nejsou tvrzením, že každý soubor nutně vyžaduje změnu
zdrojového kódu.

## Programy vhodné k prvnímu testu bez překompilování

Následující původní programy nemají v přímých ELF závislostech Mali, RGA ani
libgo2. Během průzkumu nebyly spouštěny.

| Skupina | Programy |
| --- | --- |
| Emulátory | Mednafen, ScummVM, Fake-08, XRoar, MVEM, piemu, TI99Sim, GameTank, OpenMSX |
| Herní enginy | GZDoom, LZDoom, ECWolf, Hypseus Singe, OpenBOR, Solarus |
| Nástroje | 351Files, DinguxCommander, image-viewer, gptokeyb, SDL testery ovladačů, webový filebrowser |

U těchto programů může stačit použití našich SDL/Mesa knihoven, doplnění
potřebných závislostí a úprava launcheru. Některé používají desktop OpenGL,
SDL rozšíření nebo další knihovny; je třeba ověřit i jejich načtení.

Další případy:

- **Standalone Flycast:** nemá přímou ELF závislost na Mali, ale grafické
  knihovny může načítat dynamicky. Vyžaduje kontrolu za běhu.
- **BigPEmu:** používá pluginy a přibalený gl4es `libGL`. První možností
  je zkusit přímé použití Mesy místo přibalené překladové knihovny.
- **Linapple:** používá SDL 1.2; je potřeba ověřit odpovídající kompatibilní
  vrstvu, nestačí automaticky jen naše SDL2.
- **DraStic, BigPEmu a uživatelem dodaný PICO-8:** je nutné pracovat
  s dostupnými binárkami a jejich požadavky. Vlastní překompilování nelze
  automaticky předpokládat.
- **Amiberry a DSperate:** upstream obsahuje build recepty, ale v auditovaném
  obrazu nebyly nalezeny adresáře `/opt/amiberry` a `/opt/DSperate`.
  Jejich případné přidání je rozšíření nad tento konkrétní obraz.
- **Porty a PortMaster:** rozsah závisí na jednotlivých dodaných hrách a jejich
  runtimech. Tento audit neurčuje kompatibilitu všech portů ani jejich počet.

## Integrace: práce mimo kompilaci

Pro věrnější prostředí nestačí, aby se vykreslilo okno emulátoru. Je potřeba
zachovat konfigurace, témata, volby emulátorů, práci se saves a návrat do ES.

Původní launchery často obsahují:

- `perfmax` a `perfnorm` s řízením frekvencí konkrétní desky;
- konkrétní cesty k handheldovým gamepadům v `/dev/input/by-path`;
- čtení device tree a identifikace modelu zařízení;
- nastavování gamepadů, `buttonmon`, hotkeys a restartování `ogage` nebo
  pomocných služeb pro ukončování programů;
- práci s framebufferem, konzolemi, rotací a rozlišením.

To bude především úprava shellových spouštěčů a konfigurací. Dosavadní projekt
již ověřil předání grafiky ES → Peanut-GB → ES, ale tím nejsou ověřeny původní
dArkOS launchery ani ostatní emulátory.

Bluetooth, baterie, jas, fyzické uspávání, přepínání HDMI, Wi-Fi hotspot a další
funkce handheldu nejsou nutné pro první přiblížení herní nabídky v QEMU.
Souborové a běžné síťové nástroje lze posuzovat samostatně.

## Co odložit

### ARM32

První etapa může používat ARM64 varianty. Zachování ARM32 alternativ znamená
řešit také RetroArch32, případně Retrorun32 a odpovídající ARMHF grafickou sadu.
Naše ověřené soukromé grafické prostředí je ARM64; nelze je přímo použít
pro ARM32 procesy.

Z 19 ARM32 jader mají tři přímou závislost na Mali: `flycast32_rumble`,
`parallel_n64` a `yabasanshiro`. Další mohou používat standardní GLES knihovny
nebo mít jiné překážky. Přesný rozsah ARM32 portu vyžaduje další audit a testy.

### Kodi a video

Adresář `/opt/kodi` v našem obrazu není. Aktuální upstream navíc nastavuje
`BUILD_KODI ?= n`, takže Kodi lze přirozeně vynechat:
[Makefile](https://github.com/christianhaitian/dArkOS/blob/daecf488075f0194c164578b90617fa7002ce8bd/Makefile).

Video položka ES používá samostatný `ffplay` launcher. Ten čte rozlišení
z framebufferu a na Rockchipu vybírá dekodéry `_rkmpp`. Aktuální upstream
obsahuje také vlastní FFmpeg build s Rockchip MPP/RGA. Případné video řešit
odděleně s běžným dekódováním a vhodnými distribučními knihovnami; nelze
z receptu aktuálního upstreamu dovozovat, že stejné knihovny obsahuje lednový
obraz. Zpočátku lze odložit jak Kodi, tak přehrávač videa.

## Doporučené úrovně rozsahu

| Cíl | Předběžný rozsah |
| --- | --- |
| Běžné retro systémy a původní nástroje | Jeden nový RetroArch; původní jádra a nástroje nejprve vyzkoušet, upravit launchery |
| Širší ARM64 libretro nabídka včetně dotčených N64, Dreamcast, PSP, Saturn a Vectrex jader | RetroArch + sedm jader, tedy osm identifikovaných výstupů |
| Zachování i původních standalone alternativ | Celkem 18–19 identifikovaných výstupů, plus případné problémy z runtime testů |
| Maximální shoda všech alternativ | Navíc ARM32, další volitelné aplikace a individuální porty; zatím bez spolehlivého celkového počtu |

Tyto počty nejsou časový odhad. Úprava hardwarového backendu může být podstatně
pracnější než běžné nové sestavení, zatímco některé programy mohou fungovat
po pouhé změně knihoven a launcheru.

## Výkon a zbývající nejistoty

ARM64 guest běží na x86-64 hostiteli přes QEMU TCG. Grafické testy zaznamenaly
VirGL s hostitelským LLVMpipe. Fungující spuštění například PPSSPP nebo Dolphinu
proto ještě neznamená hratelnou rychlost.

Před zahájením větší série buildů je nejhodnotnější ověřit jeden RetroArch
bez hardwarových vazeb, několik reprezentativních původních jader a jeden
původní SDL nástroj. U každého sledovat skutečně načtené knihovny, ovládání,
ukončení a návrat do ES. Zvuk a gamepady také vyžadují vlastní ověření;
dosavadní úspěšné herní testy používaly klávesnici a dummy audio.
