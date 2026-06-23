#pragma once

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "hud_navigation.h"

// namespace je "jmenna oblast".
// Pomaha seskupit souvisejici veci pod jedno jmeno, tady Hud.
// Diky tomu se funkce jmenuje Hud::begin() misto jen begin().
// Operator :: znamena "najdi vec uvnitr tohoto namespace/tridy".
// Python podobnost: namespace Hud je trochu jako modul hud.py
// a Hud::begin() je podobne jako zavolat hud.begin().
namespace Hud
{
    // static constexpr znamena "konstanta znama uz pri prekladu programu".
    // static tady rika, ze hodnota patri jen do tohoto souboru/namespace pouziti.
    // constexpr rika, ze se hodnota nemeni a prekladac ji muze pouzit jako pevnou konstantu.
    // int je cele cislo.
    // Python podobnost: je to jako napsat SCREEN_WIDTH = 128,
    // ale v C++ navic rikas typ hodnoty a ze je to skutecna konstanta pri prekladu.
    static constexpr int SCREEN_WIDTH = 128;
    static constexpr int SCREEN_HEIGHT = 64;

    // OLED_RESET = -1 znamena, ze displej nema samostatny reset pin pripojeny k MCU.
    // Python podobnost: -1 se casto pouziva jako specialni hodnota "neni nastaveno".
    static constexpr int OLED_RESET = -1;

    // uint8_t je unsigned 8-bit integer: cele cislo bez znamenka v rozsahu 0 az 255.
    // I2C adresy jsou male hodnoty, proto se sem uint8_t hodi.
    // 0x3C je hexadecimalni zapis cisla, bezna I2C adresa SSD1306 displeju.
    // Python podobnost: v Pythonu bys napsal OLED_ADDRESS = 0x3C.
    // Python int nema pevnou velikost, C++ uint8_t ma presne 8 bitu.
    static constexpr uint8_t OLED_ADDRESS = 0x3C;

    // Funkce display() vraci referenci na jeden objekt displeje.
    // Adafruit_SSD1306 & znamena "reference na Adafruit_SSD1306", tedy ne kopie objektu.
    // Reference se chova podobne jako alias na existujici objekt.
    // Python podobnost: v Pythonu se objekty bezne predavaji odkazem automaticky.
    // V C++ musis casteji explicitne rict, jestli chces kopii, pointer nebo referenci.
    static Adafruit_SSD1306 &display()
    {
        // static uvnitr funkce znamena, ze se objekt vytvori jen jednou
        // a prezije po celou dobu behu programu.
        // Python podobnost: je to trochu jako globalni promenna vytvorena az pri prvnim volani funkce.
        static Adafruit_SSD1306 instance(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
        return instance;
    }

    // bool je logicka hodnota: true nebo false.
    // begin() pripravi I2C a pokusi se inicializovat OLED displej.
    // Python podobnost: bool funguje podobne, jen Python pise True/False s velkym pismenem.
    static bool begin()
    {
        // Wire je Arduino objekt pro I2C komunikaci.
        // Wire.begin() zapne I2C na vychozich SDA/SCL pinech desky.
        // Python podobnost v CircuitPythonu by byla treba busio.I2C(scl, sda).
        Wire.begin();

        // display().begin(...) vola metodu begin na objektu displeje.
        // Tecka . znamena "zavolej funkci nebo pristup k hodnote na objektu".
        // Python podobnost: object.method() vypada stejne, treba display.begin(...).
        return display().begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
    }

    // void znamena, ze funkce nic nevraci.
    // clear() smaze framebuffer displeje a nastavi zakladni styl textu.
    // Python podobnost: funkce bez return vraci automaticky None.
    // V C++ se to pise dopredu jako void.
    static void clear()
    {
        display().clearDisplay();
        display().setTextSize(1);
        display().setTextColor(SSD1306_WHITE);
        display().setCursor(0, 0);
    }

    // smaže část displeje
    // int start_x, int start_y, int end_x, int end_y
    static void clearPart(int start_x, int start_y, int end_x, int end_y)
    {
        display().fillRect(start_x, start_y, end_x, end_y, SSD1306_BLACK);
        display().display();
    }

    // Tato funkce vykresli jednoduchou testovaci obrazovku.
    // Vetsina metod nejdrive meni pametovy obraz displeje.
    // Skutecne odeslani na OLED probehne az pri display().display().
    // Python podobnost: je to jako kdyz v knihovne nejdriv kreslis do bufferu
    // a pak zavolas show() nebo display() pro prekresleni fyzicke obrazovky.
    // static void showTestScreen()
    // {
    //     clear();
    //     display().println("SSD1306 TEST");
    //     display().println();
    //     display().println("Matrix Portal S3");
    //     display().println("PlatformIO + C++");
    //     display().display();
    // }

    // update() je pripravene misto pro budouci pravidelne prekreslovani HUDu.
    // Volame ji z loop(), i kdyz zatim nic nedela.
    // Python podobnost: obsah while True smycky by casto volal update() porad dokola.
    static void update()
    {
        clear();

        HudNavigation::State &state = HudNavigation::getState();

        display().println(state.name);
        display().println();

        for (int i = 0; i < state.childCount; i++)
        {
            if (i == state.selectedIndex)
            {
                display().print("> ");
            }
            else
            {
                display().print("  ");
            }

            display().println(state.children[i]->name);
        }

        display().display();
    }

    static void showStatus(const String &message = "")
    {
        if (message != "")
        {
            clear();
            display().println(message);
            display().display();
        }
    }

    // const char * je ukazatel na textovy retezec, ktery funkce nebude menit.
    // V Arduino/C++ se takhle casto predavaji jednoduche texty jako "SSD1306 not found".
    // Python podobnost: v Pythonu by argument byl proste str, treba def halt(message: str).
    // V C++ je textovy retezec na nizke urovni casto pointer na znaky.
    static void halt(const char *message)
    {
        Serial.println(message);

        // Nekonecna smycka. Pouziva se tady, kdyz bez displeje nechceme pokracovat.
        // Python podobnost: while True: time.sleep(1)
        while (true)
        {
            delay(1000);
        }
    }
}
