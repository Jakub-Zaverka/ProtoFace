# ProtoFace

Technicka dokumentace projektu pro `Adafruit MatrixPortal S3` v `CircuitPython`.

Projekt zobrazuje animovany oblicej na HUB75 RGB LED matici `128x32` slozene ze dvou `64x32` panelu, ovladaci menu na OLED `SSD1306`, reaguje na mikrofon, proximity senzor a akcelerometr a umi volitelne pripojit Wi-Fi, synchronizovat cas a vystavit jednoduche HTTP ovladani.

## Co projekt umi

- vykreslit oblicej z oddelenych casti `eye`, `nose`, `mouth`
- prehravat fullscreen emote a GIF animace na cele matici
- otevrit usta pri zvuku z mikrofonu
- spustit `boop` reakci podle proximity senzoru
- posouvat oblicej podle pohybu z akcelerometru
- zobrazit OLED menu pro emote, nastaveni a debug
- pres Wi-Fi synchronizovat cas a zobrazovat ho na OLED i RGB matici
- prijimat jednoduche HTTP prikazy `up`, `down`, `ok`, `back` jako dalkove ovladani menu
- merit odezvu hlavni smycky, vytizeni runtime, pomale sekce a volnou pamet
- aplikovat globalni rainbow/wave barevny efekt s omezenou obnovovaci frekvenci
- prijimat ovladani menu z externiho ESP32 ovladace pres ESP-NOW
- menit jas RGB matice a PWM vykon ventilatoru pres OLED menu

## Cilovy hardware

Aktualni projekt odpovida konfiguraci:

- deska: `Adafruit MatrixPortal S3`
- firmware: `Adafruit CircuitPython 10.1.4`
- hlavni vystup: HUB75 RGB matrix `128x32` jako dva `64x32` panely
- OLED: `SSD1306 128x64` na `0x3C`
- proximity senzor: `APDS9960`
- akcelerometr: `LIS3DH` na `0x19`
- mikrofon: `MAX9814` pres `ADS1115` na I2C, vstup `A0`
- ventilator: PWM vystup `A1`
- tlacitka:
  - `BUTTON_UP`
  - `BUTTON_DOWN`
  - `A4` jako zpet / predchozi

## Pouzite knihovny

Projekt pouziva hlavne:

- `adafruit_ssd1306`
- `adafruit_apds9960`
- `adafruit_lis3dh`
- `adafruit_ntp`
- `adafruit_ads1x15`
- `adafruit_bus_device`
- `adafruit_imageload`
- `adafruit_httpserver`
- `adafruit_framebuf`
- `adafruit_gfx`
- `adafruit_logging`

Ze standardnich modulu CircuitPython se pouzivaji napr.:

- `board`
- `digitalio`
- `displayio`
- `framebufferio`
- `rgbmatrix`
- `gifio`
- `wifi`
- `socketpool`
- `mdns`
- `microcontroller`
- `rtc`

## Struktura repozitare

### Hlavni soubory

- `code.py`
  - hlavni runtime
  - nacteni ulozenych nastaveni z `microcontroller.nvm`
  - inicializace hardwaru, UI, emote controlleru a HTTP serveru
  - hlavni smycka se ctenim vstupu a refreshi displeju
  - instrumentace vykonu pres `PerformanceMonitor`

- `display.py`
  - wrapper nad HUB75 RGB matici `128x32`
  - vytvareni regionu pro levou i pravou fyzickou stranu
  - nacitani BMP a GIF snimku do oblasti displeje
  - cache nactenych BMP assetu v RGB565
  - rychla cesta `update_matrix_rgb565()` pro uz prevedene pixely
  - globalni rainbow efekt s throttlingem pres `RAINBOW_FRAME_SKIP`
  - globalni jas pres `BRIGHTNESS_STEPS`

- `emotes.py`
  - definice emote zdroju
  - sprava regionu `eye`, `nose`, `mouth`, `whole`
  - blikani, boop, reakce na mikrofon
  - fullscreen hodiny kreslene vlastnim 5x7 fontem

- `UI.py`
  - stavovy automat OLED menu
  - menu `Emotes`, `Settings`, `Debug`
  - synchronizace stavu toggle voleb
  - prijem lokalnich tlacitek i HTTP prikazu

- `server.py`
  - jednoduchy HTTP server nad `adafruit_httpserver`
  - endpointy `/up`, `/down`, `/ok`
  - JSON endpointy pro menu a performance metriky

- `performance.py`
  - lehky profiler hlavni smycky
  - meri prumernou a maximalni periodu smycky
  - meri prumernou a maximalni dobu aktivni prace
  - eviduje nejpomalejsi sekci a volnou/obsazenou pamet

- `wifi_network.py`
  - pripojeni k hlavni nebo zalozni Wi-Fi
  - `mdns` hostname
  - `SocketPool`

- `../controller/`
  - PlatformIO firmware pro externi ESP32 ovladac
  - posila `ControlMessage` pres ESP-NOW
  - ovlada OLED menu pres akce up, down, ok a back

- `clock.py`
  - synchronizace RTC pres NTP
  - format `HH:MM`

- `accelerometer.py`
  - kalibrace a cteni `LIS3DH`

- `mic.py`
  - cte `MAX9814` pres `ADS1115` na sdilene I2C sbernici
  - pouziva single-ended vstup `A0`
  - kalibruje klidovou uroven a vraci relativni odchylku pro animaci ust

- `I2C_sim.py`
  - sdilena I2C sbernice
  - wrapper pro `APDS9960`
  - wrapper pro textove vykreslovani na OLED

### Assety

Adresar `faces/` obsahuje obrazky a GIFy pouzivane jako emote:

- `eye.bmp`
- `eye_blink.bmp`
- `eye_open.bmp`
- `mouth.bmp`
- `mouth_speak.bmp`
- `nose.bmp`
- `sleep.bmp`
- `cross.bmp`
- `giphy.gif`
- `dice.gif`

## Architektura aplikace

`code.py` je centralni orchestrator. Pri startu:

1. nacte runtime nastaveni z `microcontroller.nvm`
2. doplni vychozi hodnoty z `settings.toml`
3. inicializuje zapnute moduly
4. vytvori OLED UI
5. vstoupi do `while True`

V kazde iteraci:

1. spusti mereni iterace pres `PerformanceMonitor`
2. precte senzory
3. precte tlacitka a vyrobi click udalosti
4. prepocita pohyb obliceje podle akcelerometru
5. synchronizuje menu, hodiny a pripadne debug radky do UI
6. obslouzi menu a pripadne toggly
7. aktualizuje emote controller
8. obslouzi HTTP server
9. refresne RGB matici
10. ulozi performance snapshot a pri `Verbose` ho vypise
11. uspi smycku na `0.01 s`

Jednotlive casti smycky jsou merene jako sekce:

- `sensors`
- `buttons`
- `motion`
- `ui`
- `emote`
- `server`
- `display`

## Rozlozeni RGB matice

`Display` v `display.py` pracuje s fyzickou matici `128x32`, kde jsou dve strany
po `64x32`. Kazda strana ma stejne ctyri regiony:

- `nose`
  - pozice `0,0`
  - velikost `32x16`

- `eye`
  - pozice `31,0`
  - velikost `32x16`

- `mouth`
  - pozice `0,16`
  - velikost `64x16`

- `whole`
  - pozice `0,0`
  - velikost `64x32`

Leva strana pouziva regiony `nose`, `eye`, `mouth`, `whole`. Prava strana
pouziva `nose_right`, `eye_right`, `mouth_right`, `whole_right` a je posunuta o
`RIGHT_PANEL_X_OFFSET = 64`.

Normalni oblicej je slozeny z `eye`, `nose`, `mouth`. Kdyz je aktivni `whole`,
tri caste regiony se skryji. `FaceEmoteController` aplikuje stejne pozadavky na
vsechny fyzicke sady regionu, takze oba panely ukazuji stejnou emote logiku.

Prvni fyzicka strana je v kodu zrcadlena pres `mirror_x=True` a
`mirror_position_x=True`, aby obraz sedel na zapojeni panelu.

### Vykonove optimalizace displeje

`Display` drzi pixely v RGB565, aby se barevne assety nemusely prevadet pri kazdem vykresleni. BMP assety nactene z cesty se po prvnim prevodu ulozi do `image_cache`; opakovane emote jako blink, speak, idle nebo boop pak pouziji uz pripravenou RGB565 matici.

Pro cached assety se pouziva `update_matrix_rgb565()`, ktera preskakuje opakovanou normalizaci barev a minimalizuje pocet Python volani v pixelove smycce. To snizilo spicky pri prepnuti emote z radove stovek ms na desitky ms v beznem pripade.

Rainbow/wave efekt se neprepocitava v kazdem refreshi. Konstantou `RAINBOW_FRAME_SKIP = 3` se efekt aktualizuje kazdy treti refresh, coz snizuje cukani pri soucasnem behu efektu a prepinani emote.

## OLED UI

UI je definovane v `UI.py` jako jednoduchy stavovy automat.

### Obrazovky

- `main_menu`
- `main_screen`
- `emotes_menu`
- `emote_detail`
- `settings_menu`
- `debug_menu`

### Ovladani

- `BUTTON_UP`
  - potvrzeni

- `BUTTON_DOWN`
  - dalsi polozka

- `A4`
  - predchozi polozka
  - navrat z detailni obrazovky

Externi ESP32 controller posila pres ESP-NOW stejne akce vcetne samostatneho
`back` tlacitka.

Stejne akce umi simulovat i HTTP API:

- `GET /up`
- `GET /down`
- `GET /ok`
- `GET /api/action/back`

### Polozky menu

Hlavni menu:

- `Emotes`
- `Settings`
- `Debug`

Menu emote:

- `Clock`
- `Cross`
- `Open eye`
- `Sleep`
- `Back`

Menu nastaveni:

- `Display`
- `Brightness`
- `Fan`
- `Boop`
- `Boop Rainbow`
- `Rainbow Override`
- `Mic`
- `Blink`
- `Accelerometer`
- `Wifi`
- `Verbose`
- `Back`

Debug screen zobrazuje aktualni radky s hodnotami:

- akcelerometr
- mikrofon
- APDS proximity
- prumerny a maximalni cas smycky
- prumerny cas prace a odhad vytizeni
- volnou pamet

Prvni radek UI se automaticky zkracuje, aby se neprekryval s hodinami vpravo nahore.

Debug hodnoty se na OLED aktualizuji jen pri otevrene Debug obrazovce a nejvyse jednou za `DEBUG_UI_UPDATE_INTERVAL = 1.0` s. Duvodem je rychlost SSD1306 pres I2C: caste `display.show()` volani blokovalo hlavni smycku a drive zpusobovalo spicky kolem stovek ms.

## Emote system

Za logiku obliceje odpovida `FaceEmoteController` v `emotes.py`.

### Regiony

Controller spravuje:

- `eye_region`
- `nose_region`
- `mouth_region`
- `whole_region`

Kazdy region si drzi:

- aktivni stav
- aktualni source
- delku trvani
- uplynuly cas
- GIF player, pokud je zdroj animovany

### Idle stav

Vychozi obrazky:

- oko: `/faces/eye.bmp`
- nos: `/faces/nose.bmp`
- usta: `/faces/mouth.bmp`

### Automaticke reakce

Pokud neni aktivni menu emote:

- mikrofon:
  - `MAX9814 OUT` je pripojeny na `ADS1115 A0`
  - pri `mic_value > 5` se pouziji mluvici usta

- proximity:
  - pri `proximity_value > BOOP_PROXIMITY_THRESHOLD` se aktivuje `boop` oko
  - aktualni hodnota konstanty je `60`

- blikani:
  - po urcitem poctu cyklu se aktivuje `eye_blink.bmp`
  - interval ridi `BLINK_TIME_SET` v `code.py` a `BLINKING_SLOWER` v `emotes.py`
  - aktualni `BLINK_TIME_SET = 100`, tedy blink je zpomaleny proti puvodnimu nastaveni

- rainbow/wave:
  - zapina se pri aktivnim `boop`, pokud je zapnute `Boop Rainbow`
  - lze ho vynutit globalne pres `Rainbow Override`
  - efekt se kvuli vykonu prepocitava jen kazdy treti refresh

### Emote z menu

Pri otevrenem detailu emote ma menu prioritu nad automatickymi reakcemi.

- `Clock`
  - fullscreen hodiny vykreslene vlastnim 5x7 fontem se skalovanim `2x`
  - bitmapa hodin se cachuje a prekresli se jen pri zmene textu casu

- `Cross`
  - kriz v regionu oka

- `Sleep`
  - spici oko

- `Open eye`
  - otevrene oko a mluvici usta

`FaceEmoteController` ma v kodu pripravenou i podporu pro `Gif`, `Dice` a
`Color`, ale aktualni `UI.py` je v menu nezobrazuje. Pro jejich zpristupneni je
potreba je pridat do `self.emotes_menu_items`.

## Konfigurace

### `settings.toml`

Projekt cte konfiguraci z `settings.toml`, typicky:

```toml
HOME_WIFI_SSID = "moje_wifi"
HOME_WIFI_PASSWORD = "heslo"

BACKUP_WIFI_SSID = "zalozni_wifi"
BACKUP_WIFI_PASSWORD = "zalozni_heslo"

DEVICE_HOSTNAME = "protogen"

ACCELEROMETER_ON = true
MIC_ON = true
APDS_ON = true
SSD1306_ON = true
WIFI_ON = true
BLINK_ON = true
DISPLAY_ON = true
BOOP_RAINBOW_ON = true
RAINBOW_OVERRIDE_ON = false
VERBOSE = false
```

Pouzivane klice:

- `HOME_WIFI_SSID`
- `HOME_WIFI_PASSWORD`
- `BACKUP_WIFI_SSID`
- `BACKUP_WIFI_PASSWORD`
- `DEVICE_HOSTNAME`
- `ACCELEROMETER_ON`
- `MIC_ON`
- `APDS_ON`
- `SSD1306_ON`
- `WIFI_ON`
- `BLINK_ON`
- `DISPLAY_ON`
- `BOOP_RAINBOW_ON`
- `RAINBOW_OVERRIDE_ON`
- `VERBOSE`

`BLINK_ON` a `DISPLAY_ON` nejsou v `settings.example.toml` uvedene, ale runtime
je podporuje a pri chybejici hodnote pouzije vychozi `true`.

### Runtime perzistence

Toggle hodnoty z UI se ukladaji do `microcontroller.nvm`.

- pouziva se magic hlavicka `PFS3`
- stavy jsou ulozene jako bitove pole
- runtime nastaveni ma prioritu nad `settings.toml`

Pres UI lze za behu menit:

- `Display`
- `Brightness`
- `Fan`
- `Boop`
- `Boop Rainbow`
- `Rainbow Override`
- `Mic`
- `Blink`
- `Accelerometer`
- `Wifi`
- `Verbose`

`SSD1306_ON` se cte jen pri startu, v UI se neprepina.

## Sit a HTTP ovladani

### Wi-Fi

`Wifi` v `wifi_network.py`:

- nacte hlavni a zalozni credentials
- nastavi `wifi.radio.hostname`
- zkusí hlavni sit, pri chybe zalozni
- vytvori `mdns.Server`
- vytvori `socketpool.SocketPool`

Po uspesnem pripojeni se HTTP sluzba inzeruje pres mDNS.

### HTTP server

`ServerClass` v `server.py` startuje server na portu `80` a vystavuje:

- `/`
  - testovaci textova odpoved

- `/up`
  - simuluje pohyb nahoru / predchozi polozku

- `/down`
  - simuluje pohyb dolu / dalsi polozku

- `/ok`
  - simuluje potvrzeni

- `/menu` a `/api/menu`
  - vraci aktualni snapshot OLED menu jako JSON

- `/api/action/up`, `/api/action/down`, `/api/action/ok`, `/api/action/back`
  - JSON varianty ovladacich akci

- `/api/perf`
  - vraci posledni performance snapshot jako JSON
  - obsahuje napr. `loop_avg_ms`, `loop_max_ms`, `work_avg_ms`, `work_max_ms`, `load_pct`, `mem_free`, `mem_alloc`, `slowest_section`, `slowest_section_ms`

Aktualni `api_call` pak zpracovava `UI.handle_input()`.

### Hodiny a NTP

`Clock` v `clock.py`:

- pouziva `adafruit_ntp.NTP`
- implicitne syncuje proti `tak.cesnet.cz`
- pouziva `tz_offset=2`
- pri chybe prejde na fallback zdroj, aby aplikace nespadla
- vraci cas jako `HH:MM`

## Pridani noveho emote

Typicky postup:

1. vloz asset do `faces/`
2. v `emotes.py` vytvor zdroj pres `create_image_emote(...)` nebo `create_gif_emote(...)`
3. pridej polozku do `self.emotes_menu_items` v `UI.py`
4. rozsiri `_apply_active_menu_emote()` ve `FaceEmoteController`
5. vyber region `eye`, `nose`, `mouth` nebo `whole`

Priklad:

```python
self.eye_happy_emote = create_image_emote("/faces/eye_happy.bmp", "happy")
```

A v `_apply_active_menu_emote()`:

```python
if active_menu_emote == "happy":
    requests["eye"]["source"] = self.eye_happy_emote
    requests["eye"]["duration"] = 1
    return True
```

## Nasazeni na zarizeni

1. nahrat `CircuitPython` na `MatrixPortal S3`
2. zkopirovat Python soubory do korene zarizeni
3. zkopirovat obsah `lib/`
4. zkopirovat adresar `faces/`
5. upravit `settings.toml`
6. restartovat zarizeni

Po restartu se automaticky spusti `code.py`.

Z korene repozitare lze pouzit helper:

```powershell
.\deploy_portal.ps1
```

Skript najde disk `CIRCUITPY`, zkopiruje obsah `src/` bez `settings.toml`,
vytvori `.reload` a otevire serial monitor na `COM4`.

## Ladeni

### Performance metriky

Runtime pouziva `PerformanceMonitor` z `performance.py`. Metriky maji hlavne ukazat, kde se hlavni smycka blokuje.

Priklad radku ve `Verbose` rezimu:

```text
Perf loops=97 loop_avg=51.8ms loop_max=94.0ms work_avg=21.5ms load=41% mem_free=1848448B slowest=emote:44.9ms
```

Vyklad hodnot:

- `loops`: pocet iteraci za posledni reportovaci okno
- `loop_avg_ms`: prumerna perioda cele smycky vcetne spanku
- `loop_max_ms`: nejhorsi namerena perioda smycky
- `work_avg_ms`: prumerna doba aktivni prace bez zaverecneho spanku
- `load_pct`: odhad vytizeni smycky jako `work_avg_ms / loop_avg_ms`
- `mem_free`: volna RAM podle `gc.mem_free()`
- `slowest`: nejpomalejsi namerena sekce a jeji cas

`load_pct` neni OS CPU vytizeni. CircuitPython tady bezi v jedne hlavni smycce, proto jde o prakticky odhad pomeru aktivni prace k cele periode.

Metriky jsou dostupne trema zpusoby:

- Debug obrazovka OLED
- serial konzole pri zapnutem `Verbose`
- HTTP `GET /api/perf`

### Vysledek optimalizaci

Puvodni mereni ukazovalo dlouhe blokace hlavni smycky:

- caste OLED prekreslovani posouvalo `slowest=ui` k hodnotam kolem `300 ms`
- opakovane nahravani a prevod emote bitmap posouvalo `slowest=emote` k hodnotam kolem `300-400 ms`
- rainbow/wave efekt prepocitaval aktivni pixely pri kazdem refreshi

Po upravach:

- Debug OLED se aktualizuje jen na Debug obrazovce a max. 1x/s
- BMP assety jsou cachovane po prvnim nacteni
- cached RGB565 pixely se kopiruji rychlejsi cestou bez dalsi konverze
- clock emote se regeneruje jen pri zmene casu
- rainbow/wave efekt se prepocitava kazdy treti refresh

Typicke namerene hodnoty po optimalizaci byly priblizne:

- `loop_avg` kolem `50-55 ms`
- `work_avg` kolem `20-28 ms`
- `load` kolem `40-50 %`
- bezne `slowest=emote` kolem desitek ms

Obcasne spicky kolem `150-250 ms` jsou stale mozne pri OLED flushi, GC, prepnuti emote nebo narocnejsim efektu. To je prakticka hranice kombinace CircuitPythonu, pixelovych Python smycek, SSD1306 pres I2C a HUB75 refreshu v jedne synchronni smycce.

### Verbose rezim

Pri zapnutem `Verbose` se do konzole vypisuje:

- hodnoty akcelerometru
- mikrofon
- proximity
- zmeny nastaveni z UI
- performance snapshot kazdych 5 sekund

Krome `print()` se logy ukladaji i do vnitrniho list bufferu.

### I2C diagnostika

`I2C_sim.py` obsahuje helpery pro scan I2C zarizeni a rychlou kontrolu, jestli jsou periferni moduly na sbernici videt.

### Typicke problemy

- OLED nic nezobrazuje
  - over adresu `0x3C`
  - over `SSD1306_ON`
  - over I2C zapojeni

- Wi-Fi se nepripoji
  - over hodnoty v `settings.toml`
  - zkontroluj dosah
  - projekt zkousi i zalozni sit

- HTTP ovladani nereaguje
  - over, ze je `Wifi` zapnute
  - otevri URL vytistene do serial konzole
  - over, ze server bezi na portu `80`

- hodiny ukazuji spatny cas
  - over funkcni Wi-Fi
  - uprav `tz_offset` v `clock.py`

- oblicej nereaguje na pohyb
  - over `LIS3DH`
  - over, ze je `Accelerometer` zapnuty

- usta nereaguji na zvuk
  - over `MAX9814 OUT -> ADS1115 A0`
  - over, ze je na desce knihovna `adafruit_ads1x15`
  - over, ze je `ADS1115` videt na I2C adrese `0x48`
  - pripadne uprav prah `mic_value > 5`

- boop nereaguje
  - over `APDS9960`
  - pripadne uprav `BOOP_PROXIMITY_THRESHOLD` v `emotes.py`

- animace seka pri rainbow/wave efektu
  - zvedni `RAINBOW_FRAME_SKIP` v `display.py`
  - vypni `Boop Rainbow` nebo `Rainbow Override`
  - over v `/api/perf`, jestli je nejpomalejsi `emote`, `display` nebo `ui`

- OLED zpomaluje smycku
  - debug hodnoty se maji aktualizovat jen na Debug obrazovce
  - pokud je `slowest=ui`, omez dalsi prekreslovani OLED nebo zvys `DEBUG_UI_UPDATE_INTERVAL`

## Poznamky k aktualnimu stavu

README odpovida aktualnimu kodu v repozitari, vcetne:

- HTTP serveru v `server.py`
- endpointu `/api/perf` a `/api/action/back`
- debug obrazovky v `UI.py`
- lokalnich tlacitek `BUTTON_UP`, `BUTTON_DOWN`, `A4`
- ctyrtlacitkoveho ESP-NOW controlleru s `button4` jako `back`
- menu nastaveni `Brightness` a `Fan`
- NVM hlavicky `PFS3`
- `BLINK_ON`, `DISPLAY_ON`, `BOOP_RAINBOW_ON` a `RAINBOW_OVERRIDE_ON` runtime nastaveni
- performance mereni v `performance.py`
- cache BMP assetu a rychle RGB565 cesty v `display.py`
- zpomaleneho blink intervalu pres `BLINK_TIME_SET = 100`
