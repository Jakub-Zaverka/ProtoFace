# ProtoFace

Podrobna technicka dokumentace k projektu pro `Adafruit MatrixPortal S3` v `CircuitPython`.

Projekt ridi animovany oblicej na RGB LED matici `64x32`, jednoduche menu na OLED displeji `SSD1306`, reakce na mikrofon, akcelerometr a proximity senzor `APDS9960`, a volitelne synchronizaci casu pres Wi-Fi.

## Co projekt dela

Zarizeni zobrazuje stylizovany oblicej rozdeleny do nekolika samostatnych oblasti:

- oko
- nos
- usta
- cela plocha matice pro fullscreen animace

Chovani obliceje se meni podle vstupu:

- mikrofon otevre usta pri hlasitejsim zvuku
- proximity senzor spusti reakci typu `boop`
- akcelerometr posouva oblicej podle pohybu zarizeni
- OLED menu umoznuje rucne vybirat emote a zapinat nebo vypinat funkce
- Wi-Fi umozni synchronizaci casu a zobrazeni hodin

## Cilovy hardware

Dokumentace vychazi z aktualni konfigurace projektu a `boot_out.txt`, kde je uvedeno:

- deska: `Adafruit MatrixPortal S3`
- firmware: `Adafruit CircuitPython 10.1.4`
- hlavni LED vystup: HUB75 RGB matrix `64x32`
- I2C zarizeni:
  - `SSD1306` OLED `128x64` na adrese `0x3C`
  - `APDS9960` proximity / color senzor
- dalsi vstupy:
  - mikrofon na analogovem pinu `A3`
  - akcelerometr `LIS3DH` pres I2C na adrese `0x19`
  - tlacitka `BUTTON_UP` a `BUTTON_DOWN`

## Pouzite knihovny

Projekt pouziva knihovny ulozene v `lib/`, zejmena:

- `adafruit_ssd1306`
- `adafruit_apds9960`
- `adafruit_lis3dh`
- `adafruit_ntp`
- `adafruit_imageload`
- `adafruit_framebuf`
- `adafruit_gfx`

Krome toho projekt pouziva standardni moduly CircuitPython, napriklad:

- `board`
- `digitalio`
- `displayio`
- `framebufferio`
- `rgbmatrix`
- `gifio`
- `wifi`
- `socketpool`
- `rtc`
- `microcontroller`

## Struktura repozitare

### Hlavni soubory

- `code.py`
  - hlavni entrypoint aplikace
  - inicializace hardwaru
  - hlavni smycka
  - obsluha tlacitek, senzoru, UI a animaci

- `display.py`
  - vrstva nad HUB75 RGB matici
  - vytvareni regionu obrazovky
  - nahravani BMP a GIF obsahu do jednotlivych casti displeje

- `emotes.py`
  - definice emote zdroju a runtime logiky
  - sprava regionu oka, nosu, ust a fullscreen vrstvy
  - blikani, boop, zobrazeni hodin, GIF animace

- `UI.py`
  - jednoduche menu pro OLED displej
  - prepinani obrazovek, vyber emote, prepinani nastaveni

- `I2C_sim.py`
  - sdileny I2C pristup
  - wrapper pro `APDS9960`
  - wrapper pro textovy vystup na `SSD1306`

- `wifi_network.py`
  - pripojeni k Wi-Fi
  - fallback na zalozni sit
  - mDNS hostname a priprava socket poolu

- `clock.py`
  - synchronizace RTC pres NTP
  - formatovani casu jako `HH:MM`

- `accelerometer.py`
  - kalibrace a cteni `LIS3DH`
  - vypocet odchylky od klidove polohy

- `mic.py`
  - kalibrace mikrofonu
  - jednoducha amplitudova detekce aktivity

### Assety

Adresar `faces/` obsahuje bitmapy a GIFy pouzivane jako emote:

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

### 1. `code.py` jako centralni orchestrator

Soubor `code.py` propojuje vsechny moduly a dela tri zakladni veci:

1. nacte konfiguraci
2. inicializuje dostupny hardware
3. v nekonecne smycce pravidelne cte vstupy a aktualizuje vystupy

### 2. Dva zobrazovaci vystupy

Projekt pouziva dva nezavisle displeje:

- HUB75 RGB matice
  - hlavni vyraz obliceje a fullscreen animace
- SSD1306 OLED
  - textove menu, stavove volby a hodiny

### 3. Udalostni model

Vstupy prichazi ze ctyr zdroju:

- tlacitka
- mikrofon
- proximity senzor
- akcelerometr

Tyto vstupy se v kazdem cyklu smycky prekladaji na:

- zmenu stavu menu
- zapnuti nebo vypnuti funkci
- jednorazovy nebo prubezny emote
- posun vykreslenych casti obliceje

## Jak se projekt spousti

Po startu zarizeni probehne priblizne tento sled:

1. nacteni ulozenych runtime nastaveni z `microcontroller.nvm`
2. doplneni chybejicich hodnot z `settings.toml`
3. inicializace zapnutych modulu:
   - akcelerometr
   - Wi-Fi
   - hodiny
   - mikrofon
   - APDS9960
   - OLED
   - RGB display stack
4. vytvoreni OLED UI
5. vstup do nekonecne smycky `while True`

V kazdem pruchodu hlavni smyckou se provede:

1. cteni senzoru
2. detekce kliknuti tlacitek
3. synchronizace stavu do OLED UI
4. obsluha UI udalosti
5. aktualizace emote logiky
6. refresh RGB displeje
7. kratke `sleep(0.1)`

## Rozlozeni RGB matice

Trida `Display` v `display.py` rozdeluje matici `64x32` do ctyr regionu:

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
  - pouziva se pro fullscreen emote, napr. hodiny nebo GIF

Normalni oblicej se sklada ze tri casti `eye`, `nose`, `mouth`. Kdyz je aktivni `whole`, ostatni casti se skryji.

## OLED UI

UI je definovane v `UI.py` jako jednoduchy stavovy automat.

### Dostupne obrazovky

- `main_menu`
- `main_screen`
- `emotes_menu`
- `emote_detail`
- `settings_menu`

### Ovladani tlacitky

Projekt pouziva dve tlacitka:

- `BUTTON_DOWN`
  - pohyb na dalsi polozku
  - pripadne navrat z detailu zpet

- `BUTTON_UP`
  - potvrzeni vyberu

### Polozky menu

Hlavni menu:

- `Emotes`
- `Settings`

Menu emote:

- `Gif`
- `Clock`
- `Cross`
- `Open eye`
- `Sleep`
- `Dice`
- `Back`
- testovaci polozky `test3`, `test4`, `test5`

Menu nastaveni:

- `Display`
- `Boop`
- `Mic`
- `Blink`
- `Accelerometer`
- `Wifi`
- `Verbose`
- `Back`

UI zobrazuje vpravo nahore cas a prvni radek automaticky zkracuje tak, aby se s hodinami neprekryval.

## Emote system

Za beh obliceje odpovida `FaceEmoteController` v `emotes.py`.

### Regiony

Controller interni spravuje ctyri regiony:

- `eye_region`
- `nose_region`
- `mouth_region`
- `whole_region`

Kazdy region si drzi:

- aktivni nebo neaktivni stav
- aktualni zdroj obrazku
- dobu trvani
- cas od spusteni
- pripadny `gifio.OnDiskGif` player

### Idle stav

Ve vychozim stavu se pouzivaji:

- oko: `/faces/eye.bmp`
- nos: `/faces/nose.bmp`
- usta: `/faces/mouth.bmp`

### Automaticke reakce

Pokud neni aktivni fullscreen emote z menu, bezi tato logika:

- mikrofon:
  - kdyz `mic_value > 5`, zobrazi se mluvici usta

- proximity:
  - kdyz `proximity_value > 200`, oko prejde do `boop` vyrazu

- blikani:
  - po urcitem poctu cyklu se aktivuje blink emote oka

### Emote z menu

Pri otevreni detailu emote se na RGB matici prubezne renderuje odpovidajici vyraz:

- `Clock`
  - fullscreen bitmapa s aktualnim casem

- `Gif`
  - fullscreen GIF `giphy.gif`

- `Dice`
  - fullscreen GIF `dice.gif`

- `Cross`
  - kriz misto oka

- `Sleep`
  - zavrene oko

- `Open eye`
  - otevrene oko + mluvici usta

Dokud je detail emote aktivni, ma tento vyber prioritu nad automatickymi reakcemi ze senzoru.

## Konfigurace

### `settings.toml`

Projekt pouziva `settings.toml` pro:

- Wi-Fi prihlasovaci udaje
- hostname zarizeni
- vychozi zapnuti jednotlivych modulu

Doporuceny tvar:

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
VERBOSE = false
```

Poznamka:

- `settings.toml` obsahuje citlive udaje a nema smysl ho commitovat s realnymi hesly
- promenne `AP_SSID` a `AP_PASSWORD` jsou v aktualnim kodu pritomne v konfiguraci, ale aplikace je nikde nepouziva

### Runtime perzistence

Prepinace z OLED menu se ukladaji do `microcontroller.nvm`.

To znamena:

- zmena pres menu prezije restart
- ulozene runtime nastaveni ma prioritu pred vychozi hodnotou ze `settings.toml`

V `code.py` je pro to pouzit jednoduchy bitovy format s magic hlavickou `PFS1`.

### Prepinatelne funkce

Z UI lze zapinat a vypinat:

- `Display`
- `Boop`
- `Mic`
- `Blink`
- `Accelerometer`
- `Wifi`
- `Verbose`

## Sit a cas

### Wi-Fi

Trida `Wifi`:

- nacte credentials z environment promennych
- zkusi hlavni Wi-Fi
- pri selhani zkusi zalozni sit
- nastavi `wifi.radio.hostname`
- pripravi `socketpool.SocketPool`
- nastavi mDNS jmeno zarizeni

### Hodiny a NTP

Trida `Clock`:

- pouziva `adafruit_ntp.NTP`
- synchronizuje `rtc.RTC()`
- vraci cas jako `HH:MM`

Pokud neni dostupna sit nebo je sync vypnuty, pouzije fallback datum nebo cas a aplikace nespadne.

## Jednotlive moduly podrobne

### `display.py`

Trida `Display` resi:

- inicializaci `rgbmatrix.RGBMatrix`
- vytvoreni `FramebufferDisplay`
- spravu `displayio.Group`
- vytvareni regionu pres `create_matrix()`
- prekresleni pres `refresh()`
- deinit pro korektni znovuvytvoreni displeje

Dale obsahuje utility pro:

- prevod 2D pole na `displayio.Bitmap`
- kopirovani bitmap do regionu
- mapovani barev do lokalni palety
- prevod `RGB565 -> RGB888`
- nacitani BMP a GIF frame do aktivniho regionu

### `I2C_sim.py`

Soubor centralizuje I2C zarizeni:

- `get_i2c()`
  - vraci sdilenou I2C sbernici

- `scan_i2c()`
  - vraci seznam nalezenych adres

- `APDSSensor`
  - proximity a color data z `APDS9960`

- `OLEDDisplay`
  - textovy wrapper nad `SSD1306`
  - vlastni jednoduchy 5x7 font
  - multiline rendering
  - davkove vykresleni vice textovych bloku

### `accelerometer.py`

Modul:

- inicializuje `LIS3DH`
- pri startu provede kalibraci z vice vzorku
- vraci odchylku od klidoveho stavu pres `derivation()`

V `code.py` se tato odchylka pouziva pro posun dlazdic obliceje po displeji.

### `mic.py`

Modul:

- nacita analogovy mikrofon na `A3`
- pri startu zmeri klidovou uroven
- vraci normalizovanou odchylku od baseline

### `UI.py`

Modul:

- drzi seznamy menu polozek
- uklada vybrany index a scroll offset
- generuje udalost `EVENT_SETTING_SELECTED`
- vykresluje menu na OLED pres `show_text_blocks()`

### `emotes.py`

Modul:

- sjednocuje obrazkove a GIF emote zdroje
- spravuje prepinani mezi idle a aktivnim stavem
- prehrava GIF po snimcich
- vytvari fullscreen bitmapu s casem
- implementuje prioritu menu emote nad automatickymi reakcemi

## Jak pridat novy emote

Nejjednodussi postup:

1. vloz novy asset do `faces/`
2. v `emotes.py` vytvor novy source pres:
   - `create_image_emote(...)`
   - nebo `create_gif_emote(...)`
3. pridej polozku do `self.emotes_menu_items` v `UI.py`
4. rozsirit `_apply_active_menu_emote()` v `FaceEmoteController`
5. podle potreby nastav cilovy region:
   - `eye`
   - `mouth`
   - `nose`
   - `whole`

Priklad pro bitmapovy emote:

```python
self.eye_happy_emote = create_image_emote("/faces/eye_happy.bmp", "happy")
```

A nasledne v `_apply_active_menu_emote()`:

```python
if active_menu_emote == "happy":
    requests["eye"]["source"] = self.eye_happy_emote
    requests["eye"]["duration"] = 1
    return True
```

## Nasazeni na zarizeni

Typicky postup:

1. nahrat `CircuitPython` na `MatrixPortal S3`
2. zkopirovat Python soubory do korene zarizeni
3. zkopirovat obsah `lib/`
4. zkopirovat adresar `faces/`
5. upravit `settings.toml`
6. restartovat zarizeni

Po restartu se automaticky spusti `code.py`.

## Ladeni

### Verbose rezim

Pri zapnuti `Verbose` se do serial konzole vypisuje:

- akcelerometr
- mikrofon
- proximity
- zmeny nastaveni z UI

### I2C diagnostika

`I2C_sim.py` obsahuje `scan_i2c()`, ktere lze pouzit pro kontrolu, zda jsou zarizeni na sbernici skutecne videt.

### Typicke problemy

- OLED nic nezobrazuje
  - zkontroluj adresu `0x3C`
  - over zapnuti `SSD1306_ON`
  - over I2C zapojeni

- Wi-Fi se nepripoji
  - over hodnoty v `settings.toml`
  - zkontroluj, zda neni problem s dosahem
  - projekt zkousi i zalozni sit

- hodiny ukazuji spatny cas
  - over funkcni Wi-Fi
  - zkontroluj `tz_offset` v `clock.py`

- oblicej nereaguje na pohyb
  - over inicializaci `LIS3DH`
  - zkontroluj, ze je zapnuty `Accelerometer`

- usta nereaguji na zvuk
  - over mikrofon na pinu `A3`
  - uprav prah `mic_value > 5` podle realneho hardware

- boop nereaguje
  - over `APDS9960`
  - uprav prah `proximity_value > 200`

## Poznamky k dalsimu rozvoji

Soucasna architektura je dobre pouzitelna pro dalsi rozsirovani:

- nove emote assety
- dalsi polozky OLED menu
- detailnejsi status obrazovky
- webove rozhrani pres Wi-Fi
- jemnejsi animace podle senzoru

Prakticky je projekt uz ted rozdeleny do rozumne samostatnych vrstev:

- hardware wrappery
- UI logika
- emote controller
- hlavni runtime orchestrator

To usnadnuje upravy bez nutnosti prepisovat cely projekt.
