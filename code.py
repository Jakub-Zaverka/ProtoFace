import time
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



ACCELEROMETER_ON = True
MIC_ON = True
APDS_ON = True
SSD1306_ON = True
WIFI_ON = True
VERBOSE = False
MIN_MOVEMENT = 1

display = Display()
if ACCELEROMETER_ON:
    accelerometer = Accelerometer()

if WIFI_ON:
    wifi = Wifi()
    wifi.connect()
    device_clock = Clock(wifi)
    device_clock.sync_ntp()

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
btn_down.switch_to_input(pull=digitalio.Pull.UP)
btn_up.switch_to_input(pull=digitalio.Pull.UP)

face_emotes = emotes.FaceEmoteController(
    display,
    eye_matrix,
    nose_matrix,
    mouth_matrix,
    whole_matrix,
    blink_time_set=BLINK_TIME_SET,
    emote_timer=EMOTE_TIMER,
    boop_timer=BOOP_TIMER,
    verbose=VERBOSE,
)

display.refresh()

while True:
    movement = accelerometer.derivation() if ACCELEROMETER_ON else None
    mic_value = mic.get_value() if MIC_ON else None
    proximity_value = apds.get_value() if APDS_ON else None
    
    #if movement
    if ACCELEROMETER_ON and not face_emotes.whole_region["active"]:
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
    
    face_emotes.update(
        button_up_pressed=not btn_up.value,
        button_down_pressed=not btn_down.value,
        device_clock=device_clock if WIFI_ON else None,
        mic_value=mic_value,
        proximity_value=proximity_value,
    )



    #OLED screen
    if SSD1306_ON:
        status_region = face_emotes.get_status_region()
        oled.draw_status(
            boop=face_emotes.is_boop_active(),
            emote=face_emotes.any_active(),
            emote_time=status_region["elapsed"],
            emote_name=emotes.get_emote_name(status_region),
            current_time=device_clock.get_time() if WIFI_ON else "--:--",
        )



    # debug print
    if VERBOSE:
        if ACCELEROMETER_ON:
            print(f"Accelerometer: {movement}")

        if MIC_ON:
            print(f"Mic: {mic_value}")

        if APDS_ON:
            # print(apds.scan())
            #print(apds.get_color())
            print(f"APDS: {proximity_value}")

        print("----")
    
    
    display.refresh()
    time.sleep(0.1)
