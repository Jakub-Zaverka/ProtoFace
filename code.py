import time
from display import Display
from accelerometer import Accelerometer
from mic import Microphone
from I2C_sim import APDSSensor
from I2C_sim import OLEDDisplay



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
blink_time = 0
eye_closed = False

while True:
    #if movement
    if ACCELEROMETER_ON:
        if abs(accelerometer.derivation()[0]) > MIN_MOVEMENT or abs(accelerometer.derivation()[1]) > MIN_MOVEMENT or abs(accelerometer.derivation()[2] > MIN_MOVEMENT):
            print("move")
            #correct accelerometer setting
            eye_matrix["tile"].x -= int(accelerometer.derivation()[0])
            eye_matrix["tile"].y += int(accelerometer.derivation()[1])
        else:
            eye_matrix["tile"].x = 31
            eye_matrix["tile"].y = 0
            pass
    
    if MIC_ON:
        if mic.get_value() > 20:
            display.load_bmp_into_matrix(mouth_matrix, "/faces/mouth_speak.bmp")
            print("speak")
        else:
            display.load_bmp_into_matrix(mouth_matrix, "/faces/mouth.bmp")

    


    if blink_time >= BLINK_TIME_SET and not eye_closed:
        eye_closed = True
        display.load_bmp_into_matrix(eye_matrix, "/faces/eye_blink.bmp")
        blink_time = 0

    elif blink_time >= BLINK_TIME_SET // 6 and eye_closed:
        eye_closed = False
        display.load_bmp_into_matrix(eye_matrix, "/faces/eye.bmp")
        blink_time = 0
        print("blink")

    else:
        blink_time += 1


    if SSD1306_ON:
        oled.show_text("Test")

    if APDS_ON:
        if apds.get_value() > 200:
            #boop
            pass

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
