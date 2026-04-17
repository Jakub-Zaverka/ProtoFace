"""Main runtime loop wiring sensors, buttons, the display and emote control."""

import microcontroller
import os
import time
import adafruit_logging as logging
from display import Display
from accelerometer import Accelerometer
from mic import Microphone
from I2C_sim import APDSSensor
from I2C_sim import OLEDDisplay
import board
import digitalio
from wifi_network import Wifi
from clock import Clock
import emotes
from UI import EVENT_SETTING_SELECTED
from UI import UI
from server import ServerClass

NVM_MAGIC = b"PFS1"
LOG_BUFFER_SIZE = 100
SETTING_ENV_KEYS = {
    "Accelerometer": "ACCELEROMETER_ON",
    "Boop": "APDS_ON",
    "Blink": "BLINK_ON",
    "Wifi": "WIFI_ON",
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
    "DISPLAY_ON":6
}

MIN_MOVEMENT = 1

accelerometer = None
mic = None
apds = None
wifi = None
device_clock = None
oled = None
display = None
face_emotes = None
nose_matrix = None
eye_matrix = None
mouth_matrix = None
whole_matrix = None
sys_log = []
logger = None
server = None


class ListHandler(logging.Handler):
    """Keep recent log entries in a plain Python list."""

    def __init__(self, storage, max_items=LOG_BUFFER_SIZE):
        super().__init__()
        self.storage = storage
        self.max_items = max_items

    def emit(self, record):
        self.storage.append(str(record.msg))
        if self.max_items is not None and len(self.storage) > self.max_items:
            del self.storage[:-self.max_items]


def load_runtime_settings():
    """Load persisted UI settings from microcontroller NVM."""
    if len(microcontroller.nvm) < len(NVM_MAGIC) + 1:
        return {}

    raw = bytes(microcontroller.nvm[: len(NVM_MAGIC) + 1])
    if raw[: len(NVM_MAGIC)] != NVM_MAGIC:
        return {}

    flags = raw[len(NVM_MAGIC)]
    runtime_settings = {}
    for setting_key, bit_index in SETTING_BITS.items():
        runtime_settings[setting_key] = bool(flags & (1 << bit_index))
    return runtime_settings


def read_bool_setting(name, default):
    """Read one boolean setting from runtime JSON, env config or fallback."""
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


RUNTIME_SETTINGS = load_runtime_settings()


ACCELEROMETER_ON = read_bool_setting("ACCELEROMETER_ON", True)
MIC_ON = read_bool_setting("MIC_ON", True)
APDS_ON = read_bool_setting("APDS_ON", True)
SSD1306_ON = read_bool_setting("SSD1306_ON", True)
WIFI_ON = read_bool_setting("WIFI_ON", True)
VERBOSE = read_bool_setting("VERBOSE", False)
BLINK_ON = read_bool_setting("BLINK_ON", True)
DISPLAY_ON = read_bool_setting("DISPLAY_ON", True)

logger = logging.getLogger("runtime")
logger.setLevel(logging.INFO)
logger.addHandler(ListHandler(sys_log))


def start_network_services():
    """Start HTTP-related network services for the active Wi-Fi connection."""
    global server

    if wifi is None:
        raise RuntimeError("Wi-Fi must be initialized before starting services")

    wifi.advertise_http(80)
    if server is None:
        server = ServerClass(wifi)
    print("HTTP server available at {}".format(wifi.base_url(80)))
    print("HTTP server available at {}".format(wifi.ip_url(80)))


def persist_boolean_setting(key, value):
    """Store one boolean setting in microcontroller NVM."""
    if len(microcontroller.nvm) < len(NVM_MAGIC) + 1:
        if VERBOSE:
            print("microcontroller.nvm is too small for runtime settings")
        return False

    RUNTIME_SETTINGS[key] = value
    flags = 0
    for setting_key, bit_index in SETTING_BITS.items():
        if RUNTIME_SETTINGS.get(setting_key, False):
            flags |= 1 << bit_index

    try:
        microcontroller.nvm[: len(NVM_MAGIC) + 1] = NVM_MAGIC + bytes([flags])
    except (OSError, ValueError) as error:
        if VERBOSE:
            print(f"Failed to write runtime settings to NVM: {error}")
        return False

    return True


def persist_runtime_setting(setting_name, value):
    """Map one UI setting name to its persisted runtime key and store it."""
    key = SETTING_ENV_KEYS.get(setting_name)
    if key is None:
        if VERBOSE:
            print(f"No runtime mapping for: {setting_name}")
        return False
    return persist_boolean_setting(key, value)


def initialize_display_stack():
    """Create the HUB75 display, face regions and controller."""
    global display
    global face_emotes
    global nose_matrix
    global eye_matrix
    global mouth_matrix
    global whole_matrix

    display = Display()
    nose_matrix = display.create_matrix(
        name="nose",
        position_x=0,
        position_y=0,
        matrix_width=32,
        matrix_height=16,
    )
    eye_matrix = display.create_matrix(
        name="eye",
        position_x=31,
        position_y=0,
        matrix_width=32,
        matrix_height=16,
    )
    mouth_matrix = display.create_matrix(
        name="mouth",
        position_x=0,
        position_y=16,
        matrix_width=64,
        matrix_height=16,
    )
    whole_matrix = display.create_matrix(
        name="whole",
        position_x=0,
        position_y=0,
        matrix_width=64,
        matrix_height=32,
    )
    face_emotes = emotes.FaceEmoteController(
        display,
        eye_matrix,
        nose_matrix,
        mouth_matrix,
        whole_matrix,
        blink_enabled=BLINK_ON,
        blink_time_set=BLINK_TIME_SET,
        emote_timer=EMOTE_TIMER,
        boop_timer=BOOP_TIMER,
        verbose=VERBOSE,
    )
    display.refresh()


def shutdown_display_stack():
    """Release the HUB75 display and all objects bound to it."""
    global display
    global face_emotes
    global nose_matrix
    global eye_matrix
    global mouth_matrix
    global whole_matrix

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


def handle_ui_event(event):
    """Translate one UI event into app actions for the current loop."""
    toggled_setting = None

    if event is None:
        return toggled_setting

    event_type, value = event

    if event_type == EVENT_SETTING_SELECTED:
        toggled_setting = toggle_setting(value)

    return toggled_setting


def toggle_setting(setting_name):
    """Toggle one runtime setting and initialize hardware when needed."""
    global ACCELEROMETER_ON
    global APDS_ON
    global WIFI_ON
    global accelerometer
    global apds
    global wifi
    global device_clock
    global VERBOSE
    global MIC_ON
    global mic
    global BLINK_ON
    global DISPLAY_ON
    global display
    global face_emotes
    global server

    if setting_name == "Accelerometer":
        ACCELEROMETER_ON = not ACCELEROMETER_ON
        if ACCELEROMETER_ON and accelerometer is None:
            accelerometer = Accelerometer()
        persist_runtime_setting(setting_name, ACCELEROMETER_ON)
        return setting_name

    if setting_name == "Boop":
        APDS_ON = not APDS_ON
        if APDS_ON and apds is None:
            apds = APDSSensor()
        persist_runtime_setting(setting_name, APDS_ON)
        return setting_name

    if setting_name == "Blink":
        BLINK_ON = not BLINK_ON
        persist_runtime_setting(setting_name, BLINK_ON)
        return setting_name

    if setting_name == "Wifi":
        if WIFI_ON:
            if server is not None:
                server.server.stop()
                server = None

            WIFI_ON = False
            persist_runtime_setting(setting_name, WIFI_ON)
            return setting_name

        try:
            if wifi is None:
                wifi = Wifi()
            wifi.connect()

            if device_clock is None:
                device_clock = Clock(wifi)
            device_clock.sync_ntp()

            start_network_services()
                
            WIFI_ON = True
            persist_runtime_setting(setting_name, WIFI_ON)
            return setting_name
        except Exception as error:
            WIFI_ON = False
            if VERBOSE:
                print(f"Failed to enable Wifi: {error}")
            return None
        

    
    if setting_name == "Verbose":
        VERBOSE = not VERBOSE
        if face_emotes is not None:
            face_emotes.verbose = VERBOSE
        persist_runtime_setting(setting_name, VERBOSE)
        return setting_name
    
    if setting_name == "Mic":
        MIC_ON = not MIC_ON
        if MIC_ON and mic is None:
            mic = Microphone()
        persist_runtime_setting(setting_name, MIC_ON)
        return setting_name
    
    if setting_name == "Display":
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
    """Return the current UI-visible values for toggleable settings."""
    return {
        "Display": DISPLAY_ON,
        "Boop": APDS_ON,
        "Blink": BLINK_ON,
        "Wifi": WIFI_ON,
        "Accelerometer": ACCELEROMETER_ON,
        "Verbose": VERBOSE,
        "Mic": MIC_ON
    }


def get_clock_text():
    """Return a clock string from RTC/localtime even without Wi-Fi sync."""
    if device_clock is not None:
        return device_clock.get_time()

    now = time.localtime()
    return "{:02}:{:02}".format(now.tm_hour, now.tm_min)


def sync_ui_settings(ui):
    """Push current runtime setting values into the rendered UI."""
    for setting_name, setting_value in get_setting_values().items():
        ui.set_setting_value(setting_name, setting_value)


if ACCELEROMETER_ON:
    accelerometer = Accelerometer()

if WIFI_ON:
    wifi = Wifi()
    wifi.connect()
    device_clock = Clock(wifi)
    device_clock.sync_ntp()
    start_network_services()

if MIC_ON:
    mic = Microphone()

if APDS_ON:
    apds = APDSSensor()

if SSD1306_ON:
    oled = OLEDDisplay()


BLINK_TIME_SET = 10
BOOP_TIMER = 5
EMOTE_TIMER = 10


btn_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
btn_up = digitalio.DigitalInOut(board.BUTTON_UP)
btn_prev = digitalio.DigitalInOut(board.A4)
btn_down.switch_to_input(pull=digitalio.Pull.UP)
btn_up.switch_to_input(pull=digitalio.Pull.UP)
btn_prev.switch_to_input(pull=digitalio.Pull.UP)

if DISPLAY_ON:
    initialize_display_stack()

ui = UI(oled) if SSD1306_ON else None
prev_up_pressed = False
prev_down_pressed = False
prev_prev_pressed = False
toggled_setting = None

while True:
    toggled_setting = None
    iteration_logs = []
    movement = accelerometer.derivation() if ACCELEROMETER_ON else None
    mic_value = mic.get_value() if MIC_ON else None
    proximity_value = apds.get_value() if APDS_ON else None
    up_pressed = not btn_up.value
    down_pressed = not btn_down.value
    prev_pressed = not btn_prev.value
    up_click = up_pressed and not prev_up_pressed
    down_click = down_pressed and not prev_down_pressed
    prev_click = prev_pressed and not prev_prev_pressed
    #if movement
    if (
        ACCELEROMETER_ON
        and face_emotes is not None
        and not face_emotes.whole_region["active"]
    ):
        if abs(movement[0]) > MIN_MOVEMENT or abs(movement[1]) > MIN_MOVEMENT or abs(movement[2]) > MIN_MOVEMENT:
            if VERBOSE:
                print("move")
            #correct accelerometer setting
            eye_matrix["tile"].x -= int(movement[0])
            eye_matrix["tile"].y += int(movement[1])
            nose_matrix["tile"].x -= int(movement[0])
            nose_matrix["tile"].y += int(movement[1])
            mouth_matrix["tile"].x -= int(movement[0])
            mouth_matrix["tile"].y += int(movement[1])
            whole_matrix["tile"].x -= int(movement[0])
            whole_matrix["tile"].y += int(movement[1])
        else:
            eye_matrix["tile"].x = 31
            eye_matrix["tile"].y = 0
            nose_matrix["tile"].x = 0
            nose_matrix["tile"].y = 0
            mouth_matrix["tile"].x = 0
            mouth_matrix["tile"].y = 16
            whole_matrix["tile"].x = 0
            whole_matrix["tile"].y = 0
    
    ui_event = None
    active_menu_emote = None
    if ui is not None:
        sync_ui_settings(ui)
        ui.set_clock_text(get_clock_text())
        ui.set_debug_lines([
            f"Acc: {movement[0]}{movement[1]}",
            f"Mic: {mic_value}",
            f"APDS: {proximity_value}",
        ])
        ui_event = ui.handle_input(
            confirm_click=up_click,
            next_click=down_click,
            prev_click=prev_click,
            server=server
        )
        active_menu_emote = ui.get_active_menu_emote()

    new_setting = handle_ui_event(ui_event)
    if new_setting is not None:
        toggled_setting = new_setting
        if toggled_setting == "Blink" and face_emotes is not None:
            face_emotes.blink_enabled = BLINK_ON

    if ui is not None:
        sync_ui_settings(ui)
        ui.render_ui()

    if face_emotes is not None:
        face_emotes.update(
            active_menu_emote=active_menu_emote,
            device_clock=device_clock if WIFI_ON else None,
            mic_value=mic_value,
            proximity_value=proximity_value,
        )

    if server is not None:
        server.poll()


    # debug print
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
            message = f"APDS: {proximity_value}"
            iteration_logs.append(message)
            logger.info(message)

        if toggled_setting is not None:
            message = f"UI setting: {toggled_setting}"
            iteration_logs.append(message)
            logger.info(message)

        if iteration_logs:
            print("------")
            print(f"{get_clock_text()}{iteration_logs}")

    
    if display is not None:
        display.refresh()
    prev_up_pressed = up_pressed
    prev_down_pressed = down_pressed
    prev_prev_pressed = prev_pressed
    time.sleep(0.1)
