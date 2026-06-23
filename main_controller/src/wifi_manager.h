#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include "secrets.h"

// Tento soubor je dummy priklad pripojeni ESP32-S3 k Wi-Fi.
// SSID a heslo si zmen na svoji 2.4 GHz Wi-Fi.
// ESP32 obecne nepodporuje 5 GHz Wi-Fi site.
namespace Wifi
{
    // const char * je C/C++ zapis textu.
    // Python podobnost: WIFI_SSID = "NAZEV_WIFI"
    static const char *WIFI_SSID = HOME_WIFI_SSID;
    static const char *WIFI_PASSWORD = HOME_WIFI_PASSWORD;

    static const char *BACKUP_SSID = BACKUP_WIFI_SSID;
    static const char *BACKUP_PASSWORD = BACKUP_WIFI_PASSWORD;

    // unsigned long je cele cislo bez znamenka.
    // millis() vraci cas od startu desky v milisekundach.
    static unsigned long lastStatusPrintMs = 0;

    // Funkce vrati true, kdyz je deska aktualne pripojena k Wi-Fi.
    // Python podobnost: def is_connected() -> bool:
    static bool isConnected()
    {
        return WiFi.status() == WL_CONNECTED;
    }

    static String status()
    {
        if (isConnected())
        {
            return String("Wi-Fi connected\nIP address: ") +
                   WiFi.localIP().toString() +
                   "\nMAC address: " +
                   WiFi.macAddress();
        }

        return "Wi-Fi disconnected";
    }

    static bool tryConnect(const char *ssid, const char *password, unsigned long timeoutMs)
    {

        Serial.print("Connecting to Wi-Fi: ");
        Serial.println(ssid);

        WiFi.disconnect(true);
        delay(200);
        WiFi.begin(ssid, password);

        const unsigned long startMs = millis();

        while (!isConnected() && millis() - startMs < timeoutMs)
        {
            Serial.print(".");
            delay(500);
        }

        Serial.println();
        return isConnected();
    }

    // connect() spusti pripojeni k Wi-Fi a chvili ceka na vysledek.
    // WiFi.begin(...) je Arduino/ESP32 obdoba "zacni se pripojovat k teto siti".
    static void connect()
    {
        // WIFI_STA znamena station mode: deska se chova jako klient,
        // podobne jako notebook nebo telefon pripojeny k routeru.
        WiFi.mode(WIFI_STA);

        const unsigned long timeoutMs = 15000;

        int wifi_count = WiFi.scanNetworks();
        Serial.print("Found Wi-Fi networks: ");
        Serial.println(wifi_count);

        for (int i = 0; i < wifi_count; i++)
        {
            Serial.print(" - ");
            Serial.println(WiFi.SSID(i));

            if (WiFi.SSID(i) == WIFI_SSID)
            {
                tryConnect(WIFI_SSID, WIFI_PASSWORD, timeoutMs);
            }
            else if (WiFi.SSID(i) == BACKUP_SSID)
            {
                tryConnect(BACKUP_SSID, BACKUP_PASSWORD, timeoutMs);
            }
        }

        if (isConnected())
        {
            Serial.println("Wi-Fi connected");
            Serial.print("IP address: ");
            Serial.println(WiFi.localIP());
            Serial.print("MAC address: ");
            Serial.println(WiFi.macAddress());
        }
        else
        {
            Serial.println("Wi-Fi connection failed");
        }
    }

    // update() ukazuje priklad pravidelne kontroly stavu ve smycce loop().
    // Kazdych 5 sekund vypise, jestli je Wi-Fi pripojena.
    static void update()
    {
        const unsigned long now = millis();

        if (now - lastStatusPrintMs < 30000)
        {
            return;
        }

        lastStatusPrintMs = now;

        if (isConnected())
        {
            Serial.print("Wi-Fi OK, RSSI: ");
            Serial.print(WiFi.RSSI());
            Serial.println(" dBm");
        }
        else
        {
            Serial.println("Wi-Fi disconnected");
        }
    }
}
