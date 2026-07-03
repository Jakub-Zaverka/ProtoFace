#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "generated_settings.h"
#include <esp_sleep.h>
#include <driver/gpio.h>

// Prihlasovaci udaje k Wi-Fi, ke ktere se ESP32 pripoji.
// Password je redundant, protože se k wifi nepřipojuje TODO:Odebrat
// Sit musi byt 2.4 GHz, protoze ESP32 nepodporuje 5 GHz Wi-Fi.
const char *WIFI_SSID = "NAZEV_WIFI";
const char *WIFI_PASSWORD = "HESLO_WIFI";



// MAC adresa prijimaci desky. - Matrix portálu S3
// Na tuto adresu bude tento program posilat zpravy pres ESP-NOW.
uint8_t receiverMac[] = {0x28, 0x37, 0x2F, 0xE0, 0xBC, 0x40};

// Struktura popisuje data, ktera se budou posilat prijimaci.
// Sender i receiver musi mit stejnou strukturu, jinak si data spatne prectou.
struct ControlMessage
{
    uint32_t counter;
    bool button1;
    bool button2;
    bool button3;
    bool button4;
};

static const gpio_num_t WAKE_D0 = GPIO_NUM_0;
static const gpio_num_t WAKE_D1 = GPIO_NUM_1;
static const gpio_num_t WAKE_D2 = GPIO_NUM_2;
static const gpio_num_t WAKE_D3 = GPIO_NUM_21;

static const unsigned long SLEEP_THRESHOLD_TIME = 30 * 1000; // 30s
static unsigned long last_input_time = 0;
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

// Neni potřeba se teď připojovat k wifi
// Neni použito v kódu
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

void enterLightSleep()
    {
        esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);

        gpio_wakeup_enable(WAKE_D0, GPIO_INTR_LOW_LEVEL);
        gpio_wakeup_enable(WAKE_D1, GPIO_INTR_LOW_LEVEL);
        gpio_wakeup_enable(WAKE_D2, GPIO_INTR_LOW_LEVEL);
        gpio_wakeup_enable(WAKE_D3, GPIO_INTR_LOW_LEVEL);

        esp_sleep_enable_gpio_wakeup();

        Serial.flush();
        esp_light_sleep_start();

        // Po probuzeni program pokracuje tady.
        gpio_wakeup_disable(WAKE_D0);
        gpio_wakeup_disable(WAKE_D1);
        gpio_wakeup_disable(WAKE_D2);
        gpio_wakeup_disable(WAKE_D3);
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

        bool esp_channel_set = false;
        WiFi.mode(WIFI_STA);

        for (int i = 0; i < networkCount; i++)
        {
            if (false)
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
            }

            if (!esp_channel_set && WiFi.SSID(i) == HOME_WIFI_SSID)
            {
                esp_wifi_set_channel(WiFi.channel(i), WIFI_SECOND_CHAN_NONE);
                Serial.print("Connected to:");
                Serial.println(WiFi.SSID(i));
                Serial.print("On channel:");
                Serial.println(WiFi.channel(i));
                esp_channel_set = true;
            }
            else if (!esp_channel_set && WiFi.SSID(i) == BACKUP_WIFI_SSID)
            {
                esp_wifi_set_channel(WiFi.channel(i), WIFI_SECOND_CHAN_NONE);
                Serial.print("Connected to:");
                Serial.println(WiFi.SSID(i));
                Serial.print("On channel:");
                Serial.println(WiFi.channel(i));
                esp_channel_set = true;
            }
            else if (!esp_channel_set)
            {
                // Zatim nic, rozhodneme az po kontrole vsech nalezenych siti.
            }
            else
            {
                // Nebo nalezen jiný channel
            }
        }

        if (!esp_channel_set)
        {
            Serial.println("No Known WIFI available");
        }
    }


    // inicializujeme ESP-NOW a pridame prijimaci desku jako peer.
    initEspNow();

    // Vychozi hodnoty zpravy pred prvnim odeslanim.
    msg.counter = 0;
    msg.button1 = false;
    msg.button2 = false;
    msg.button3 = false;
    msg.button4 = false;

    pinMode(D0, INPUT_PULLUP);
    pinMode(D1, INPUT_PULLUP);
    pinMode(D2, INPUT_PULLUP);
    pinMode(D3, INPUT_PULLUP);

    pinMode(LED_BUILTIN, OUTPUT);
    
    Serial.println("Setup done");

    last_input_time = millis();

    //Setup done led
    digitalWrite(LED_BUILTIN, LOW);
}


void loop()
{
    msg.button1 = false;
    msg.button2 = false;
    msg.button3 = false;
    msg.button4 = false;

    char debug_value = '\0';

    if (Serial.available() > 0)
    {
        debug_value = Serial.read();

        Serial.print("Prijal jsem znak: ");
        Serial.println(debug_value);
    }


    if (digitalRead(D0) == LOW || debug_value == 'w')
    {
        msg.button1 = true;
        esp_err_t result = esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
        if (result == ESP_OK)
        {
            Serial.print("Odeslano, counter = ");
            ++msg.counter;
            Serial.println(msg.counter);
            Serial.println("Up");
        }
        else
        {
            Serial.print("Chyba pri esp_now_send(): ");
            Serial.println(result);
        }
        last_input_time = millis();
    }
    else if (digitalRead(D1) == LOW || debug_value == 's')
    {
        msg.button2 = true;
        esp_err_t result = esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
        if (result == ESP_OK)
        {
            Serial.print("Odeslano, counter = ");
            ++msg.counter;
            Serial.println(msg.counter);
            Serial.println("Down");
        }
        else
        {
            Serial.print("Chyba pri esp_now_send(): ");
            Serial.println(result);
        }
        last_input_time = millis();
    }
    else if (digitalRead(D2) == LOW || debug_value == 'd')
    {
        msg.button3 = true;
        esp_err_t result = esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
        if (result == ESP_OK)
        {
            Serial.print("Odeslano, counter = ");
            ++msg.counter;
            Serial.println(msg.counter);
            Serial.println("Ok");
        }
        else
        {
            Serial.print("Chyba pri esp_now_send(): ");
            Serial.println(result);
        }
        last_input_time = millis();
    }
    else if (digitalRead(D3) == LOW || debug_value == 'a')
    {
        msg.button4 = true;
        esp_err_t result = esp_now_send(receiverMac, (uint8_t *)&msg, sizeof(msg));
        if (result == ESP_OK)
        {
            Serial.print("Odeslano, counter = ");
            ++msg.counter;
            Serial.println(msg.counter);
            Serial.println("Home");
        }
        else
        {
            Serial.print("Chyba pri esp_now_send(): ");
            Serial.println(result);
        }
        last_input_time = millis();
    }

    delay(100);

    if (millis() - last_input_time > SLEEP_THRESHOLD_TIME)
    {
        digitalWrite(LED_BUILTIN, HIGH);
        enterLightSleep();
        digitalWrite(LED_BUILTIN, LOW);
        last_input_time = millis();
    }
}
