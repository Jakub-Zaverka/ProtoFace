#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "generated_settings.h"

// Prihlasovaci udaje k Wi-Fi, ke ktere se ESP32 pripoji.
// Sit musi byt 2.4 GHz, protoze ESP32 nepodporuje 5 GHz Wi-Fi.
const char *WIFI_SSID = "NAZEV_WIFI";
const char *WIFI_PASSWORD = "HESLO_WIFI";

// MAC adresa prijimaci desky.
// Na tuto adresu bude tento program posilat zpravy pres ESP-NOW.
uint8_t receiverMac[] = {0x28, 0x37, 0x2F, 0xE0, 0xBC, 0x40};

// Struktura popisuje data, ktera se budou posilat prijimaci.
// Sender i receiver musi mit stejnou strukturu, jinak si data spatne prectou.
// struct ControlMessage
// {
//     // Pocitadlo odeslanych zprav. Hodi se pro kontrolu,
//     // jestli zpravy chodi ve spravnem poradi.
//     uint32_t counter;

//     // Ukazkove stavy tlacitek.
//     bool button1;
//     bool button2;

//     // Obecna ciselna hodnota. Tady se do ni uklada cteni z analogoveho pinu A0.
//     int value;
//     char debug;
// };

struct ControlMessage{
    uint32_t counter;
    bool button1;
    bool button2;
    bool button3;
};

// Globalni instance zpravy.
// Funkce loop() ji pred kazdym odeslanim upravi a posle receiveru.
ControlMessage msg;

// Callback funkce, kterou ESP-NOW zavola po kazdem pokusu o odeslani.
// Podle hodnoty status zjistime, jestli se zpravu povedlo predat.
// Tato signatura odpovida Arduino ESP32 Core 3.3.x / ESP-IDF 5+.
// void onDataSent(const esp_now_send_info_t* info, esp_now_send_status_t status)
// {
//     Serial.print("ESP-NOW send status: ");

//     if (status == ESP_NOW_SEND_SUCCESS)
//     {
//         Serial.println("OK");
//     }
//     else
//     {
//         Serial.println("FAIL");
//     }
// }

void connectToWiFi(const char *ssid, const char *password)
{
    Serial.println();
    Serial.print("Pripojuji se k Wi-Fi: ");
    Serial.println(ssid);

    // ESP32 bude fungovat jako Wi-Fi klient.
    // To je dulezite i pro ESP-NOW, protoze peer se pozdeji navaze na station interface.
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    // Ceka, dokud se deska nepripoji k routeru.
    // Kazdych 500 ms vypise tecku, aby bylo videt, ze program stale bezi.
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    // Po uspesnem pripojeni vypise diagnosticke informace.
    Serial.println();
    Serial.println("Wi-Fi pripojeno");
    Serial.print("IP adresa: ");
    Serial.println(WiFi.localIP());

    Serial.print("MAC adresa senderu: ");
    Serial.println(WiFi.macAddress());

    Serial.print("Wi-Fi kanal: ");
    Serial.println(WiFi.channel());

    // Vypne usporny rezim Wi-Fi.
    // Pro ovladani a rychle reakce je lepsi nizsi latence nez uspora energie.
    // esp_wifi_set_ps(WIFI_PS_NONE);
}

void initEspNow()
{
    // Inicializuje ESP-NOW. Bez toho nelze pridavat peery ani posilat zpravy.
    if (esp_now_init() != ESP_OK)
    {
        Serial.println("Chyba: esp_now_init() selhalo");
        return;
    }

    Serial.println("ESP-NOW inicializovano");

    // Registruje callback, ktery se zavola po odeslani zpravy.
    // esp_now_register_send_cb(onDataSent);

    // Nastaveni prijimace, kteremu budeme posilat data.
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, receiverMac, 6);

    // Hodnota 0 znamena: pouzij aktualni Wi-Fi kanal.
    // Protoze uz jsme pripojeni k routeru, pouzije se kanal routeru.
    peerInfo.channel = 0;

    // Posilame pres station interface, protoze deska bezi jako Wi-Fi klient.
    peerInfo.ifidx = WIFI_IF_STA;

    // Sifrovani je zatim vypnute.
    peerInfo.encrypt = false;

    // Prida receiver do seznamu ESP-NOW zarizeni, kterym smime posilat data.
    if (esp_now_add_peer(&peerInfo) != ESP_OK)
    {
        Serial.println("Chyba: nepodarilo se pridat ESP-NOW peer");
        return;
    }

    Serial.println("Receiver pridan jako ESP-NOW peer");
}

void setup()
{
    // Spusti seriovou linku pro vypisy do monitoru.
    Serial.begin(115200);

    // Kratke cekani, aby se seriovy monitor stihl pripojit po startu desky.
    delay(2000);

    WiFi.scanNetworks();
    WiFi.disconnect();

    int networkCount = WiFi.scanNetworks();

    if (networkCount == 0)
    {
        Serial.println("Nenalezeny zadne site.");
    }
    else
    {
        Serial.print("Nalezeno siti: ");
        Serial.println(networkCount);

        for (int i = 0; i < networkCount; i++)
        {
            Serial.print(i + 1);
            Serial.print(": ");

            Serial.print(WiFi.SSID(i));
            Serial.print(" | signal: ");
            Serial.print(WiFi.RSSI(i));
            Serial.print(" dBm");

            Serial.print(" | kanal: ");
            Serial.print(WiFi.channel(i));

            Serial.print(" | sifrovani: ");
            Serial.println(WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "open" : "secured");

            delay(10);

            if (WiFi.status() != WL_CONNECTED && WiFi.SSID(i) == HOME_WIFI_SSID)
            {
                connectToWiFi(HOME_WIFI_SSID, HOME_WIFI_PASSWORD);
            }
            else if (WiFi.status() != WL_CONNECTED && WiFi.SSID(i) == BACKUP_WIFI_SSID)
            {
                connectToWiFi(BACKUP_WIFI_SSID, BACKUP_WIFI_PASSWORD);
            }
            else if (WiFi.status() != WL_CONNECTED)
            {
                Serial.println("No WIFI available");
            }
            else
            {
                // Připojeno k jiné WiFi síti
            }
        }
    }

    // Nejdriv se pripojime k Wi-Fi, aby ESP-NOW pouzil stejny kanal jako router.
    // connectToWiFi();

    // Potom inicializujeme ESP-NOW a pridame prijimaci desku jako peer.
    initEspNow();

    // Vychozi hodnoty zpravy pred prvnim odeslanim.
    msg.counter = 0;
    msg.button1 = false;
    msg.button2 = false;
    msg.button2 = false;

    Serial.println("Setup done");
}

// void loop()
// {
//     // Pri kazdem pruchodu zvysi pocitadlo odeslanych zprav.
//     msg.counter++;

//     // Testovaci zmena hodnoty button1: pri kazdem odeslani se prepne true/false.
//     msg.button1 = !msg.button1;

//     // Druhe tlacitko je zatim vzdy vypnute.
//     msg.button2 = false;

//     // Do zpravy se ulozi aktualni analogova hodnota z pinu A0.
//     // Pozdeji se sem muze dat treba hodnota joysticku, potenciometru nebo senzoru.
//     msg.value = analogRead(A0);

//     // Odesle celou strukturu msg na MAC adresu receiveru.
//     // Pretypovani na uint8_t* rika funkci, ze ma strukturu poslat jako blok bajtu.
//     esp_err_t result = esp_now_send(receiverMac, (uint8_t*)&msg, sizeof(msg));

//     // esp_now_send() vraci jen informaci, jestli se zpravu podarilo zaradit k odeslani.
//     // Skutecny vysledek odeslani vypise callback onDataSent().
//     if (result == ESP_OK)
//     {
//         Serial.print("Odeslano, counter = ");
//         Serial.println(msg.counter);
//     }
//     else
//     {
//         Serial.print("Chyba pri esp_now_send(): ");
//         Serial.println(result);
//     }

//     // Posila jednu zpravu za sekundu.
//     delay(1000);
// }

void loop()
{
    // Serial.println(WiFi.localIP());

    msg.button1 = false;
    msg.button2 = false;
    msg.button3 = false;
    
    char debug_value;

    if (Serial.available() > 0)
    {
        debug_value = Serial.read();

        Serial.print("Prijal jsem znak: ");
        Serial.println(debug_value);
    }

    if (analogRead(A0) == HIGH || debug_value == 'w')
    {
        msg.button1 = true;
        esp_err_t result = esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
        if (result == ESP_OK)
        {
            Serial.print("Odeslano, counter = ");
            ++msg.counter;
            Serial.println(msg.counter);
        }
        else
        {
            Serial.print("Chyba pri esp_now_send(): ");
            Serial.println(result);
        }
    }
    else if (analogRead(A1) == HIGH || debug_value == 's')
    {
        msg.button2 = true;
        esp_err_t result = esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
        if (result == ESP_OK)
        {
            Serial.print("Odeslano, counter = ");
            ++msg.counter;
            Serial.println(msg.counter);
        }
        else
        {
            Serial.print("Chyba pri esp_now_send(): ");
            Serial.println(result);
        }
    }
    else if (analogRead(A2) == HIGH || debug_value == 'd')
    {
        msg.button3 = true;
        esp_err_t result = esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
        if (result == ESP_OK)
        {
            Serial.print("Odeslano, counter = ");
            ++msg.counter;
            Serial.println(msg.counter);
        }
        else
        {
            Serial.print("Chyba pri esp_now_send(): ");
            Serial.println(result);
        }
    }

    delay(100);
}