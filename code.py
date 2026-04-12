import time
from display import Display
from accelerometer import Accelerometer
from mic import Microphone
from I2C_sim import APDSSensor
from I2C_sim import OLEDDisplay
import board
import digitalio
from wifi_network import Wifi



ACCELEROMETER_ON = True
MIC_ON = True
APDS_ON = True
SSD1306_ON = True
WIFI_ON = True
VERBOSE = False
MIN_MOVEMENT = 0.5

display = Display()
if ACCELEROMETER_ON:
    accelerometer = Accelerometer()

if WIFI_ON:
    wifi = Wifi()
    wifi.connect()
    wifi.get_time_ntp()

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

display.load_bmp_into_matrix(eye_matrix, "/faces/eye.bmp")
display.load_bmp_into_matrix(nose_matrix, "/faces/nose.bmp")
display.load_bmp_into_matrix(mouth_matrix, "/faces/mouth.bmp")


display.refresh()


if MIC_ON:
    mic = Microphone()

if APDS_ON:
    apds = APDSSensor()

if SSD1306_ON:
    oled = OLEDDisplay()


BLINK_TIME_SET = 10
BOOP_TIMER = 5
blink_time = 0
eye_closed = False
boop = False
boop_count = 0


btn_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
btn_up = digitalio.DigitalInOut(board.BUTTON_UP)
btn_down.switch_to_input(pull=digitalio.Pull.UP)
btn_up.switch_to_input(pull=digitalio.Pull.UP)

EMOTE_TIMER = 10
emote_time = 0
emote = False
current_emote_bmp = None
current_emote_timer = 0


def update_emote(
    requested_bmp,
    requested_timer,
    emote_active,
    emote_time,
    current_emote_bmp,
    current_emote_timer,
    display,
    target_matrix,
    idle_bmp,
    verbose=False,
):
    emote_started = False

    if requested_bmp is not None:
        if not emote_active or current_emote_bmp != requested_bmp:
            display.load_bmp_into_matrix(target_matrix, requested_bmp)
            emote_started = True
            if verbose:
                print("emote")
                print(requested_bmp)
        emote_active = True
        emote_time = 0
        current_emote_bmp = requested_bmp
        current_emote_timer = requested_timer
    elif emote_active:
        emote_time += 1

        if emote_time >= current_emote_timer:
            emote_active = False
            emote_time = 0
            current_emote_bmp = None
            current_emote_timer = 0
            display.load_bmp_into_matrix(target_matrix, idle_bmp)

    return (
        emote_active,
        emote_time,
        current_emote_bmp,
        current_emote_timer,
        emote_started,
    )


while True:
    #if movement
    if ACCELEROMETER_ON:
        if abs(accelerometer.derivation()[0]) > MIN_MOVEMENT or abs(accelerometer.derivation()[1]) > MIN_MOVEMENT or abs(accelerometer.derivation()[2] > MIN_MOVEMENT):
            print("move")
            #correct accelerometer setting
            eye_matrix["tile"].x -= int(accelerometer.derivation()[0])
            eye_matrix["tile"].y += int(accelerometer.derivation()[1])
            nose_matrix["tile"].x -= int(accelerometer.derivation()[0])
            nose_matrix["tile"].y += int(accelerometer.derivation()[1])
            mouth_matrix["tile"].x -= int(accelerometer.derivation()[0])
            mouth_matrix["tile"].y += int(accelerometer.derivation()[1])
        else:
            eye_matrix["tile"].x = 31
            eye_matrix["tile"].y = 0
            nose_matrix["tile"].x = 0
            nose_matrix["tile"].y = 0
            mouth_matrix["tile"].x = 0
            mouth_matrix["tile"].y = 16
            pass
    
    if MIC_ON:
        if mic.get_value() > 10:
            display.load_bmp_into_matrix(mouth_matrix, "/faces/mouth_speak.bmp")
            if VERBOSE: 
                print("speak")
        else:
            display.load_bmp_into_matrix(mouth_matrix, "/faces/mouth.bmp")

    

    #Blinking
    if not boop and not emote:
        if blink_time >= BLINK_TIME_SET and not eye_closed:
            eye_closed = True
            display.load_bmp_into_matrix(eye_matrix, "/faces/eye_blink.bmp")
            blink_time = 0

        elif blink_time >= BLINK_TIME_SET // 6 and eye_closed:
            eye_closed = False
            display.load_bmp_into_matrix(eye_matrix, "/faces/eye.bmp")
            blink_time = 0
            if VERBOSE:
                print("blink")

        else:
            blink_time += 1

    #Emote
    requested_emote_bmp = None
    requested_emote_timer = 0

    if not btn_up.value:
        requested_emote_bmp = "/faces/cross.bmp"
        requested_emote_timer = EMOTE_TIMER
    elif not btn_down.value:
        requested_emote_bmp = "/faces/sleep.bmp"
        requested_emote_timer = EMOTE_TIMER + 10

    (
        emote,
        emote_time,
        current_emote_bmp,
        current_emote_timer,
        emote_started,
    ) = update_emote(
        requested_bmp=requested_emote_bmp,
        requested_timer=requested_emote_timer,
        emote_active=emote,
        emote_time=emote_time,
        current_emote_bmp=current_emote_bmp,
        current_emote_timer=current_emote_timer,
        display=display,
        target_matrix=eye_matrix,
        idle_bmp="/faces/eye.bmp",
        verbose=VERBOSE,
    )

    if emote_started:
        boop = False
        boop_count = 0
        eye_closed = False

    # boop
    if not emote:
        if APDS_ON:
            if apds.get_value() > 200:
                if not boop:
                    display.load_bmp_into_matrix(eye_matrix, "/faces/eye_open.bmp")
                boop = True
                boop_count = 0
                eye_closed = False
                if VERBOSE:
                    print("boop")

            elif boop:
                boop_count += 1

                if boop_count >= BOOP_TIMER:
                    boop = False
                    boop_count = 0
                    eye_closed = False
                    display.load_bmp_into_matrix(eye_matrix, "/faces/eye.bmp")

    if SSD1306_ON:
        split_emote_name = (str(current_emote_bmp)).split("/")
        oled.draw_status(boop=boop, emote=emote, emote_time=emote_time, emote_name=split_emote_name[-1])



    # debug print
    if VERBOSE:
        if ACCELEROMETER_ON:
            print(f"Accelerometer: {accelerometer.derivation()}")

        if MIC_ON:
            print(f"Mic: {mic.get_value()}")

        if APDS_ON:
            # print(apds.scan())
            #print(apds.get_color())
            print(f"APDS: {apds.get_value()}")

        print("----")
    
    
    display.refresh()
    time.sleep(0.1)
