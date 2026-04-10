import time

from display import Display
import adafruit_imageload
import displayio


display = Display()

nose_matrix = display.create_matrix(
    name="nose",
    position_x=5,
    position_y=5,
    matrix_width=4,
    matrix_height=4,
)

# display.update_matrix(
#     nose_matrix,
#     [[1,1,1,1],
#      [0,1,1,0],
#      [0,1,1,0],
#      [1,0,0,1]],
# )

eye_matrix = display.create_matrix(
    name="eye",
    position_x=31,
    position_y=0,
    matrix_width=32,
    matrix_height=16,
)

eye_bitmap, palette = adafruit_imageload.load(
    "/protogen_eye_32x16.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette,
)




display.update_matrix(eye_matrix, eye_bitmap)

print(display.matrix_to_list(nose_matrix))

display.refresh()

while True:
    time.sleep(1)
