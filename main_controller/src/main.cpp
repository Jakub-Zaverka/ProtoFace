#include <Arduino.h>
#include "hud.h"
#include "wifi_manager.h"

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println();

    if (!Hud::begin())
    {
        Hud::halt("SSD1306 not found");
    }

    Hud::showTestScreen();
    Hud::clearPart(0,0,16,8);

    Wifi::connect();
}

void loop()
{
    Wifi::update();
    Hud::showStatus(Wifi::status());
}
