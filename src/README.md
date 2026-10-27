# ProtoFace

Technicka dokumentace a specifikace chovani pro prepis projektu z CircuitPython do C++.

Overeno proti aktualnimu pracovnimu stromu dne 27. 10. 2026 (vcetne dosud necommitnutych uprav). Implementacni kontrakty, use cases a postup migrace jsou v kapitole [Podklady pro prepis do C++](#podklady-pro-prepis-do-c). Python firmware zustava referencni implementaci; navrzena C++ architektura zatim neni implementovana.

Projekt zobrazuje animovany oblicej na HUB75 RGB LED matici `128x32` slozene ze dvou `64x32` panelu, ovladaci menu na OLED `SSD1306`, reaguje na mikrofon, proximity senzor a akcelerometr a umi volitelne pripojit Wi-Fi, synchronizovat cas a vystavit jednoduche HTTP ovladani.

## Co projekt umi

- vykreslit oblicej z oddelenych casti `eye`, `nose`, `mouth`
- prehravat fullscreen emote a GIF animace na cele matici
- plynule morfovat staticke BMP emotes presunem pixelu mezi jejich pozicemi
- otevrit usta pri zvuku z mikrofonu
- spustit `boop` reakci podle proximity senzoru
- posouvat oblicej podle pohybu z akcelerometru
- zobrazit OLED menu pro emote, nastaveni a debug
- staticky zalamovat dlouhe OLED polozky a drzet vybrany kurzor na obrazovce
- pres Wi-Fi synchronizovat cas a zobrazovat ho na OLED i RGB matici
- prijimat jednoduche HTTP prikazy `up`, `down`, `ok`, `back` jako dalkove ovladani menu
- merit odezvu hlavni smycky, vytizeni runtime, pomale sekce a volnou pamet
- aplikovat globalni rainbow/wave barevny efekt s omezenou obnovovaci frekvenci
- prijimat ovladani menu z externiho ESP32 ovladace pres ESP-NOW
- menit jas RGB matice a PWM vykon ventilatoru pres OLED menu

## Cilovy hardware

Aktualni projekt odpovida konfiguraci:

- deska: `Adafruit MatrixPortal S3`
- firmware: CircuitPython; historicke overeni nahrani nize pouzivalo `10.2.1`, aktualni verzi na desce tento dokument znovu neoveruje
- hlavni vystup: HUB75 RGB matrix `128x32` jako dva `64x32` panely
- OLED: `SSD1306 128x64` na `0x3C`
- proximity senzor: `APDS9960`
- akcelerometr: `LIS3DH` na `0x19`, alternativne `0x18`, rozsah ?2 g
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
  - cteni aktivnich pixelu a vykreslovani mezisnimku pro BMP morph
  - globalni rainbow efekt s throttlingem pres `RAINBOW_FRAME_SKIP`
  - globalni jas pres `BRIGHTNESS_STEPS`

- `emotes.py`
  - definice emote zdroju
  - sprava regionu `eye`, `nose`, `mouth`, `whole`
  - blikani, boop, reakce na mikrofon
  - prehravani BMP prechodu predgenerovanych na PC
  - fullscreen hodiny kreslene vlastnim 5x7 fontem

- `UI.py`
  - stavovy automat OLED menu
  - menu `Emotes`, `Settings`, `Debug`
  - synchronizace stavu toggle voleb
  - prijem lokalnich tlacitek i HTTP prikazu
  - adaptivni zalamovani a strankovani podle skutecneho poctu OLED radku
  - ochrana proti opakovanemu odeslani stejneho framebufferu pres I2C

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
- `blep.bmp`
- `flat_mouth.bmp`
- `hearth.bmp`
- `question.bmp`
- `sad_eye.bmp`
- `sad_mouth.bmp`
- `test_colors.bmp`
- `u.bmp` (UwU oko)
- `wwww.bmp` (UwU/OwO usta)
- `uwu_text.bmp` (UwU Full)

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

Pro predgenerovane morphy poskytuje `Display.load_transition()` sdilenou
cache a `draw_sparse_rgb565()` vykresluje ridke mezisnimky v logickych
souradnicich. Renderer zajisti zrcadleni jednotlivych panelu.

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

- `Hearth`
- `Narrow`
- `Sad`
- `Question`
- `Cross`
- `Open eye`
- `UwU`
- `UwU Full`
- `OwO`
- `Sleep`
- `Blep`
- `Dead`
- `Clock`
- `Name`
- `Slots`
- `Back`

Menu nastaveni:

- `Display`
- `Brightness`
- `Font`
- `Fan`
- `Boop`
- `Boop Calibrate`
- `Boop Rainbow`
- `Rainbow Override`
- `Mic`
- `Smooth Speak`
- `Speak Override`
- `Blink`
- `Smooth Transitions`
- `Accelerometer`
- `Wifi_Broadcast`
- `Wifi_Connect`
- `Verbose`
- `Back`

Debug screen zobrazuje aktualni radky s hodnotami:

- akcelerometr
- mikrofon
- APDS proximity
- prumerny a maximalni cas smycky
- prumerny cas prace a odhad vytizeni
- volnou pamet

OLED se neprekresluje v kazde iteraci hlavni smycky. `needs_render` se nastavi
jen pri zmene obrazovky, vyberu, hodnoty nastaveni, casu nebo debug textu.
Pred zapisem se navic porovna podpis vyslednych textovych bloku s poslednim
uspesne vykreslenym obsahem; identicky framebuffer se znovu neposila pres I2C.

Dlouhe polozky se neposouvaji vodorovne. Staticky se zalomi na vice fyzickych
radku podle aktualni velikosti fontu. Seznamy pocitaji vysku kazde polozky po
zalomeni, podle ni posouvaji `scroll_offset` a vzdy zachovaji na obrazovce
zacatek vybrane polozky s kurzorem. Nadpis ma rezervovany jeden radek a muze se
zkratit, aby neodsunul kurzor mimo displej. Prvni radek stale ponechava prostor
pro hodiny vpravo nahore.

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
- odkaz na predgenerovane snimky, cas zacatku a posledni vykresleny krok BMP prechodu
- priznak, zda prechod konci navratem do idle zdroje

### Idle stav

Vychozi obrazky:

- oko: `/faces/eye.bmp`
- nos: `/faces/nose.bmp`
- usta: `/faces/mouth.bmp`

### Automaticke reakce

Pokud neni aktivni menu emote:

- mikrofon:
  - `MAX9814 OUT` je pripojeny na `ADS1115 A0`
  - pri `mic_value >= 5` se prodlouzi mluveni o 200 ms; hodnota `> 3` prodlouzi pouze jiz aktivni podrzeni

- proximity:
  - pri `proximity_value > BOOP_PROXIMITY_THRESHOLD` se aktivuje `boop` oko
  - `225` je pocatecni fallback; runtime threshold adaptuje podle posledni sekundy vzorku (prumer + 15, nejvyse 255), s pozastavenim uceni pri boopu

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
Volba `Speak Override` dovoli mikrofonu docasne nahradit pouze region ust
animaci `mouth_speak`; fullscreen emote zustava nadrazeny.

- `Name`
  - fullscreen napis `ZTRACEN?`, generovany bez externiho obrazku

- `UwU`, `OwO`
  - kombinovane oci a usta `wwww`, prazdny nos

- `UwU Full`
  - fullscreen BMP `uwu_text.bmp`

- `Clock`
  - fullscreen hodiny vykreslene vlastnim 5x7 fontem se skalovanim `2x`
  - bitmapa hodin se cachuje a prekresli se jen pri zmene textu casu

- `Slots`
  - fullscreen automat se tremi valci a sesti jednoduchymi symboly
  - boop senzor spusti kratke roztoceni a valce se postupne zastavi
  - dalsi roztočení se spusti az novym boopem po oddaleni ruky

- `Cross`
  - kriz v regionu oka

- `Hearth`
  - srdce v regionu oka

- `Narrow`
  - privrene oko a rovna usta

- `Sad`
  - kombinuje `/faces/sad_eye.bmp` a `/faces/sad_mouth.bmp`

- `Question`
  - otaznik v regionu oka

- `Sleep`
  - spici oko

- `Open eye`
  - otevrene oko a mluvici usta

- `Blep`
  - vyplazeny jazyk v regionu ust

- `Dead`
  - cerveny kriz, nos a smutna usta (`sad_mouth.bmp`); nazev lokalni promenne v kodu je zavadejici

### Pixelovy prechod BMP

Pixelovy morph je volitelny pres `Smooth Transitions` a ve vychozim stavu
je vypnuty. Po zapnuti controller prehrava soubory z `transitions/`, ktere
vznikly na PC. Na ESP32 se jiz nehleda nejblizsi cilovy pixel ani nepocita
interpolace. Vsech 51 paru registrovanych vyrazu oci a pusy ma po 7 snimcich;
zpetny smer pouziva stejne snimky v opacnem poradi.

Prechod trva 200 ms podle `time.monotonic()`. Oba panely sdileji data i cas
aktualizace; zrcadleni provadi renderer. Pri zpozdeni se preskoci stare
mezisnimky, pri nezmenenem indexu se znovu nekopiruji.
`Smooth Speak` zapina samostatne plynule otevirani a zavirani pusy, i kdyz
je globalni `Smooth Transitions` vypnute. Zmena smeru navazuje na aktualni
otevreni. Podrzeni mikrofonu je take casove (200 ms).

Chybejici nebo nepodporovane prechody se nahradi okamzitym prepnutim;
GIFy a dynamicke bitmapy tento morph nepouzivaji. Zakladni soubor pro
mouth/speak je povinny pri startu. Pri preruseni obecneho morphu novym
vyrazem muze vzniknout skok, protoze dalsi prechod vychazi z predchoziho
ciloveho vyrazu. Podrobnosti viz [generovani na PC](#prechody-generovane-na-pc).

V kodu zustava zaklad prehravani GIFu a zakomentovane vetve pro `Gif`, `Dice`
a `Color`. Tyto polozky nejsou v aktualnim menu ani v dodane sade assetu a bez
doplneni souboru a aktivace vetvi se nepovazuji za dostupne emotes.

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
WIFI_CONNECT_ON = false
WIFI_BROADCAST_ON = true
AP_SSID = "Alan Protogen"
AP_PASSWORD = ""
SMOOTH_SPEAK_ON = false
SPEAK_OVERRIDE_ON = false
BLINK_ON = true
DISPLAY_ON = true
BOOP_RAINBOW_ON = true
RAINBOW_OVERRIDE_ON = false
SMOOTH_TRANSITIONS_ON = false
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
- `WIFI_CONNECT_ON`
- `WIFI_BROADCAST_ON`
- `AP_SSID`
- `AP_PASSWORD`
- `SMOOTH_SPEAK_ON`
- `SPEAK_OVERRIDE_ON`
- `BLINK_ON`
- `DISPLAY_ON`
- `BOOP_RAINBOW_ON`
- `RAINBOW_OVERRIDE_ON`
- `SMOOTH_TRANSITIONS_ON`
- `VERBOSE`

`BLINK_ON` a `DISPLAY_ON` nejsou v `settings.example.toml` uvedene, ale runtime
je podporuje a pri chybejici hodnote pouzije vychozi `true`.

### Runtime perzistence

Hodnoty z UI se ukladaji do `microcontroller.nvm`.

- pouziva se magic hlavicka `PFS4`
- stavy jsou ulozene jako bitove pole
- `Brightness`, `Font` a `Fan` jsou ulozene jako indexy preddefinovanych kroku
- runtime nastaveni ma prioritu nad `settings.toml`

Pres UI lze za behu menit:

- `Display`
- `Brightness`
- `Font`
- `Fan`
- `Boop`
- `Boop Calibrate`
- `Boop Rainbow`
- `Rainbow Override`
- `Mic`
- `Smooth Speak`
- `Speak Override`
- `Blink`
- `Smooth Transitions`
- `Accelerometer`
- `Wifi_Broadcast`
- `Wifi_Connect`
- `Verbose`

`SSD1306_ON` se cte jen pri startu, v UI se neprepina.

## Sit a HTTP ovladani

### Wi-Fi

`Wifi` v `wifi_network.py` podporuje dva vzajemne prepinane rezimy:

- `Wifi_Broadcast` (vychozi): vlastni AP, kanal 1, nejvyse 4 klienti; SSID a heslo z `AP_SSID` a `AP_PASSWORD`. Bez SSID pouzije `Alan_Protogen-`, bez hesla otevrenou sit. Priklad konfigurace pouziva `Alan Protogen`.
- `Wifi_Connect`: klient existujici site; vyhleda kanal a zkusi hlavni a potom zalozni credentials. Po pripojeni vytvori socket pool a mDNS a zkusi NTP.
- HTTP bezi i v AP rezimu, adresu vypisuje runtime. AP nevytvari mDNS server, proto zde pouzijte primou IP.
- Pri odpojeni nebo nenalezene siti se radio ponecha na fallback kanalu 1 pomoci otevreneho AP `<hostname>-fallback`; HTTP je zastaveny. To umoznuje pokracovat s ESP-NOW, pokud controller pouziva stejny kanal.
- `WIFI_ON` je odvozeno jako OR obou rezimu; samostatny stejnojmenny TOML klic neurcuje start. Pokud jsou pri startu zapnute oba rezimy, prednost ma broadcast.

### HTTP server

`ServerClass` v `server.py` startuje server na portu `80` a vystavuje:

- `/`
  - webove ovladani z `/static/index.html`; pri chybejicim souboru nahradni HTML

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

- `/api/time?year=2026&month=10&day=27&hour=20&minute=30&second=0`
  - prevezme lokalni cas prohlizece, nastavi RTC a vrati `ok` a `clock_text`; pri chybe `ok: false` a `error`

Vsechny uvedene endpointy pouzivaji GET. Akce s registrovanym runtime callbackem ihned meni UI a vraceji snapshot po zmene; `api_call` je pouze zalozni cesta bez callbacku. Zmena obliceje se projevi pri nasledujici aktualizaci emote controlleru.

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
4. zkopirovat adresare `faces/`, `transitions/` a `static/`
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
- bezne OLED obrazovky se odesilaji jen pri zmene obsahu
- identicke textove bloky jsou odfiltrovane pred drahym I2C `display.show()`
- dlouhe UI polozky se staticky zalamuji bez casovaneho prekreslovani
- BMP assety jsou cachovane po prvnim nacteni
- cached RGB565 pixely se kopiruji rychlejsi cestou bez dalsi konverze
- clock emote se regeneruje jen pri zmene casu
- rainbow/wave efekt se prepocitava kazdy treti refresh
- oci a pusa pouzivaji sedmisnimkove prechody generovane na PC

Typicke namerene hodnoty po optimalizaci byly priblizne:

- `loop_avg` kolem `50-55 ms`
- `work_avg` kolem `20-28 ms`
- `load` kolem `40-50 %`
- bezne `slowest=emote` kolem desitek ms

Obcasne spicky jsou stale mozne pri skutecne zmene OLED obsahu, GC, prvotnim
nacteni BMP ci souboru prechodu nebo narocnejsim
efektu. Prubezne vysoke `slowest=ui` mimo zmeny obsahu uz ocekavane neni.

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
  - pripadne over prahy `MIC_SPEAK_THRESHOLD = 5` a `MIC_RELEASE_THRESHOLD = 3`

- boop nereaguje
  - over `APDS9960`
  - pouzij `Boop Calibrate`; fallback `BOOP_PROXIMITY_THRESHOLD` runtime doplnuje adaptivnim prahem

- animace seka pri rainbow/wave efektu
  - zvedni `RAINBOW_FRAME_SKIP` v `display.py`
  - vypni `Boop Rainbow` nebo `Rainbow Override`
  - over v `/api/perf`, jestli je nejpomalejsi `emote`, `display` nebo `ui`

- OLED zpomaluje smycku
  - debug hodnoty se maji aktualizovat jen na Debug obrazovce
  - over, zda se skutecne meni hodiny, debug radky nebo stav menu
  - bez zmeny obsahu ma `UI.render_ui()` pres `needs_render` okamzite skoncit
  - pokud je `slowest=ui` jen na Debug obrazovce, zvys `DEBUG_UI_UPDATE_INTERVAL`

- kurzor nebo polozka menu neni videt
  - UI strankuje podle poctu fyzickych radku po zalomeni
  - over aktualni velikost `Font`; velmi dlouha polozka muze zaplnit vsechny dostupne radky
  - nadpis se muze zkratit, aby prvni radek vybrane polozky zustal viditelny

- pixelovy prechod zacina z opacne strany
  - over `mirror_x`; `get_active_pixels_rgb565()` musi vracet logicke, ne fyzicky zrcadlene X
  - over stejny cas aktualizace obou panelu a aktualnost souboru `transitions/`

## Poznamky k aktualnimu stavu

README odpovida aktualnimu kodu v repozitari, vcetne:

- HTTP serveru v `server.py`
- endpointu `/api/perf` a `/api/action/back`
- debug obrazovky v `UI.py`
- lokalnich tlacitek `BUTTON_UP`, `BUTTON_DOWN`, `A4`
- ctyrtlacitkoveho ESP-NOW controlleru s `button4` jako `back`
- menu nastaveni `Brightness` a `Fan`
- NVM hlavicky `PFS4`
- runtime nastaveni `BLINK_ON`, `DISPLAY_ON`, `BOOP_RAINBOW_ON`, `RAINBOW_OVERRIDE_ON`, `SMOOTH_SPEAK_ON`, `SPEAK_OVERRIDE_ON`, `Brightness`, `Font` a `Fan`
- performance mereni v `performance.py`
- cache BMP assetu a rychle RGB565 cesty v `display.py`
- adaptivni viceradkove OLED menu a deduplikace framebufferu v `UI.py`
- PC generatoru, sdilene cache a casovanych BMP prechodu v `emotes.py`
- zpomaleneho blink intervalu pres `BLINK_TIME_SET = 100`


### Prechody generovane na PC

Spustte z korene repozitare `python tools/generate_transitions.py`.
Generator bez externich knihoven vytvori `src/transitions/*.mph`: vsech 51
paru mezi 9 vyrazy oci a 6 vyrazy pusy (135.5 KiB v aktualnich assetech).
Kazdy soubor obsahuje 7 ridkych RGB565 snimku, souradnice a hlavicku.
Po zmene BMP souboru je nutne generator spustit znovu a nahrat prechody.

Na desku patri `display.py`, `emotes.py`, `precomputed.py` i adresar
`transitions/`. Parovani pixelu a interpolace bezi pouze na PC. Mezisnimky
pro oba panely jsou sdilene a zpetny prechod pouziva obracene poradi.
Cache drzi nejvyse 6 paru; aktivni animace a Smooth Speak si mohou ponechat
vlastni odkazy. Barvy se pri nacteni prizpusobi aktualnimu jasu a zapojeni.
Zmena jasu znovu vytvori display stack a cache.

`SPEAK_TRANSITION_SECONDS = 0.20` urcuje dobu predgenerovanych prechodu;
obecne prechody i Smooth Speak ridi `time.monotonic()`. Pri zpomaleni smycky
se stare snimky preskoci. Podrzeni mikrofonu trva `MIC_SPEAK_HOLD_SECONDS`.
Pokud prechod neni dostupny (napr. fullscreen nebo dynamicky obrazek),
obrazek se prepne primo bez narocneho runtime morphu. Chybejici zakladni
prechod mouth/speak vyvola srozumitelnou chybu pri startu.
Pri preruseni obecneho morphu jinym vyrazem zacina dalsi prechod od
predchoziho ciloveho vyrazu; muze tedy vzniknout drobny skok. Smooth Speak
meni smer prubezne z aktualniho otevreni. GIFy zustavaji beze zmen.

Host overeni: `python -m unittest discover -s tests`.
Skutecnou plynulost a pamet je nutne merit na MatrixPortal S3.


#### Regenerovani a nahrani

Z korene repozitare:

```powershell
python tools/generate_transitions.py
python -m unittest discover -s tests
python -m py_compile src/emotes.py src/display.py src/precomputed.py tools/generate_transitions.py
.\deploy_portal.ps1
```

`deploy_portal.ps1` vyhleda disk `CIRCUITPY`, vyzada potvrzeni a zkopiruje
`src/` vcetne `transitions/`; `settings.toml` neprepisuje. Generator se ve
skriptu nespousti automaticky. Skript na konci otevre serial monitor na
pevnem `COM4`; skutecny port je nutne overit (pri nahrani 22. 10. 2026 to byl
`COM5`). Pri rucnim kopirovani nahrajte tri Python soubory uvedene vyse a
cely adresar `transitions/` do korene disku desky.

#### Format a pamet

Soubor `.mph` obsahuje hlavicku `MPH1`, jednobajtovou sirku, vysku a pocet
snimku. Kazdy snimek zacina 16bitovym little-endian poctem zaznamu;
zaznam ma 4 bajty: `x`, `y`, RGB565 little-endian. Cerne pixely se neukladaji,
proto je skutecna velikost mensi nez u plnych RGB565 bitmap.

Aktualnich 51 souboru ma dohromady 138 727 bajtu (135,5 KiB) v ulozisti.
To neni trvala spotreba RAM: nacitaji se jednotlive pary, cache se po
naplneni sesti polozek vyprazdni a aktivni prehravace mohou stale drzet
odkazy. K pixelovym datum je treba pripocitat rezii objektu a docasne buffery
pri nacitani. Skutecnou volnou RAM sledujte pres `/api/perf` (`mem_free`).

#### Overeni nahrani 22. 10. 2026

Na MatrixPortal S3 s CircuitPython 10.2.1 byly nahrany tri Python soubory a
51 souboru prechodu (54 souboru celkem). Kopie byly overeny SHA-256.
Proslo 10 host testu, kontrola syntaxe a `git diff --check`. Serial na COM5
ukazoval bezici `code.py` bez zachycene chyby. Toto overeni nepotvrzuje
vizualni plynulost ani spotrebu RAM pri vsech kombinacich efektu.

## Podklady pro prepis do C++

Tato kapitola popisuje kompatibilitu s aktualnim Python runtime. Odstavce oznacene
**Navrh C++** jsou navrh implementace, nikoliv popis existujiciho firmware.
Pro zachovani presneho vzhledu preneste i existujici BMP, fontove tabulky a webovou
stranku; samotny text README nenahrazuje binarni assety.

### Rozsah a hranice migrace

Prepisuje se firmware MatrixPortal S3 (`src/*.py`). `controller/src/main.cpp` je
jiz C++ a zustava komunikacnim partnerem; generator `tools/generate_transitions.py`
muze nadale bezet na PC v Pythonu. C++ firmware musi zachovat menu, reakce,
geometrii, barvy, konfiguraci a sitovy protokol. Neni potreba prenaset `.mpy`
knihovny: ty jsou soucasti CircuitPython, nikoliv znovupouzitelnym C++ kodem.

**Navrh C++:** oddelte cistou logiku od ovladacu, aby se dala simulovat na PC:

| Komponenta | Vstup a vystup / odpovednost | Reference |
|---|---|---|
| Runtime | nastaveni, senzory, udalosti -> jeden krok aplikace | `code.py` |
| SensorService | platnost vzorku, mikrofon, proximity, relativni pohyb | `mic.py`, `accelerometer.py`, `I2C_sim.py` |
| BoopTracker | vzorek + monotonic cas + freeze -> threshold | `BoopThresholdTracker` |
| MenuModel | `Up/Down/Ok/Back` -> obrazovka, emote, setting event | `UI.py` |
| FaceController | menu + senzory + cas -> pozadavky regionu a efekty | `emotes.py` |
| TransitionPlayer | dvojice zdroju + cas -> sdileny sparse frame | `precomputed.py` |
| MatrixRenderer | logicke regiony -> HUB75 vystup | `display.py` |
| OledRenderer | model menu -> textove bloky a framebuffer | `UI.py`, `I2C_sim.py` |
| SettingsStore | load/save booleanu a hodnotovych indexu | NVM funkce v `code.py` |
| NetworkService | AP/STA, ESP-NOW, HTTP -> udalosti a JSON | `wifi_network.py`, `server.py` |
| ClockService / Performance | RTC, NTP / statistiky smycky | `clock.py`, `performance.py` |

Pouzijte typovane enumy pro obrazovky, emote a udalosti; chybejici vzorek musi mit
vlastni priznak platnosti (nenahrazovat nulou). Sdilene prechody musi zit alespon
po dobu vsech aktivnich prehravacu, i kdyz je cache vyprazdnena.

### Use cases a akceptacni scenare

Kazdy scenar overte na C++ firmware a porovnejte se stejnymi vstupy Pythonu.

| ID | Predpoklad a akce uzivatele | Pozadovany vysledek a alternativy |
|---|---|---|
| UC01 Start | Zapnout desku s platnym ulozenym nastavenim | Obnovit volby, inicializovat povolene periferie, vykreslit idle oblicej a hlavni menu. Neplatna hlavicka nastaveni -> TOML/defaulty. Chybejici volitelny senzor neukonci aplikaci. |
| UC02 Ovladani | V menu stisknout lokalni tlacitko, controller nebo webovou sipku | Jedna akce meni jednu logickou polozku, seznam cykli pres konec. Drzeni lokalniho tlacitka neposila dalsi hrany. `BUTTON_UP` znamena potvrzeni, nikoliv sipku nahoru. |
| UC03 Vyraz | Emotes -> Sad -> Ok | Smutne oko a usta na obou stranach, nos idle. Detail drzi vyraz. Predchozi/dalsi nebo Back vrati seznam a automaticke reakce. |
| UC04 Mluveni | Bez detailu emote dodat mic >= 5, potom ticho | Mluvici usta, minimalne casove podrzeni 200 ms od posledniho prodlouzeni; pri Smooth Speak plynule otevreni/zavreni. Hodnota <= 3 neprodluzuje podrzeni. |
| UC05 Speak Override | Sad detail + zapnuty Speak Override + zvuk | Mikrofon prevezme pouze usta. Oci zustanou Sad. Clock/Name/Slots/UwU Full zustavaji fullscreen bez mluvicich ust. |
| UC06 Boop | Priblizit ruku nad adaptivni threshold v idle | Otevrene oko, pri Boop Rainbow barevny efekt. Tracker behem reakce neuci ruku jako klidovou uroven. Boop Calibrate resetuje vzorky podle aktualni hodnoty. |
| UC07 Blink | Idle bez boopu a menu detailu | Po 125 zpusobilych update krocich pozadavek na blink, delka 16 kroku. Vypnuty Blink ho nespousti. Nejde o 125 sekund ani pevny pocet ms. |
| UC08 Fullscreen | Vybrat Clock, Name nebo UwU Full | Cele `64x32` na obou panelech; skryte dilci regiony. Clock meni bitmapu pri zmene HH:MM; Name ukazuje ZTRACEN?. |
| UC09 Slots | Otevrit Slots, priblizit a podrzet ruku | Jeden spin, valce konci v krocich 16/22/28; ruka drzenim nespousti dalsi spin. Oddalit a znovu priblizit -> dalsi spin. Odchod z detailu zrusi rozto?en?. |
| UC10 Pohyb | Naklonit desku mimo fullscreen | Pri absolutni odchylce libovolne osy > 1 posunout vsechny regiony o `-int(dx), +int(dy)` od aktualni pozice. Pri klidu obnovit zakladni pozice. |
| UC11 Nastaveni | Zmenit Brightness, Font, Fan a prepinac, restartovat | Kroky cykli; po restartu zustanou ulozene indexy/volby. Brightness obnovi display stack a cache. Display OFF uvolni RGB vystup, menu pokracuje. |
| UC12 Telefon | Pripojit telefon k AP a otevrit vypsanou IP | Web ukazuje stejny model menu; GET akce vraci novy snapshot. Nastaveni casu pres /api/time aktualizuje RTC i hodiny. |
| UC13 Sit | Prepnout Wifi_Broadcast na Wifi_Connect | Zastavit predchozi HTTP, prepnout rezim, zkusit hlavni/zalozni sit, obnovit sluzby. Neuspech nesmi zastavit oblicej; fallback kanal 1. |
| UC14 Diagnostika | Otevrit Debug, pak ho zavrit | Hodnoty a metriky obnovovat nejvyse 1x/s, pri vstupu ihned. Mimo Debug neprekreslovat jeho hodnoty. Identicky OLED obsah znovu neposilat. |
| UC15 Prechody | Zapnout Smooth Transitions a prepnout vyraz | Sedm snimku behem 200 ms, obe strany stejny logicky krok. Pomala smycka preskoci stare kroky. Chybejici nepovinny prechod -> prime prepnuti. |
| UC16 Vypadek senzoru | Odpojit ADS1115/LIS3DH/APDS za provozu | Chybejici hodnota je neplatna, nikoliv aktivita; dostupne casti pokracuji. Ovladace zkouseji obnoveni; navrat mikrofonu muze zahrnovat kalibraci. |

### Poradi jednoho kroku a casova semantika

Referencni poradi je: zacatek profileru -> senzory a boop tracker -> nejvyse jedna
ESP-NOW zprava -> hrany lokalnich tlacitek -> pohyb -> UI + zmena nastaveni + OLED
-> FaceController -> HTTP poll -> RGB refresh -> ulozeni stavu tlacitek -> metriky
-> verbose log -> sleep 10 ms. HTTP callback tedy muze zmenit menu az po aktualizaci
obliceje v danem kroku. Nominalni sleep neni garantovana perioda ani 100 FPS.

**Navrh C++:** pouzijte monotonic cas pro animace a casove odecty bez problemu pri
prete?en? citace; RTC pouze pro datum/HH:MM. Pro prvni port zachovejte pocitadlove
reakce na definovanem logickem ticku. Prevod bliku, Slots, pohybu a rainbow na
milisekundy je vedoma zmena chovani, musi mit zvlast zvolenou periodu a overeni.
Rychlejsi C++ loop by jinak zrychlil animace i kumulativni pohyb.

Priorita se resi po regionech:

1. Menu detail nastavi pozadavky; fullscreen skryje vsechny dilci casti.
2. Mikrofon smi menit usta bez menu, nebo se Speak Override; nikdy pres fullscreen.
3. Boop smi menit oko pouze bez aktivniho menu a fullscreen.
4. Blink pouze bez menu/fullscreen, bez jineho pozadavku na oko a pri volnem oku.
5. Region bez aktivniho vyrazu se vraci na svuj idle zdroj.

Mluveni pouziva `mic >= 5` pro nove podrzeni `now + 0.20 s`; `mic > 3` ho
prodlouzi pouze dokud predchozi deadline nevyprsel. Hodnota `None` mikrofonni
vetev preskoci. Bezne regiony stale maji delky v update krocich (boop 5,
mic request 6, blink `100 // 6 = 16`); neprenaset tyto hodnoty jako sekundy.
Smooth Speak ma samostatnou casovou polohu a pri zmene smeru navazuje na aktualni
otevreni, i kdyz globalni Smooth Transitions neni zapnute.

Boop tracker pred prijetim vzorku odstrani hodnoty starsi nez 1 s, vypocita
`min(255, floor(prumer) + 15)` a teprve potom rozhodne o novem vzorku. Pokud je
vzorek nad prahem, neulozi ho a zmrazi uceni na 1 s. Pri aktivnim boopu je uceni
take zmrazene (vcetne orezavani okna). Bez vzorku zachova posledni threshold;
kalibrace maze okno a nastavi `min(255, value + 15)` nebo fallback 225.

### Vstupy, obraz a pamet

Mikrofon: ADS1115 `0x48`, single-ended A0, gain 1, data rate 860. Baseline je
prumer 20 vzorku s prodlevou 50 ms. Aktivita je
`round(abs(raw - baseline) / 1000, 2)`. Preneste rozsah hodnot `AnalogIn.value`;
surovy registr jine C++ knihovny nemusi mit stejnou skalu, a tedy ani prah 5.
LIS3DH: prumer 20 vzorku po 50 ms, odchylka od baseline zaokrouhlena na 2 mista.
I2C se sdili pres STEMMA_I2C, jinak board.I2C. PWM ventilatoru: A1, 25 kHz,
`round(percent * 65535 / 100)`, kroky 0/50/100 %.

Geometrie regionu je popsana vyse. Pri portu zachovejte i prekryv nose/eye na
sloupci 31 a poradi vrstev nose -> eye -> mouth -> whole. Pro prvni panel je
`tileX = 64 - sourceX - width` a lokalni pixel `x = width - 1 - logicalX`;
druhy panel ma `tileX = 64 + sourceX`, bez zrcadleni. Pohyb se aplikuje na
pozici regionu, ne na data prechodu. Nazvy left/right v kodu nejsou spolehlivym
popisem fyzicke leve/prave strany masky.

RGB888 se prevadi prohozenim G/B (`SWAP_GREEN_BLUE = True`), potom
`((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)`. Jas nasobi jednotlive
5/6/5bitove kanaly s orezanim dolu. Kroky 0.3/0.4/0.5/0.7/1.0,
vychozi index 2. Neaplikovat stejny jas znovu v ovladaci panelu.
Rainbow pracuje nad aktivnimi pixely, zachovava zakladni bitmapu a prepocitava
se kazdy treti refresh; rychlost faze 8, prostorove koeficienty X=10, Y=16.
Pro presny vzhled preneste wheel a vypocet z `display.py`.

Plny RGB565 framebuffer 128x32 zabere 8192 B; double buffering 16384 B bez DMA
bitplanu, regionu, zakladnich bitmap, OLED a cache. Rozpocet proto nezamenujte
s celkovou spotrebou. RGB vystup pouziva `BIT_DEPTH=2`, symbolicke piny
`MTX_R1/G1/B1/R2/G2/B2`, `MTX_ADDRA/B/C/D`, `MTX_CLK/LAT/OE`.
**Navrh C++:** konkretni GPIO cisla a HUB75/DMA ovladac overte proti definici
MatrixPortal S3 a zapojeni; tento repozitar nema C++ board konfiguraci prijimace.

Prechody `.mph` pouzijte podle formatu vyse. Jmeno je lexikograficky serazena
dvojice nazvu BMP bez pripon `a--b.mph`; opacny smer obraci snimky. Hlavicka ma
7 B, pocty zaznamu a barvy jsou little-endian. Barvy souboru jsou kanonicke
RGB565: pred panelovym prevodem expandovat r/b `*255//31`, g `*255//63`.
Kazdy sparse snimek nejprve vymaze predchozi obsah regionu. Cache klic zahrnuje
jmena i rozmery; pri sedmem novem paru se cela cache vyprazdni. Neplatna
hlavicka/zkraceny soubor vyvolava ValueError, chybejici soubor vraci None.
Zakladni mouth/speak par se nacita pri konstrukci controlleru i s vypnutymi
smooth volbami; jeho absence je startovni chyba.

### Presne zdroje menu emote

Prazdna bunka znamena idle region; fullscreen nahrazuje vsechny dilci regiony.
Cesty BMP jsou relativni k `/faces/`. Nazev `Hearth` zustava kvuli kompatibilite UI.

| Menu | Oko | Nos | Usta | Whole |
|---|---|---|---|---|
| Hearth | hearth.bmp | idle | idle | ? |
| Narrow | eye_blink.bmp | idle | flat_mouth.bmp | ? |
| Sad | sad_eye.bmp | idle | sad_mouth.bmp | ? |
| Question | question.bmp | idle | idle | ? |
| Cross | cross.bmp | idle | idle | ? |
| Open eye | eye_open.bmp | idle | mouth_speak.bmp | ? |
| UwU | u.bmp | cerna bitmapa 32x16 | wwww.bmp | ? |
| UwU Full | ? | ? | ? | uwu_text.bmp |
| OwO | eye_open.bmp | cerna bitmapa 32x16 | wwww.bmp | ? |
| Sleep | sleep.bmp | idle | flat_mouth.bmp | ? |
| Blep | idle | idle | blep.bmp | ? |
| Dead | cross.bmp cervene | nose.bmp cervene | sad_mouth.bmp cervene | ? |
| Clock | ? | ? | ? | generovane HH:MM |
| Name | ? | ? | ? | generovane ZTRACEN? |
| Slots | ? | ? | ? | generovane tri valce |

### Perzistence a konfiguracni kontrakt

PFS4 ma presne 9 B: offset 0..3 ASCII `PFS4`, 4..5 bitove pole (bit 0 je LSB
prvniho bajtu), 6 brightness index, 7 font index, 8 fan index.

| Bit | Klic | Default bez ulozene hodnoty/TOML |
|---|---|---|
| 0 | ACCELEROMETER_ON | true |
| 1 | MIC_ON | true |
| 2 | APDS_ON | true |
| 3 | WIFI_ON | odvozeny OR, nenacita se jako hlavni volba |
| 4 | VERBOSE | false |
| 5 | BLINK_ON | true |
| 6 | DISPLAY_ON | true |
| 7 | BOOP_RAINBOW_ON | true |
| 8 | RAINBOW_OVERRIDE_ON | false |
| 9 | WIFI_CONNECT_ON | false |
| 10 | WIFI_BROADCAST_ON | true |
| 11 | SMOOTH_TRANSITIONS_ON | false |
| 12 | SMOOTH_SPEAK_ON | false |
| 13 | SPEAK_OVERRIDE_ON | false |

PFS3 ma dva flag bajty bez indexu, PFS1 jeden flag bajt bez indexu. Neznamy
magic vraci prazdna nastaveni. Priznaky chybejici v kratsim formatu se doplni
z TOML/defaultu; bity pritomne v bajtu, i historicky nevyuzite, se ctou jako
ulozene hodnoty. U indexu mimo rozsah pouzit default: brightness 2,
font 0 (1.5x), fan 0. Font kroky jsou 1.5x/2x/2.5x. Indexy se ctou z NVM,
nikoliv z TOML. SSD1306_ON je startovni TOML volba s default true bez NVM bitu.
Boop Calibrate je akce a adaptivni threshold se neuklada.

**Navrh C++:** NVS muze nahradit fyzickou NVM, ale definujte verzi schematu a
jednorazovy import PFS4, pokud ma zustat nastaveni ze stareho firmware. Po
preflashovani neni automaticke zachovani CircuitPython NVM zaruceno. Podporu
TOML zachovejte parserem, nebo dodejte prevod konfigurace; credentials nepatri
do verejne dokumentace ani napevno do firmware.

### ESP-NOW a HTTP kontrakty

ESP-NOW payload: offset 0..3 `uint32_t counter` little-endian, bajty 4/5/6/7
jsou nenulove boolean Up/Down/Ok/Back. Prijimac akceptuje 7 B (Back=false)
nebo 8 B, jine delky odmita. Counter se dekoduje, ale zatim nededuplikuje.
Controller blokuje opakovani tlacitka 400 ms a musi mit spravnou MAC prijimace
a stejny kanal; AP_SSID ovladace musi odpovidat portalu. Pri STA rezimu se
controller sam neprepina podle domaciho SSID (hleda AP_SSID).
**Navrh C++:** kodujte bajty explicitne, nespol?hejte na velikost `bool` a
padding struktury. ESP-NOW callback muze vkladat udalosti do omezene fronty;
menu a I2C obsluhujte v hlavni uloze.

JSON menu odpoved obsahuje `ok`, `active_screen`, tri `*_selected_index`, tri
`*_scroll_offset` (main/emotes/settings), `selected_emote`, `clock_text`,
`selected_index`, `visible_items`, `scroll_offset`, `controls`.
`visible_items` jsou objekty `{index, label, selected}`, u nastaveni navic
`value` a `display_value` krom Back. `controls` je
`["up", "ok", "down", "back", "refresh"]`; refresh znamena znovu nacist menu.
Snapshot seznamu je logicky vyrez, nemusi odpovidat poctu fyzickych zalomenych
radku OLED. Pri nedostupnem UI: `{ok:false,error:"menu_snapshot_unavailable"}`.
Performance bez provideru: `{ok:false,error:"performance_unavailable"}`.
Time bez handleru: `{ok:false,error:"time_handler_unavailable"}`; chybne parametry
vraceji `ok:false` a text chyby. Chyby se vyjadruji JSONem, kod route nenastavuje
zvlastni HTTP chybovy status. `/api/time` zadny dalsi timezone prevod nedela.

Startovni obrazovka je main_menu. Seznamy cykli; Back z emote_detail vraci
emotes_menu, z podmenu hlavni menu. Prev/Next opousti detail; fyzicke Confirm
v detailu nic nedela, zatimco synchronni HTTP Ok pouzije stejnou confirm cestu.
Tuto drobnou asymetrii oproti zalozni `api_call` ceste pri portu evidujte.
Bez funkcniho OLED se UI model v aktualnim Pythonu vubec nevytvori, takze web
nema samostatne funkcni menu. Oddeleni menu od OLED v C++ je mozne vylepseni,
ale znamena rozsireni soucasneho chovani.

### Poradi implementace a dokonceni portu

1. Prenest assets, konfiguraci a cistou logiku MenuModel/BoopTracker/FaceController;
   pripravit simulovane senzory a injektovatelny monotonic cas.
2. Rozbehnout HUB75 se statickymi regiony, overit zrcadleni, prekryvy a RGB barvy;
   potom pridat .mph prehravac a Smooth Speak.
3. Pripojit sdilene I2C, OLED font a adaptivni layout, senzory a fan PWM.
4. Doplnit perzistenci, AP/STA, ESP-NOW, HTTP kontrakty a RTC.
5. Projit UC01?UC16, porovnat obraz i menu, merit RAM a nejhorsi odezvu na desce.

Stavajici host testy (`python -m unittest discover -s tests`) pokryvaji prechody
a Smooth Speak, nikoliv cely runtime. Pouzijte je jako referencni pripady pro
C++ testy, zejmena zmenu smeru mluveni, sdileni snimku a zpozdenou aktualizaci.
Doplnte hranicni pripady mic 3/5, boop rovno/nad threshold, chybne delky paketu,
NVM verze/indexy a plnou cache. Pro vizualni porovnani zachytte framebuffer pred
fyzickym zrcadlenim a stejny vysledek po mapovani na oba panely.

Port je hotovy az po overeni skutecneho HUB75 vystupu, senzoru, controlleru,
webu a restartu s ulozenym nastavenim. Kompilace ani host testy nepotvrzuji
fyzicke barvy, plynulost nebo RAM pri kombinaci rainbow, Slots a Wi-Fi.

Zname vlastnosti k vedomemu rozhodnuti: NTP ma pevny offset +2 bez automatickeho
letniho/zimniho casu; fallback obsahuje datum 1970 a pristup k NTP datetime muze
jeste selhat. Pohyb je kumulativni za tick. Slots a blink jsou pocitadlove.
Novy obecny morph muze skocit z predchoziho ciloveho vyrazu. Tyto vlastnosti
neoznacujte jako opravene pouze tim, ze se kod prepise do C++.
