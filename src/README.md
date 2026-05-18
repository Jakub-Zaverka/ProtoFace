# ProtoFace

Technicka dokumentace projektu pro `Adafruit MatrixPortal S3` v `CircuitPython`.

Projekt zobrazuje animovany oblicej na RGB LED matici `64x32`, ovladaci menu na OLED `SSD1306`, reaguje na mikrofon, proximity senzor a akcelerometr a umi volitelne pripojit Wi-Fi, synchronizovat cas a vystavit jednoduche HTTP ovladani.

## Co projekt umi

- vykreslit oblicej z oddelenych casti `eye`, `nose`, `mouth`
- prehravat fullscreen emote a GIF animace na cele matici
- otevrit usta pri zvuku z mikrofonu
- spustit `boop` reakci podle proximity senzoru
- posouvat oblicej podle pohybu z akcelerometru
- zobrazit OLED menu pro emote, nastaveni a debug
- pres Wi-Fi synchronizovat cas a zobrazovat ho na OLED i RGB matici
- prijimat jednoduche HTTP prikazy `up`, `down`, `ok` jako dalkove ovladani menu

## Cilovy hardware

Aktualni projekt odpovida konfiguraci:

- deska: `Adafruit MatrixPortal S3`
- firmware: `Adafruit CircuitPython 10.1.4`
- hlavni vystup: HUB75 RGB matrix `64x32`
- OLED: `SSD1306 128x64` na `0x3C`
- proximity senzor: `APDS9960`
- akcelerometr: `LIS3DH` na `0x19`
- mikrofon: analogovy vstup `A3`
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

- `display.py`
  - wrapper nad HUB75 RGB matici
  - vytvareni regionu
  - nacitani BMP a GIF snimku do oblasti displeje

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

- `wifi_network.py`
  - pripojeni k hlavni nebo zalozni Wi-Fi
  - `mdns` hostname
  - `SocketPool`

- `clock.py`
  - synchronizace RTC pres NTP
  - format `HH:MM`

- `accelerometer.py`
  - kalibrace a cteni `LIS3DH`

- `mic.py`
  - kalibrace mikrofonu
  - jednoducha detekce odchylky od klidove hladiny

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

1. precte senzory a stavy tlacitek
2. prepocita pohyb obliceje podle akcelerometru
3. synchronizuje aktualni hodnoty do UI
4. obslouzi menu a pripadne toggly
5. aktualizuje emote controller
6. obslouzi HTTP server
7. refresne RGB matici
8. uspi smycku na `0.1 s`

## Rozlozeni RGB matice

`Display` v `display.py` deli matici `64x32` na ctyri regiony:

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

Normalni oblicej je slozeny z `eye`, `nose`, `mouth`. Kdyz je aktivni `whole`, tri caste regiony se skryji.

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

Stejne akce umi simulovat i HTTP API:

- `GET /up`
- `GET /down`
- `GET /ok`

### Polozky menu

Hlavni menu:

- `Emotes`
- `Settings`
- `Debug`

Menu emote:

- `Gif`
- `Clock`
- `Cross`
- `Open eye`
- `Sleep`
- `Dice`
- `Back`
- `test3`
- `test4`
- `test5`

Menu nastaveni:

- `Display`
- `Boop`
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

Prvni radek UI se automaticky zkracuje, aby se neprekryval s hodinami vpravo nahore.

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
  - pri `mic_value > 5` se pouziji mluvici usta

- proximity:
  - pri `proximity_value > 200` se aktivuje `boop` oko

- blikani:
  - po urcitem poctu cyklu se aktivuje `eye_blink.bmp`

### Emote z menu

Pri otevrenem detailu emote ma menu prioritu nad automatickymi reakcemi.

- `Clock`
  - fullscreen hodiny vykreslene vlastnim 5x7 fontem se skalovanim `2x`

- `Gif`
  - fullscreen GIF `giphy.gif`

- `Dice`
  - fullscreen GIF `dice.gif`

- `Cross`
  - kriz v regionu oka

- `Sleep`
  - spici oko

- `Open eye`
  - otevrene oko a mluvici usta

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
- `VERBOSE`

### Runtime perzistence

Toggle hodnoty z UI se ukladaji do `microcontroller.nvm`.

- pouziva se magic hlavicka `PFS1`
- stavy jsou ulozene jako bitove pole
- runtime nastaveni ma prioritu nad `settings.toml`

Pres UI lze za behu menit:

- `Display`
- `Boop`
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

## Ladeni

### Verbose rezim

Pri zapnutem `Verbose` se do konzole vypisuje:

- hodnoty akcelerometru
- mikrofon
- proximity
- zmeny nastaveni z UI

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
  - over mikrofon na `A3`
  - pripadne uprav prah `mic_value > 5`

- boop nereaguje
  - over `APDS9960`
  - pripadne uprav prah `proximity_value > 200`

## Poznamky k aktualnimu stavu

README odpovida aktualnimu kodu v repozitari, vcetne:

- HTTP serveru v `server.py`
- debug obrazovky v `UI.py`
- tritiho tlacitka na `A4`
- `BLINK_ON` a `DISPLAY_ON` runtime nastaveni

Testovaci polozky `test3`, `test4`, `test5` jsou v menu pritomne, ale zatim nemaji implementovanou logiku v emote controlleru.
