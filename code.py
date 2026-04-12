import time
from display import Display
from accelerometer import Accelerometer
from mic import Microphone
from I2C_sim import APDSSensor
from I2C_sim import OLEDDisplay
import board
import digitalio



ACCELEROMETER_ON = True
MIC_ON = True
APDS_ON = True
SSD1306_ON = True
VERBOSE = False
MIN_MOVEMENT = 0.5

display = Display()
if ACCELEROMETER_ON:
    accelerometer = Accelerometer()

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

EMOTE_TIMER = 10
emote_time = 0
emote = False


def handle_emote(
    button_pressed,
    emote_active,
    emote_time,
    display,
    target_matrix,
    active_bmp,
    idle_bmp,
    timer_limit,
    verbose=False,
):
    if button_pressed:
        if not emote_active:
            display.load_bmp_into_matrix(target_matrix, active_bmp)
        emote_active = True
        emote_time = 0
        if verbose:
            print("emote")
            print("pressed down")
    elif emote_active:
        emote_time += 1

        if emote_time >= timer_limit:
            emote_active = False
            emote_time = 0
            display.load_bmp_into_matrix(target_matrix, idle_bmp)

    return emote_active, emote_time


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


    if SSD1306_ON:
        oled.show_text("Test")

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


    #Emote
    emote, emote_time = handle_emote(
        button_pressed=not btn_down.value,
        emote_active=emote,
        emote_time=emote_time,
        display=display,
        target_matrix=eye_matrix,
        active_bmp="/faces/sleep.bmp",
        idle_bmp="/faces/eye.bmp",
        timer_limit=EMOTE_TIMER,
        verbose=VERBOSE,
    )

    emote, emote_time = handle_emote(
        button_pressed=not btn_up.value,
        emote_active=emote,
        emote_time=emote_time,
        display=display,
        target_matrix=eye_matrix,
        active_bmp="/faces/cross.bmp",
        idle_bmp="/faces/eye.bmp",
        timer_limit=EMOTE_TIMER,
        verbose=VERBOSE,
    )



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
