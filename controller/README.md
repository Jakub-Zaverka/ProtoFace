# ProtoFace Controller

Technicka dokumentace firmware pro externi ESP32 ovladac. Controller bezi na
`Seeed Studio XIAO ESP32-C6`, cte ctyri tlacitka a posila jejich stav do
MatrixPortal S3 pres ESP-NOW.

## Hardware

- deska: `Seeed Studio XIAO ESP32-C6`
- framework: Arduino pres PlatformIO
- tlacitka: `D0`, `D1`, `D2`, `D3`
- komunikace: ESP-NOW na stejnem Wi-Fi kanalu jako MatrixPortal S3
- serial monitor: `115200`

Tlacitka pouzivaji `INPUT_PULLUP`, stisk tedy spoji pin na `GND`.

## Ovladani

Mapovani fyzickych tlacitek:

- `D0` -> `Up`
- `D1` -> `Down`
- `D2` -> `Ok`
- `D3` -> `Home` / `Back`

Stejne akce jde posilat i ze serial monitoru:

- `w` -> `Up`
- `s` -> `Down`
- `d` -> `Ok`
- `a` -> `Home` / `Back`

Opakovane odeslani stejneho tlacitka je blokovane na
`BUTTON_REPEAT_BLOCK_MS = 400`, aby jeden stisk neposlal vice prikazu.

## ESP-NOW zprava

Controller posila tuto strukturu:

```cpp
struct ControlMessage {
    uint32_t counter;
    bool button1; // up / previous
    bool button2; // down / next
    bool button3; // ok / confirm
    bool button4; // home / back
};
```

Na CircuitPython receiveru se zprava dekoduje v `src/code.py`:

- `button1` -> `prev`
- `button2` -> `next`
- `button3` -> `confirm`
- `button4` -> `back`

Receiver aktualne akceptuje 7b i 8b variantu zpravy, aby zustala kompatibilita
se starsim firmwarem bez `button4`.

## Wi-Fi kanal

ESP-NOW musi bezet na stejnem Wi-Fi kanalu jako prijimaci MatrixPortal S3.
Controller se k routeru neprihlasuje natrvalo; pri startu provede scan siti,
nejdrive zkusi `BACKUP_WIFI_SSID`, potom `HOME_WIFI_SSID` a nastavi radio na
kanal nalezene site pres `esp_wifi_set_channel(...)`.

Pokud controller zadnou znamou sit nenajde, vypise `No Known WIFI available`.
ESP-NOW peer se presto inicializuje, ale komunikace bude fungovat jen pokud je
radio nahodou na stejnem kanalu jako receiver.

MAC adresa MatrixPortal S3 je nastavena v `controller/src/main.cpp`:

```cpp
uint8_t receiverMac[] = {0x28, 0x37, 0x2F, 0xE0, 0xBC, 0x40};
```

Pri zmene prijimaci desky je potreba tuto adresu upravit. MatrixPortal si umi
svoji MAC vypsat v `src/code.py` u `wifi.radio.mac_address`.

## Konfigurace

Zkopiruj priklad konfigurace:

```powershell
Copy-Item settings.example.toml settings.toml
```

Pouzivane hodnoty:

```toml
HOME_WIFI_SSID = ""
HOME_WIFI_PASSWORD = ""

BACKUP_WIFI_SSID = ""
BACKUP_WIFI_PASSWORD = ""

DEVICE_HOSTNAME = "protogen-controller"
```

`settings.toml` se necommituje. Pri buildu PlatformIO spusti
`scripts/generate_settings.py`, ktery z nej vytvori
`src/generated_settings.h`.

## Build a upload

Z adresare `controller/`:

```powershell
pio run
pio run --target upload
pio device monitor
```

Z korene repozitare jde pouzit helper:

```powershell
.\deploy_xiao.ps1
```

## Typicke problemy

- Controller posila, ale MatrixPortal nereaguje
  - over, ze `receiverMac` odpovida MAC adrese MatrixPortal S3
  - over, ze controller nasel stejnou Wi-Fi sit a nastavil spravny kanal
  - over, ze MatrixPortal ma zapnutou Wi-Fi a vytvoreny `espnow.ESPNow()`

- Tlacitko posle akci opakovane
  - zkontroluj zapojeni na `GND`
  - zvys `BUTTON_REPEAT_BLOCK_MS`

- Build selze na `generated_settings.h`
  - zkopiruj `settings.example.toml` na `settings.toml`
  - zkontroluj, ze mas nainstalovane PlatformIO a dostupny prikaz `pio`
