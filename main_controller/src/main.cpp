#include <Arduino.h>
#include "hud.h"
#include "hud_navigation.h"
#include "wifi_manager.h"

static constexpr int BUTTON_UP_PIN = PIN_BUTTON_UP;
static constexpr int BUTTON_DOWN_PIN = PIN_BUTTON_DOWN;
static constexpr int BUTTON_SELECT_PIN = A0;

static bool lastUpPressed = false;
static bool lastDownPressed = false;
static bool lastSelectPressed = false;

static bool isPressed(int pin)
{
    return digitalRead(pin) == LOW;
}

static void updateButtons()
{
    const bool upPressed = isPressed(BUTTON_UP_PIN);
    const bool downPressed = isPressed(BUTTON_DOWN_PIN);
    const bool selectPressed = isPressed(BUTTON_SELECT_PIN);

    if (upPressed && !lastUpPressed)
    {
        HudNavigation::moveUp();
    }

    if (downPressed && !lastDownPressed)
    {
        HudNavigation::moveDown();
    }

    if (selectPressed && !lastSelectPressed)
    {
        HudNavigation::select();
    }

    lastUpPressed = upPressed;
    lastDownPressed = downPressed;
    lastSelectPressed = selectPressed;
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println();

    if (!Hud::begin())
    {
        Hud::halt("SSD1306 not found");
    }

    pinMode(BUTTON_UP_PIN, INPUT_PULLUP);
    pinMode(BUTTON_DOWN_PIN, INPUT_PULLUP);
    pinMode(BUTTON_SELECT_PIN, INPUT_PULLUP);

    HudNavigation::begin();
    Wifi::connect();
}

void loop()
{
    updateButtons();
    Wifi::update();
    Hud::update();
}
