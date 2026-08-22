"""Program ridi cely runtime obliceje, menu, senzoru, Wi-Fi a HTTP ovladani."""

# Importy vsech modulu, ktere hlavni runtime propojuje.
import microcontroller
import os
import time
import adafruit_logging as logging
import display as display_module
from display import Display
from accelerometer import Accelerometer
from mic import Microphone
from I2C_sim import APDSSensor
from I2C_sim import cycle_oled_font_scale
from I2C_sim import get_oled_font_scale_count
from I2C_sim import get_oled_font_scale_index
from I2C_sim import get_oled_font_scale_label
from I2C_sim import OLEDDisplay
from I2C_sim import set_oled_font_scale_index
import board
import digitalio
from wifi_network import Wifi
from clock import Clock
import emotes
from UI import EVENT_SETTING_SELECTED
from UI import SCREEN_DEBUG_MENU
from UI import UI
from server import ServerClass
from performance import PerformanceMonitor
import espnow
import struct
import pwmio

# Identifikator a mapa bitu pro ulozeni runtime voleb do `microcontroller.nvm`.
NVM_MAGIC = b"PFS4"
OLD_NVM_MAGIC = b"PFS3"
LEGACY_NVM_MAGIC = b"PFS1"
NVM_FLAG_BYTES = 2
NVM_VALUE_BYTES = 3
LOG_BUFFER_SIZE = 100
DEBUG_UI_UPDATE_INTERVAL = 1.0
WIFI_RETRY_SETTINGS = {
    # "Wifi Main": "main",
    # "Wifi Backup": "backup",
}
BOOP_AUTO_TUNE_WINDOW = 1.0
BOOP_SPIKE_MARGIN = 15
BOOP_MAX_THRESHOLD = 255
BOOP_SAMPLE_FREEZE_AFTER_SPIKE = 1.0
SETTING_ENV_KEYS = {
    "Accelerometer": "ACCELEROMETER_ON",
    "Boop": "APDS_ON",
    "Boop Rainbow": "BOOP_RAINBOW_ON",
    "Rainbow Override": "RAINBOW_OVERRIDE_ON",
    "Blink": "BLINK_ON",
    "Smooth Transitions": "SMOOTH_TRANSITIONS_ON",
    "Wifi_Connect": "WIFI_CONNECT_ON",
    "Wifi_Broadcast": "WIFI_BROADCAST_ON",
    "Verbose": "VERBOSE",
    "Mic": "MIC_ON",
    "Display": "DISPLAY_ON"
}
SETTING_BITS = {
    "ACCELEROMETER_ON": 0,
    "MIC_ON": 1,
    "APDS_ON": 2,
    "WIFI_ON": 3,
    "VERBOSE": 4,
    "BLINK_ON": 5,
    "DISPLAY_ON": 6,
    "BOOP_RAINBOW_ON": 7,
    "RAINBOW_OVERRIDE_ON": 8,
    "WIFI_CONNECT_ON": 9,
    "WIFI_BROADCAST_ON": 10,
    "SMOOTH_TRANSITIONS_ON": 11,
}
VALUE_SETTING_KEYS = (
    "BRIGHTNESS_INDEX",
    "OLED_FONT_SCALE_INDEX",
    "FAN_SPEED_INDEX",
)

MIN_MOVEMENT = 1

# Globalni runtime stav. Jednotlive periferie se inicializuji jen pokud jsou zapnute.
accelerometer = None
mic = None
apds = None
wifi = None
esp = None
device_clock = None
oled = None
display = None
face_emotes = None
nose_matrix = None
eye_matrix = None
mouth_matrix = None
whole_matrix = None
nose_matrix_right = None
eye_matrix_right = None
mouth_matrix_right = None
whole_matrix_right = None
sys_log = []
logger = None
server = None
ui = None
perf = None
boop_threshold_tracker = None
boop_threshold = emotes.BOOP_PROXIMITY_THRESHOLD
fan_pwm = None
FAN_SPEED_STEPS = (0, 50, 100)
FAN_SPEED_PERCENT = 0


class BoopThresholdTracker:
    """Detekuje boop jako nahly narust proti poslednim namerenym hodnotam."""

    def __init__(
        self,
        window_seconds=BOOP_AUTO_TUNE_WINDOW,
        spike_margin=BOOP_SPIKE_MARGIN,
        fallback_threshold=emotes.BOOP_PROXIMITY_THRESHOLD,
        freeze_after_spike=BOOP_SAMPLE_FREEZE_AFTER_SPIKE,
    ):
        self.window_seconds = window_seconds
        self.spike_margin = spike_margin
        self.fallback_threshold = fallback_threshold
        self.freeze_after_spike = freeze_after_spike
        self.samples = []
        self.threshold = fallback_threshold
        self.freeze_until = 0.0

    def update(self, value, now=None, freeze=False):
        """Vrati threshold a vzorkuje jen hodnoty mimo aktivni boop."""
        if now is None:
            now = time.monotonic()

        if value is None:
            self._trim(now)
            return self.threshold

        value = int(value)
        frozen = freeze or now < self.freeze_until
        if not frozen:
            self._trim(now)

        self.threshold = self._calculate_threshold()
        if frozen:
            return self.threshold

        if value > self.threshold:
            self.freeze_until = now + self.freeze_after_spike
            return self.threshold

        self.samples.append((now, value))
        return self.threshold

    def calibrate(self, value=None):
        """Resetuje automaticky threshold podle aktualni proximity hodnoty."""
        self.samples = []
        self.freeze_until = 0.0
        if value is None:
            self.threshold = self.fallback_threshold
        else:
            self.threshold = min(BOOP_MAX_THRESHOLD, int(value) + self.spike_margin)
        return self.threshold

    def _trim(self, now):
        oldest_allowed = now - self.window_seconds
        while self.samples and self.samples[0][0] < oldest_allowed:
            self.samples.pop(0)

    def _calculate_threshold(self):
        if not self.samples:
            return self.threshold

        baseline = sum(sample[1] for sample in self.samples) // len(self.samples)
        return min(BOOP_MAX_THRESHOLD, baseline + self.spike_margin)


class ListHandler(logging.Handler):
    """Uklada posledni log zaznamy do seznamu pro pozdejsi zobrazeni."""

    def __init__(self, storage, max_items=LOG_BUFFER_SIZE):
        super().__init__()
        self.storage = storage
        self.max_items = max_items

    def emit(self, record):
        self.storage.append(str(record.msg))
        if self.max_items is not None and len(self.storage) > self.max_items:
            del self.storage[:-self.max_items]


def load_runtime_settings():
    """Nacte ulozene runtime volby z `microcontroller.nvm`."""
    # Prvni byty NVM obsahuji hlavicku, bitove pole prepinacu a hodnotove indexy.
    if len(microcontroller.nvm) < len(NVM_MAGIC) + 1:
        return {}

    raw_length = len(NVM_MAGIC) + NVM_FLAG_BYTES + NVM_VALUE_BYTES
    raw = bytes(microcontroller.nvm[:raw_length])
    magic = raw[: len(NVM_MAGIC)]
    if magic == NVM_MAGIC:
        flag_bytes = raw[len(NVM_MAGIC): len(NVM_MAGIC) + NVM_FLAG_BYTES]
        value_bytes = raw[
            len(NVM_MAGIC) + NVM_FLAG_BYTES:
            len(NVM_MAGIC) + NVM_FLAG_BYTES + NVM_VALUE_BYTES
        ]
    elif magic == OLD_NVM_MAGIC:
        flag_bytes = raw[len(OLD_NVM_MAGIC): len(OLD_NVM_MAGIC) + NVM_FLAG_BYTES]
        value_bytes = b""
    elif magic == LEGACY_NVM_MAGIC:
        flag_bytes = raw[len(LEGACY_NVM_MAGIC): len(LEGACY_NVM_MAGIC) + 1]
        value_bytes = b""
    else:
        return {}

    runtime_settings = {}
    for setting_key, bit_index in SETTING_BITS.items():
        byte_index = bit_index // 8
        if byte_index >= len(flag_bytes):
            continue
        flags = flag_bytes[byte_index]
        runtime_settings[setting_key] = bool(flags & (1 << (bit_index % 8)))

    for offset, setting_key in enumerate(VALUE_SETTING_KEYS):
        if offset < len(value_bytes):
            runtime_settings[setting_key] = int(value_bytes[offset])
    return runtime_settings


def read_bool_setting(name, default):
    """Precte jeden boolean z runtime pameti, `settings.toml` nebo fallbacku."""
    # Prioritu ma hodnota ulozena za behu pres OLED menu.
    value = RUNTIME_SETTINGS.get(name)
    if value is not None:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() == "true"

    try:
        value = os.getenv(name)
    except (ValueError, TypeError):
        return default

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() == "true"


def read_index_setting(name, default, max_exclusive):
    """Precte ulozeny index a vrati fallback pri hodnote mimo rozsah."""
    try:
        value = int(RUNTIME_SETTINGS.get(name, default))
    except (TypeError, ValueError):
        return default

    if value < 0 or value >= max_exclusive:
        return default
    return value


RUNTIME_SETTINGS = load_runtime_settings()

# Vychozi konfigurace runtime vznikne spojenim persistentnich voleb a `settings.toml`.
ACCELEROMETER_ON = read_bool_setting("ACCELEROMETER_ON", True)
MIC_ON = read_bool_setting("MIC_ON", True)
MIC_READ_ON = True
APDS_ON = read_bool_setting("APDS_ON", True)
SSD1306_ON = read_bool_setting("SSD1306_ON", True)
WIFI_CONNECT_ON = read_bool_setting("WIFI_CONNECT_ON", False)
WIFI_BROADCAST_ON = read_bool_setting("WIFI_BROADCAST_ON", True)
WIFI_ON = WIFI_CONNECT_ON or WIFI_BROADCAST_ON
VERBOSE = read_bool_setting("VERBOSE", False)
BLINK_ON = read_bool_setting("BLINK_ON", True)
SMOOTH_TRANSITIONS_ON = read_bool_setting("SMOOTH_TRANSITIONS_ON", False)
DISPLAY_ON = read_bool_setting("DISPLAY_ON", True)
BOOP_RAINBOW_ON = read_bool_setting("BOOP_RAINBOW_ON", True)
RAINBOW_OVERRIDE_ON = read_bool_setting("RAINBOW_OVERRIDE_ON", False)
RUNTIME_SETTINGS.update({
    "ACCELEROMETER_ON": ACCELEROMETER_ON,
    "MIC_ON": MIC_ON,
    "APDS_ON": APDS_ON,
    "WIFI_ON": WIFI_ON,
    "WIFI_CONNECT_ON": WIFI_CONNECT_ON,
    "WIFI_BROADCAST_ON": WIFI_BROADCAST_ON,
    "VERBOSE": VERBOSE,
    "BLINK_ON": BLINK_ON,
    "SMOOTH_TRANSITIONS_ON": SMOOTH_TRANSITIONS_ON,
    "DISPLAY_ON": DISPLAY_ON,
    "BOOP_RAINBOW_ON": BOOP_RAINBOW_ON,
    "RAINBOW_OVERRIDE_ON": RAINBOW_OVERRIDE_ON,
})
display_module.set_brightness_scale_index(
    read_index_setting(
        "BRIGHTNESS_INDEX",
        display_module.get_brightness_scale_index(),
        len(display_module.BRIGHTNESS_STEPS),
    )
)
set_oled_font_scale_index(
    read_index_setting(
        "OLED_FONT_SCALE_INDEX",
        get_oled_font_scale_index(),
        get_oled_font_scale_count(),
    )
)
RUNTIME_SETTINGS.update({
    "BRIGHTNESS_INDEX": display_module.get_brightness_scale_index(),
    "OLED_FONT_SCALE_INDEX": get_oled_font_scale_index(),
    "FAN_SPEED_INDEX": read_index_setting("FAN_SPEED_INDEX", 0, len(FAN_SPEED_STEPS)),
})
FAN_SPEED_PERCENT = FAN_SPEED_STEPS[RUNTIME_SETTINGS["FAN_SPEED_INDEX"]]

logger = logging.getLogger("runtime")
logger.setLevel(logging.INFO)
logger.addHandler(ListHandler(sys_log))


def start_network_services():
    """Spusti mDNS inzerci a HTTP server pro aktivni Wi-Fi pripojeni."""
    global server

    if wifi is None:
        raise RuntimeError("Wi-Fi must be initialized before starting services")

    wifi.advertise_http(80)
    if server is None:
        server = ServerClass(wifi)
    if ui is not None:
        server.set_menu_action_handler(handle_http_menu_action)
        server.set_menu_snapshot(refresh_ui_snapshot(ui))
    server.set_time_handler(handle_http_time_sync)
    if perf is not None:
        server.set_performance_provider(get_performance_snapshot)
    print("HTTP server available at {}".format(wifi.base_url(80)))
    print("HTTP server available at {}".format(wifi.ip_url(80)))


def stop_network_services():
    """Zastavi HTTP server, pokud bezi."""
    global server

    if server is not None:
        try:
            server.server.stop()
        except Exception as error:
            if VERBOSE:
                print(f"Failed to stop HTTP server: {error}")
        server = None


def ensure_espnow():
    """Inicializuje ESP-NOW jen jednou."""
    global esp

    if esp is None:
        esp = espnow.ESPNow()
        if wifi is not None:
            mac = wifi.radio.mac_address
            # print("uint8_t receiverMac[] = {%s};" % ", ".join(["0x%02X" % b for b in mac]))


def is_wifi_connected():
    """Vrati `True`, kdyz je Wi-Fi objekt realne pripojeny k AP."""
    return wifi is not None and wifi.is_connected()


def connect_wifi(profile="auto", persist=False, mode="broadcast"):
    """Spusti vybrany Wi-Fi rezim bez shozeni runtime pri chybe."""
    global wifi
    global device_clock
    global WIFI_ON
    global WIFI_CONNECT_ON
    global WIFI_BROADCAST_ON

    stop_network_services()
    if wifi is None:
        wifi = Wifi()

    try:
        if mode == "connect":
            connected = wifi.Wifi_Connect(profile)
        else:
            connected = wifi.Wifi_Broadcast()
    except Exception as error:
        connected = False
        if VERBOSE:
            print(f"Failed to connect Wifi: {error}")
        try:
            wifi.set_fallback_channel()
        except Exception:
            pass
    if connected:
        WIFI_CONNECT_ON = mode == "connect"
        WIFI_BROADCAST_ON = mode != "connect"
    else:
        if mode == "connect":
            WIFI_CONNECT_ON = False
        else:
            WIFI_BROADCAST_ON = False
    WIFI_ON = WIFI_CONNECT_ON or WIFI_BROADCAST_ON
    if connected:
        if wifi.is_station_connected():
            try:
                if device_clock is None:
                    device_clock = Clock(wifi)
                device_clock.sync_ntp()
            except Exception as error:
                if VERBOSE:
                    print(f"Failed to sync clock: {error}")

        try:
            start_network_services()
        except Exception as error:
            if VERBOSE:
                print(f"Failed to start network services: {error}")
            WIFI_ON = False
            WIFI_CONNECT_ON = False
            WIFI_BROADCAST_ON = False
    else:
        device_clock = None

    ensure_espnow()
    if persist:
        persist_runtime_setting("Wifi_Connect", WIFI_CONNECT_ON)
        persist_runtime_setting("Wifi_Broadcast", WIFI_BROADCAST_ON)
    return WIFI_ON


def disconnect_wifi(persist=False):
    """Odpoji Wi-Fi a ponecha fallback kanal pro ESP-NOW."""
    global WIFI_ON
    global WIFI_CONNECT_ON
    global WIFI_BROADCAST_ON
    global device_clock

    stop_network_services()
    if wifi is not None:
        wifi.disconnect()
    device_clock = None
    WIFI_ON = False
    WIFI_CONNECT_ON = False
    WIFI_BROADCAST_ON = False
    ensure_espnow()
    if persist:
        persist_runtime_setting("Wifi_Connect", WIFI_CONNECT_ON)
        persist_runtime_setting("Wifi_Broadcast", WIFI_BROADCAST_ON)


def get_performance_snapshot():
    """Vrati posledni namereny performance snapshot pro HTTP API."""
    if perf is None:
        return {}
    return perf.last_snapshot


def handle_http_time_sync(year, month, day, hour, minute, second):
    """Nastavi RTC podle lokalniho casu poslaneho z weboveho prohlizece."""
    global device_clock

    if device_clock is None:
        device_clock = Clock(wifi)
    return device_clock.set_datetime(year, month, day, hour, minute, second)


def persist_runtime_settings_to_nvm():
    """Zapise vsechny runtime volby do `microcontroller.nvm`."""
    required_length = len(NVM_MAGIC) + NVM_FLAG_BYTES + NVM_VALUE_BYTES
    if len(microcontroller.nvm) < required_length:
        if VERBOSE:
            print("microcontroller.nvm is too small for runtime settings")
        return False

    flag_bytes = [0] * NVM_FLAG_BYTES
    for setting_key, bit_index in SETTING_BITS.items():
        if RUNTIME_SETTINGS.get(setting_key, False):
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            flag_bytes[byte_index] |= 1 << bit_offset
    value_bytes = bytes([
        int(RUNTIME_SETTINGS.get("BRIGHTNESS_INDEX", 0)) & 0xFF,
        int(RUNTIME_SETTINGS.get("OLED_FONT_SCALE_INDEX", 0)) & 0xFF,
        int(RUNTIME_SETTINGS.get("FAN_SPEED_INDEX", 0)) & 0xFF,
    ])

    try:
        microcontroller.nvm[:required_length] = NVM_MAGIC + bytes(flag_bytes) + value_bytes
    except (OSError, ValueError) as error:
        if VERBOSE:
            print(f"Failed to write runtime settings to NVM: {error}")
        return False

    return True


def persist_boolean_setting(key, value):
    """Ulozi jeden runtime prepinac do `microcontroller.nvm`."""
    RUNTIME_SETTINGS[key] = value
    return persist_runtime_settings_to_nvm()


def persist_value_setting(key, value):
    """Ulozi jednu runtime hodnotu do `microcontroller.nvm`."""
    RUNTIME_SETTINGS[key] = int(value)
    return persist_runtime_settings_to_nvm()


def persist_runtime_setting(setting_name, value):
    """Prevede nazev polozky z UI na ulozeny klic a zapise ho do NVM."""
    key = SETTING_ENV_KEYS.get(setting_name)
    if key is None:
        if VERBOSE:
            print(f"No runtime mapping for: {setting_name}")
        return False
    return persist_boolean_setting(key, value)


def set_fan_speed(percent):
    """Nastavi PWM vykon ventilatoru v rozsahu 0 az 100 procent."""
    global FAN_SPEED_PERCENT

    percent = max(0, min(100, int(percent)))
    FAN_SPEED_PERCENT = percent
    if fan_pwm is not None:
        fan_pwm.duty_cycle = round(percent * 65535 / 100)


def cycle_fan_speed():
    """Posune ventilator na dalsi preddefinovany vykon."""
    try:
        current_index = FAN_SPEED_STEPS.index(FAN_SPEED_PERCENT)
    except ValueError:
        current_index = 0

    current_index = (current_index + 1) % len(FAN_SPEED_STEPS)
    set_fan_speed(FAN_SPEED_STEPS[current_index])
    persist_value_setting("FAN_SPEED_INDEX", current_index)
    return FAN_SPEED_PERCENT


def initialize_display_stack():
    """Vytvori RGB matici, regiony obliceje a controller emote."""
    global display
    global face_emotes
    global nose_matrix
    global eye_matrix
    global mouth_matrix
    global whole_matrix
    global nose_matrix_right
    global eye_matrix_right
    global mouth_matrix_right
    global whole_matrix_right

    # Kazda fyzicka strana ma vlastni sadu regionu, aby sla ovladat nezavisle.
    display = Display()
    nose_matrix = display.create_matrix(
        name="nose",
        position_x=0,
        position_y=0,
        matrix_width=32,
        matrix_height=16,
        mirror_x=True,
        mirror_position_x=True,
    )
    eye_matrix = display.create_matrix(
        name="eye",
        position_x=31,
        position_y=0,
        matrix_width=32,
        matrix_height=16,
        mirror_x=True,
        mirror_position_x=True,
    )
    mouth_matrix = display.create_matrix(
        name="mouth",
        position_x=0,
        position_y=16,
        matrix_width=64,
        matrix_height=16,
        mirror_x=True,
        mirror_position_x=True,
    )
    whole_matrix = display.create_matrix(
        name="whole",
        position_x=0,
        position_y=0,
        matrix_width=64,
        matrix_height=32,
        mirror_x=True,
        mirror_position_x=True,
    )
    nose_matrix_right = display.create_matrix(
        name="nose_right",
        position_x=0,
        position_y=0,
        matrix_width=32,
        matrix_height=16,
        screen="right",
    )
    eye_matrix_right = display.create_matrix(
        name="eye_right",
        position_x=31,
        position_y=0,
        matrix_width=32,
        matrix_height=16,
        screen="right",
    )
    mouth_matrix_right = display.create_matrix(
        name="mouth_right",
        position_x=0,
        position_y=16,
        matrix_width=64,
        matrix_height=16,
        screen="right",
    )
    whole_matrix_right = display.create_matrix(
        name="whole_right",
        position_x=0,
        position_y=0,
        matrix_width=64,
        matrix_height=32,
        screen="right",
    )
    face_emotes = emotes.FaceEmoteController(
        display,
        eye_matrix,
        nose_matrix,
        mouth_matrix,
        whole_matrix,
        secondary_faces=[{
            "eye": eye_matrix_right,
            "nose": nose_matrix_right,
            "mouth": mouth_matrix_right,
            "whole": whole_matrix_right,
        }],
        blink_enabled=BLINK_ON,
        smooth_transitions_enabled=SMOOTH_TRANSITIONS_ON,
        blink_time_set=BLINK_TIME_SET,
        emote_timer=EMOTE_TIMER,
        boop_timer=BOOP_TIMER,
        boop_rainbow_enabled=BOOP_RAINBOW_ON,
        rainbow_override_enabled=RAINBOW_OVERRIDE_ON,
        verbose=VERBOSE,
    )
    display.refresh()


def shutdown_display_stack():
    """Uvolni RGB matici a objekty navazane na aktivni displej."""
    global display
    global face_emotes
    global nose_matrix
    global eye_matrix
    global mouth_matrix
    global whole_matrix
    global nose_matrix_right
    global eye_matrix_right
    global mouth_matrix_right
    global whole_matrix_right

    if face_emotes is not None:
        face_emotes.shutdown()
    face_emotes = None

    if display is not None:
        display.deinit()
    display = None
    nose_matrix = None
    eye_matrix = None
    mouth_matrix = None
    whole_matrix = None
    nose_matrix_right = None
    eye_matrix_right = None
    mouth_matrix_right = None
    whole_matrix_right = None


def handle_ui_event(event):
    """Prevede jednu UI udalost na akci aplikace v aktualni iteraci."""
    toggled_setting = None

    if event is None:
        return toggled_setting

    event_type, value = event

    if event_type == EVENT_SETTING_SELECTED:
        toggled_setting = toggle_setting(value)

    return toggled_setting


def toggle_setting(setting_name):
    """Prepne jednu runtime volbu a pri potrebe doinicializuje hardware."""
    global ACCELEROMETER_ON
    global APDS_ON
    global boop_threshold
    global boop_threshold_tracker
    global WIFI_ON
    global WIFI_CONNECT_ON
    global WIFI_BROADCAST_ON
    global accelerometer
    global apds
    global wifi
    global device_clock
    global VERBOSE
    global MIC_ON
    global mic
    global BLINK_ON
    global SMOOTH_TRANSITIONS_ON
    global DISPLAY_ON
    global BOOP_RAINBOW_ON
    global RAINBOW_OVERRIDE_ON
    global display
    global face_emotes
    global server

    if setting_name == "Accelerometer":
        # Pri zapnuti vytvor senzor jen jednou a pak uz ho znovu pouzivej.
        ACCELEROMETER_ON = not ACCELEROMETER_ON
        if ACCELEROMETER_ON and accelerometer is None:
            accelerometer = initialize_optional_component("Accelerometer", Accelerometer)
        persist_runtime_setting(setting_name, ACCELEROMETER_ON)
        return setting_name

    if setting_name == "Boop":
        APDS_ON = not APDS_ON
        if APDS_ON and apds is None:
            apds = initialize_optional_component("APDS", APDSSensor)
        persist_runtime_setting(setting_name, APDS_ON)
        return setting_name

    if setting_name == "Boop Calibrate":
        current_value = None
        if APDS_ON:
            if apds is None:
                apds = initialize_optional_component("APDS", APDSSensor)
            if apds is not None:
                current_value = read_optional_component("APDS", apds.get_value)
        boop_threshold = boop_threshold_tracker.calibrate(current_value)
        return setting_name

    if setting_name == "Boop Rainbow":
        BOOP_RAINBOW_ON = not BOOP_RAINBOW_ON
        if face_emotes is not None:
            face_emotes.set_boop_rainbow_enabled(BOOP_RAINBOW_ON)
        persist_runtime_setting(setting_name, BOOP_RAINBOW_ON)
        return setting_name

    if setting_name == "Rainbow Override":
        RAINBOW_OVERRIDE_ON = not RAINBOW_OVERRIDE_ON
        if face_emotes is not None:
            face_emotes.set_rainbow_override_enabled(RAINBOW_OVERRIDE_ON)
        persist_runtime_setting(setting_name, RAINBOW_OVERRIDE_ON)
        return setting_name

    if setting_name == "Blink":
        BLINK_ON = not BLINK_ON
        persist_runtime_setting(setting_name, BLINK_ON)
        return setting_name

    if setting_name == "Smooth Transitions":
        SMOOTH_TRANSITIONS_ON = not SMOOTH_TRANSITIONS_ON
        if face_emotes is not None:
            face_emotes.set_smooth_transitions_enabled(SMOOTH_TRANSITIONS_ON)
        persist_runtime_setting(setting_name, SMOOTH_TRANSITIONS_ON)
        return setting_name

    if setting_name == "Brightness":
        display_module.cycle_brightness_scale()
        persist_value_setting("BRIGHTNESS_INDEX", display_module.get_brightness_scale_index())
        if DISPLAY_ON:
            shutdown_display_stack()
            initialize_display_stack()
        return setting_name

    if setting_name == "Font":
        cycle_oled_font_scale()
        persist_value_setting("OLED_FONT_SCALE_INDEX", get_oled_font_scale_index())
        return setting_name

    if setting_name == "Fan":
        cycle_fan_speed()
        return setting_name

    if setting_name in WIFI_RETRY_SETTINGS:
        connect_wifi(WIFI_RETRY_SETTINGS[setting_name], persist=False)
        return setting_name

    if setting_name == "Wifi_Connect":
        if WIFI_CONNECT_ON:
            disconnect_wifi(persist=True)
            return setting_name

        WIFI_BROADCAST_ON = False
        connect_wifi("auto", persist=True, mode="connect")
        return setting_name

    if setting_name == "Wifi_Broadcast":
        if WIFI_BROADCAST_ON:
            disconnect_wifi(persist=True)
            return setting_name

        WIFI_CONNECT_ON = False
        connect_wifi("auto", persist=True, mode="broadcast")
        return setting_name
        

    
    if setting_name == "Verbose":
        VERBOSE = not VERBOSE
        if face_emotes is not None:
            face_emotes.verbose = VERBOSE
        persist_runtime_setting(setting_name, VERBOSE)
        return setting_name
    
    if setting_name == "Mic":
        MIC_ON = not MIC_ON
        if MIC_ON and mic is None:
            mic = initialize_optional_component("Mic", Microphone)
        persist_runtime_setting(setting_name, MIC_ON)
        return setting_name
    
    if setting_name == "Display":
        # RGB matici lze za behu vytvorit i uplne uvolnit.
        DISPLAY_ON = not DISPLAY_ON
        if DISPLAY_ON:
            if display is None:
                initialize_display_stack()
        else:
            shutdown_display_stack()
        persist_runtime_setting(setting_name, DISPLAY_ON)
        return setting_name

    if VERBOSE:
        message = f"Unknown setting: {setting_name}"
        print(message)
        logger.warning(message)
    return None


def get_setting_values():
    """Vrati aktualni hodnoty voleb, ktere ma UI zobrazit."""
    return {
        "Display": DISPLAY_ON,
        "Boop": APDS_ON,
        "Boop Calibrate": True,
        "Boop Rainbow": BOOP_RAINBOW_ON,
        "Rainbow Override": RAINBOW_OVERRIDE_ON,
        "Blink": BLINK_ON,
        "Smooth Transitions": SMOOTH_TRANSITIONS_ON,
        "Brightness": display_module.get_brightness_scale(),
        "Font": get_oled_font_scale_label(),
        "Fan": FAN_SPEED_PERCENT,
        "Wifi_Connect": WIFI_CONNECT_ON and is_wifi_connected(),
        "Wifi_Broadcast": WIFI_BROADCAST_ON and is_wifi_connected(),
        # "Wifi Main": True,
        # "Wifi Backup": True,
        "Accelerometer": ACCELEROMETER_ON,
        "Verbose": VERBOSE,
        "Mic": MIC_ON
    }


def get_clock_text():
    """Vrati text hodin z RTC nebo lokalniho casu i bez Wi-Fi syncu."""
    if device_clock is not None:
        return device_clock.get_time()

    now = time.localtime()
    return "{:02}:{:02}".format(now.tm_hour, now.tm_min)


def format_debug_value(value):
    """Prevede chybejici debug hodnotu na kratky placeholder."""
    if value is None:
        return "--"
    return str(value)


def initialize_optional_component(name, component_class):
    """Vytvori volitelnou komponentu, aniz by jeji absence zastavila runtime."""
    try:
        return component_class()
    except (OSError, ValueError, RuntimeError) as error:
        print("{} unavailable: {}".format(name, error))
        return None


def read_optional_component(name, reader):
    """Bezpecne precte senzor a pri chybe vrati chybejici hodnotu."""
    try:
        return reader()
    except (OSError, ValueError, RuntimeError) as error:
        if VERBOSE:
            print("{} read failed: {}".format(name, error))
        return None


def build_debug_lines(movement, mic_value, proximity_value, boop_threshold):
    """Sestavi radky pro OLED debug obrazovku."""
    movement_text = "--"
    if movement is not None:
        movement_text = "{:.2f},{:.2f}".format(movement[0], movement[1])

    return [
        f"Acc: {movement_text}",
        f"Mic: {format_debug_value(mic_value)}",
        f"APDS: {format_debug_value(proximity_value)}",
        f"Boop T: {format_debug_value(boop_threshold)}",
    ] + perf.format_debug_lines()


def sync_ui_settings(ui):
    """Propise aktualni runtime volby do OLED UI."""
    for setting_name, setting_value in get_setting_values().items():
        ui.set_setting_value(setting_name, setting_value)


def refresh_ui_snapshot(ui):
    """Vrati aktualni HTTP snapshot UI nebo `None`, pokud UI neni aktivni."""
    if ui is None:
        return None

    sync_ui_settings(ui)
    ui.set_clock_text(get_clock_text())
    return ui.get_http_menu_snapshot()


def process_ui_inputs(ui, server, *, confirm_click=False, next_click=False, prev_click=False):
    """Zpracuje jednu sadu UI vstupu a vrati aktivni menu emote a zmenene nastaveni."""
    if ui is None:
        return None, None

    sync_ui_settings(ui)
    ui.set_clock_text(get_clock_text())

    ui_event = ui.handle_input(
        confirm_click=confirm_click,
        next_click=next_click,
        prev_click=prev_click,
        server=server
    )
    active_menu_emote = ui.get_active_menu_emote()

    toggled_setting = handle_ui_event(ui_event)
    if toggled_setting is not None and toggled_setting == "Blink" and face_emotes is not None:
        face_emotes.blink_enabled = BLINK_ON

    sync_ui_settings(ui)
    ui.render_ui()
    return active_menu_emote, toggled_setting


def handle_http_menu_action(action):
    """Zpracuje HTTP menu akci synchronne a vrati aktualizovany snapshot menu."""
    if action == "back":
        if ui is not None:
            ui.go_back()
            sync_ui_settings(ui)
            ui.render_ui()
        if server is not None:
            snapshot = refresh_ui_snapshot(ui)
            server.set_menu_snapshot(snapshot)
            return snapshot
        return None

    confirm_click = action == "ok"
    next_click = action == "down"
    prev_click = action == "up"

    process_ui_inputs(
        ui,
        server,
        confirm_click=confirm_click,
        next_click=next_click,
        prev_click=prev_click,
    )

    if server is not None:
        snapshot = refresh_ui_snapshot(ui)
        server.set_menu_snapshot(snapshot)
        return snapshot

    return None

def decode_control_message(packet):
    if hasattr(packet, "msg"):
        data = packet.msg
    else:
        data = packet

    if len(data) not in (7, 8):
        raise ValueError("ControlMessage must have 7 or 8 bytes")

    return {
        "counter": struct.unpack("<I", data[0:4])[0],
        "button1": bool(data[4]),
        "button2": bool(data[5]),
        "button3": bool(data[6]),
        "button4": len(data) >= 8 and bool(data[7]),
    }


def control_message_to_ui_clicks(message):
    """Prevede ESP-NOW ControlMessage na stejne kliky, ktere pouziva OLED UI."""
    return {
        "confirm": message["button3"],
        "next": message["button2"],
        "prev": message["button1"],
        "back": message["button4"],
    }


# Casove konstanty pro automaticke reakce obliceje.
BLINK_TIME_SET = 100
BOOP_TIMER = 5
EMOTE_TIMER = 10


# Inicializace hardwaru podle nactenych runtime voleb.
if ACCELEROMETER_ON:
    accelerometer = initialize_optional_component("Accelerometer", Accelerometer)

if WIFI_BROADCAST_ON:
    connect_wifi("auto", persist=False, mode="broadcast")
elif WIFI_CONNECT_ON:
    connect_wifi("auto", persist=False, mode="connect")

if MIC_ON:
    mic = initialize_optional_component("Mic", Microphone)

if APDS_ON:
    apds = initialize_optional_component("APDS", APDSSensor)

boop_threshold_tracker = BoopThresholdTracker()

if SSD1306_ON:
    oled = initialize_optional_component("OLED", OLEDDisplay)

# Tlacitka pouzivaji pull-up, stisk tedy vraci logickou nulu.
btn_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
btn_up = digitalio.DigitalInOut(board.BUTTON_UP)
btn_prev = digitalio.DigitalInOut(board.A4)
btn_down.switch_to_input(pull=digitalio.Pull.UP)
btn_up.switch_to_input(pull=digitalio.Pull.UP)
btn_prev.switch_to_input(pull=digitalio.Pull.UP)

if DISPLAY_ON:
    initialize_display_stack()

# OLED UI je volitelne. Kdyz neni OLED aktivni, zbytek runtime muze bezet dal.
ui = UI(oled) if oled is not None else None
if server is not None and ui is not None:
    server.set_menu_action_handler(handle_http_menu_action)
    server.set_menu_snapshot(refresh_ui_snapshot(ui))
prev_up_pressed = False
prev_down_pressed = False
prev_prev_pressed = False
toggled_setting = None
perf = PerformanceMonitor(report_interval=5.0)
last_debug_ui_update = 0.0
if server is not None:
    server.set_performance_provider(get_performance_snapshot)


# PWM vystup pro ridici vodic ventilatoru na A1.
fan_pwm = pwmio.PWMOut(
    board.A1,
    frequency=25_000,
    duty_cycle=0
)
set_fan_speed(FAN_SPEED_PERCENT)

# Hlavni smycka pravidelne cte vstupy, aktualizuje UI a prekresluje vystupy.
while True:
    perf.begin_loop()
    toggled_setting = None
    iteration_logs = []

    # 1) Nacti vstupy ze senzoru.
    perf.begin_section("sensors")
    debug_screen_active = ui is not None and ui.active_screen == SCREEN_DEBUG_MENU
    movement = read_optional_component("Accelerometer", accelerometer.derivation) if ACCELEROMETER_ON and accelerometer is not None else None
    mic_value = read_optional_component("Mic", mic.get_value) if MIC_ON and mic is not None and (MIC_READ_ON or debug_screen_active) else None
    proximity_value = read_optional_component("APDS", apds.get_value) if APDS_ON and apds is not None else None
    boop_active = face_emotes is not None and face_emotes.is_boop_active()
    boop_threshold = boop_threshold_tracker.update(
        proximity_value,
        freeze=boop_active,
    )
    perf.end_section()

    # 1.5) Přečti ESP komunikaci
    esp_confirm_click = False
    esp_next_click = False
    esp_prev_click = False
    esp_back_click = False

    packet = esp.read() if esp is not None else None
    if packet is not None:
        message = decode_control_message(packet)
        esp_pressed = control_message_to_ui_clicks(message)
        esp_confirm_click = esp_pressed["confirm"]
        esp_next_click = esp_pressed["next"]
        esp_prev_click = esp_pressed["prev"]
        esp_back_click = esp_pressed["back"]

    # 2) Preved fyzicke stavy tlacitek na jednotlive klik udalosti.
    perf.begin_section("buttons")
    up_pressed = not btn_up.value
    down_pressed = not btn_down.value
    prev_pressed = not btn_prev.value
    up_click = up_pressed and not prev_up_pressed
    down_click = down_pressed and not prev_down_pressed
    prev_click = prev_pressed and not prev_prev_pressed
    perf.end_section()

    # 3) Posun oblicej podle akcelerometru, ale jen kdyz zrovna neni aktivni fullscreen emote.
    perf.begin_section("motion")
    if (
        ACCELEROMETER_ON
        and face_emotes is not None
        and movement is not None
        and not face_emotes.whole_region["active"]
    ):
        if abs(movement[0]) > MIN_MOVEMENT or abs(movement[1]) > MIN_MOVEMENT or abs(movement[2]) > MIN_MOVEMENT:
            if VERBOSE:
                print("move")
            # Posun vsechny regiony stejne, aby se oblicej hybal jako celek.
            movement_x = int(movement[0])
            movement_y = int(movement[1])
            for matrix_group in (
                eye_matrix,
                nose_matrix,
                mouth_matrix,
                whole_matrix,
                eye_matrix_right,
                nose_matrix_right,
                mouth_matrix_right,
                whole_matrix_right,
            ):
                display.set_matrix_position(
                    matrix_group,
                    matrix_group["tile"].x - movement_x,
                    matrix_group["tile"].y + movement_y,
                )
        else:
            for matrix_group in (
                eye_matrix,
                nose_matrix,
                mouth_matrix,
                whole_matrix,
                eye_matrix_right,
                nose_matrix_right,
                mouth_matrix_right,
                whole_matrix_right,
            ):
                display.set_matrix_position(
                    matrix_group,
                    matrix_group["position_x"],
                    matrix_group["position_y"],
                )
    perf.end_section()

    # 4) Synchronizuj OLED UI, zpracuj vstup a zjisti, jestli je otevreny nejaky emote z menu.
    perf.begin_section("ui")
    ui_event = None
    active_menu_emote = None
    if ui is not None:
        sync_ui_settings(ui)
        ui.set_clock_text(get_clock_text())
        was_debug_screen = ui.active_screen == SCREEN_DEBUG_MENU
        if esp_back_click:
            ui.go_back()
        ui_event = ui.handle_input(
            confirm_click=up_click or esp_confirm_click,
            next_click=down_click or esp_next_click,
            prev_click=prev_click or esp_prev_click,
            server=server
        )
        active_menu_emote = ui.get_active_menu_emote()
        if ui.active_screen == SCREEN_DEBUG_MENU:
            now = time.monotonic()
            if not was_debug_screen or now - last_debug_ui_update >= DEBUG_UI_UPDATE_INTERVAL:
                if not was_debug_screen and mic_value is None and MIC_ON and mic is not None:
                    mic_value = read_optional_component("Mic", mic.get_value)
                ui.set_debug_lines(
                    build_debug_lines(
                        movement,
                        mic_value,
                        proximity_value,
                        boop_threshold,
                    )
                )
                last_debug_ui_update = now

    # 5) Preved udalost z UI na zmenu runtime nastaveni.
    new_setting = handle_ui_event(ui_event)
    if new_setting is not None:
        toggled_setting = new_setting
        if toggled_setting == "Blink" and face_emotes is not None:
            face_emotes.blink_enabled = BLINK_ON

    # 6) Po zpracovani zmen znovu vyrenderuj OLED.
    if ui is not None:
        sync_ui_settings(ui)
        ui.render_ui()
    perf.end_section()

    # 7) Aktualizuj emote controller podle menu a senzoru.
    perf.begin_section("emote")
    if face_emotes is not None:
        face_emotes.update(
            active_menu_emote=active_menu_emote,
            device_clock=device_clock if is_wifi_connected() else None,
            mic_value=mic_value,
            proximity_value=proximity_value,
            boop_threshold=boop_threshold,
        )
    perf.end_section()

    # 8) Obsluz HTTP server, pokud bezi.
    perf.begin_section("server")
    if server is not None:
        if ui is not None:
            server.set_menu_snapshot(ui.get_http_menu_snapshot())
        else:
            server.set_menu_snapshot(None)
        server.poll()
    perf.end_section()


    # 9) Odesli vykreslene zmeny na RGB matici a uloz stavy tlacitek pro dalsi iteraci.
    perf.begin_section("display")
    if display is not None:
        display.refresh()
    perf.end_section()

    prev_up_pressed = up_pressed
    prev_down_pressed = down_pressed
    prev_prev_pressed = prev_pressed

    perf.end_work()
    if perf.should_report():
        perf.report()
        if VERBOSE:
            message = perf.format_log_line()
            iteration_logs.append(message)
            logger.info(message)

    # 10) Vypis debug logy do konzole a do kruhoveho bufferu.
    if VERBOSE:
        if ACCELEROMETER_ON:
            message = f"Accelerometer: {movement}"
            iteration_logs.append(message)
            logger.info(message)

        if MIC_ON:
            message = f"Mic: {mic_value}"
            iteration_logs.append(message)
            logger.info(message)

        if APDS_ON:
            # print(apds.scan())
            #print(apds.get_color())
            message = f"APDS: {proximity_value} / Boop T: {boop_threshold}"
            iteration_logs.append(message)
            logger.info(message)

        if toggled_setting is not None:
            message = f"UI setting: {toggled_setting}"
            iteration_logs.append(message)
            logger.info(message)

        if iteration_logs:
            print("------")
            print(f"{get_clock_text()}{iteration_logs}")

    # Kratke uspani drzi smycku stabilni a omezuje zbytecne pretizeni CPU.
    time.sleep(0.01)
