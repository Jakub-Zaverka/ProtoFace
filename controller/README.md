# ProtoFace Controller

PlatformIO firmware for the ESP32 controller that sends OLED menu input to the
ProtoFace display board over ESP-NOW.

## Hardware

- Seeed Studio XIAO ESP32-C6
- Arduino framework through PlatformIO

## Controls

The controller sends this message:

```cpp
struct ControlMessage {
    uint32_t counter;
    bool button1; // up
    bool button2; // down
    bool button3; // ok
};
```

On the CircuitPython receiver:

- `button1` controls menu up / previous
- `button2` controls menu down / next
- `button3` confirms the selected item

## Configuration

Copy the example settings file and fill in local values:

```powershell
Copy-Item settings.example.toml settings.toml
```

`settings.toml` is ignored by git. During PlatformIO builds,
`scripts/generate_settings.py` generates `src/generated_settings.h` from it.

## Build And Upload

From this directory:

```powershell
pio run
pio run --target upload
pio device monitor
```
