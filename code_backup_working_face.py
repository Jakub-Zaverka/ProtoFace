import board
import displayio
import time
import pulseio
import rgbmatrix
import framebufferio

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64,
    height=32,
    bit_depth=3,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_B1,
        board.MTX_G1,
        board.MTX_R2,
        board.MTX_B2,
        board.MTX_G2,
    ],
    addr_pins=[board.MTX_ADDRA, board.MTX_ADDRB, board.MTX_ADDRC, board.MTX_ADDRD],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
)

display = framebufferio.FramebufferDisplay(matrix)

display.brightness = 0
splash = displayio.Group()
display.root_group = splash

odb = displayio.OnDiskBitmap('images/face.bmp')
face = displayio.TileGrid(odb, pixel_shader=odb.pixel_shader)
splash.append(face)
# Wait for the image to load.
display.refresh(target_frames_per_second=60)

# Fade up the backlight
for i in range(100):
    display.brightness = 0.01 * i
    time.sleep(0.05)

# Wait forever
while True:
    odb = displayio.OnDiskBitmap('images/face.bmp')
    face = displayio.TileGrid(odb, pixel_shader=odb.pixel_shader)
    splash.append(face)
    time.sleep(2)
    odb = displayio.OnDiskBitmap('images/blink.bmp')
    face = displayio.TileGrid(odb, pixel_shader=odb.pixel_shader)
    splash.append(face)
    time.sleep(10)
    pass