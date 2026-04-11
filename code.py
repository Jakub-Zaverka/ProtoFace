import time
from display import Display
from accelerometer import Accelerometer
from mic import Microphone


MIC_ON = True
ACCELEROMETER_ON = False
VERBOSE = True
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
    matrix_width=32,
    matrix_height=16,
)

display.load_bmp_into_matrix(eye_matrix, "/protogen_eye_32x16.bmp")


display.refresh()


if MIC_ON:
    mic = Microphone()



while True:
    #if movement
    if ACCELEROMETER_ON:
        if abs(accelerometer.derivation()[0]) > MIN_MOVEMENT or abs(accelerometer.derivation()[1]) > MIN_MOVEMENT or abs(accelerometer.derivation()[2] > MIN_MOVEMENT):
            print("move")
            #correct accelerometer setting
            eye_matrix["tile"].x -= int(accelerometer.derivation()[0])
            eye_matrix["tile"].y += int(accelerometer.derivation()[1])


    if VERBOSE:
        if ACCELEROMETER_ON:
            print(accelerometer.derivation())

        if MIC_ON:
            print(mic.get_value())

        print("----")
    
    
    display.refresh()
    time.sleep(0.1)