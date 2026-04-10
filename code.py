import time
from display import Display
from accelerometer import Accelerometer


display = Display()
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

display.load_bmp_into_matrix(nose_matrix, "/protogen_eye_32x16.bmp")



# display.update_matrix(eye_matrix, eye_bitmap)

# print(display.matrix_to_list(nose_matrix))

display.refresh()

while True:
    time.sleep(0.1)
    print(accelerometer.derivation())
