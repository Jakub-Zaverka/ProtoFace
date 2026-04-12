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

whole_matrix["tile"].hidden = True

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


btn_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
btn_up = digitalio.DigitalInOut(board.BUTTON_UP)
btn_down.switch_to_input(pull=digitalio.Pull.UP)
btn_up.switch_to_input(pull=digitalio.Pull.UP)

# Emote logic:
# Each region tracks one display area and remembers its current emote state.
# In every loop we prepare requested_* values for each region:
#   requested_*_bmp   -> what should be shown in that region this loop
#   requested_*_timer -> how long the emote should stay active
# emotes.update_emote() is the only place that starts, refreshes and ends emotes.
# When an emote ends, the region returns to its idle source automatically.
EMOTE_TIMER = 10
BLINK_EMOTE_TIMER = max(1, BLINK_TIME_SET // 6)

# Prebuilt emote sources for the eye and mouth regions.
EYE_IDLE_EMOTE = emotes.create_image_emote("/faces/eye.bmp", "eye")
EYE_SLEEP_EMOTE = emotes.create_image_emote("/faces/sleep.bmp", "sleep")
EYE_BLINK_EMOTE = emotes.create_image_emote("/faces/eye_blink.bmp", "blink")
EYE_BOOP_EMOTE = emotes.create_image_emote("/faces/eye_open.bmp", "boop")
MOUTH_IDLE_EMOTE = emotes.create_image_emote("/faces/mouth.bmp", "mouth")
MOUTH_SPEAK_EMOTE = emotes.create_image_emote("/faces/mouth_speak.bmp", "speak")

def set_face_hidden(hidden):
    # Whole-screen emotes temporarily hide the normal face regions below them.
    eye_matrix["tile"].hidden = hidden
    nose_matrix["tile"].hidden = hidden
    mouth_matrix["tile"].hidden = hidden


# Each region binds one logical emote channel to one physical matrix.
eye_region = emotes.create_region("eye", eye_matrix, EYE_IDLE_EMOTE)
nose_region = emotes.create_region("nose", nose_matrix, "/faces/nose.bmp")
mouth_region = emotes.create_region("mouth", mouth_matrix, MOUTH_IDLE_EMOTE)
whole_region = emotes.create_region("whole", whole_matrix, hidden_when_idle=True)

while True:
    
    #if movement
    if ACCELEROMETER_ON and not whole_region["active"]:
        if abs(accelerometer.derivation()[0]) > MIN_MOVEMENT or abs(accelerometer.derivation()[1]) > MIN_MOVEMENT or abs(accelerometer.derivation()[2] > MIN_MOVEMENT):
            print("move")
            #correct accelerometer setting
            eye_matrix["tile"].x -= int(accelerometer.derivation()[0])
            eye_matrix["tile"].y += int(accelerometer.derivation()[1])
            nose_matrix["tile"].x -= int(accelerometer.derivation()[0])
            nose_matrix["tile"].y += int(accelerometer.derivation()[1])
            mouth_matrix["tile"].x -= int(accelerometer.derivation()[0])
            mouth_matrix["tile"].y += int(accelerometer.derivation()[1])
            whole_matrix["tile"].x -= int(accelerometer.derivation()[0])
            whole_matrix["tile"].y += int(accelerometer.derivation()[1])
        else:
            eye_matrix["tile"].x = 31
            eye_matrix["tile"].y = 0
            nose_matrix["tile"].x = 0
            nose_matrix["tile"].y = 0
            mouth_matrix["tile"].x = 0
            mouth_matrix["tile"].y = 16
            whole_matrix["tile"].x = 0
            whole_matrix["tile"].y = 0
    


    #Emote
    # Per-loop emote requests. None means "no new request for this region now".
    requested_eye_bmp = None
    requested_eye_timer = 0
    requested_nose_bmp = None
    requested_nose_timer = 0
    requested_mouth_bmp = None
    requested_mouth_timer = 0
    requested_whole_bmp = None
    requested_whole_timer = 0

    # Fullscreen clock emote has highest priority because it covers the whole face.
    if not btn_up.value and not whole_region["active"]:
        requested_whole_bmp = emotes.create_clock_emote(device_clock)
        requested_whole_timer = EMOTE_TIMER

    # if not btn_down.value and not whole_region["active"]:
    #     requested_eye_bmp = EYE_SLEEP_EMOTE
    #     requested_eye_timer = EMOTE_TIMER + 10

    if not btn_down.value and not whole_region["active"]:
        requested_eye_bmp = EYE_BOOP_EMOTE
        requested_eye_timer = EMOTE_TIMER
        requested_mouth_bmp = MOUTH_SPEAK_EMOTE
        requested_mouth_timer = EMOTE_TIMER

    # Microphone speaking is a short mouth emote refreshed while sound is present.
    if MIC_ON and not whole_region["active"]:
        if mic.get_value() > 5:
            requested_mouth_bmp = MOUTH_SPEAK_EMOTE
            requested_mouth_timer = 1
            if VERBOSE:
                print("speak")

    # Proximity sensor triggers the eye "boop" emote unless something else already won.
    if APDS_ON and not whole_region["active"] and requested_eye_bmp is None:
        if apds.get_value() > 200:
            requested_eye_bmp = EYE_BOOP_EMOTE
            requested_eye_timer = BOOP_TIMER

    # Blink is the fallback eye emote when nothing else uses the eyes.
    if not whole_region["active"] and requested_eye_bmp is None:
        if not eye_region["active"]:
            blink_time += 1
            if blink_time >= BLINK_TIME_SET:
                requested_eye_bmp = EYE_BLINK_EMOTE
                requested_eye_timer = BLINK_EMOTE_TIMER
                blink_time = 0
        elif emotes.get_emote_name(eye_region) != "blink":
            blink_time = 0

    nose_emote, nose_started = emotes.update_emote(
        display,
        nose_region,
        source=requested_nose_bmp,
        duration=requested_nose_timer,
        verbose=VERBOSE,
    )

    mouth_emote, mouth_started = emotes.update_emote(
        display,
        mouth_region,
        source=requested_mouth_bmp,
        duration=requested_mouth_timer,
        verbose=VERBOSE,
    )

    eye_emote, eye_started = emotes.update_emote(
        display,
        eye_region,
        source=requested_eye_bmp,
        duration=requested_eye_timer,
        verbose=VERBOSE,
    )

    whole_emote, whole_started = emotes.update_emote(
        display,
        whole_region,
        source=requested_whole_bmp,
        duration=requested_whole_timer,
        verbose=VERBOSE,
    )

    # Hide normal face parts while a whole-screen emote is active.
    set_face_hidden(whole_region["active"])

    if eye_started or nose_started or mouth_started or whole_started:
        # Restart blink cadence after any non-blink eye change begins.
        if emotes.get_emote_name(eye_region) != "blink":
            blink_time = 0



    #OLED screen
    if SSD1306_ON:
        # Show the most relevant active region on the status OLED.
        if whole_region["active"]:
            status_region = whole_region
        elif eye_region["active"]:
            status_region = eye_region
        elif nose_region["active"]:
            status_region = nose_region
        elif mouth_region["active"]:
            status_region = mouth_region
        else:
            status_region = eye_region

        boop_active = emotes.get_emote_name(eye_region) == "boop"
        oled.draw_status(
            boop=boop_active,
            emote=(
                eye_region["active"]
                or nose_region["active"]
                or mouth_region["active"]
                or whole_region["active"]
            ),
            emote_time=status_region["elapsed"],
            emote_name=emotes.get_emote_name(status_region),
            current_time=device_clock.get_time() if WIFI_ON else "--:--",
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
