import time

import adafruit_lis3dh
import board
import displayio

from face_display import FaceDisplay

CALIBRATION_SAMPLES = 20
BASELINE_ALPHA = 0.02
DISPLAY_SMOOTHING = 0.18
DEAD_ZONE = 0.0
PIXELS_PER_MS2_X = -2
PIXELS_PER_MS2_Y = -2

displayio.release_displays()


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


i2c = board.I2C()
sensor = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)
sensor.range = adafruit_lis3dh.RANGE_2_G

face = FaceDisplay()

print("Kalibrace...")
sx = sy = sz = 0.0
for _ in range(CALIBRATION_SAMPLES):
    x, y, z = sensor.acceleration
    sx += x
    sy += y
    sz += z
    time.sleep(0.05)

bx = sx / CALIBRATION_SAMPLES
by = sy / CALIBRATION_SAMPLES
bz = sz / CALIBRATION_SAMPLES

print("Matrix Portal S3 akcelerometr je pripraveny.")

# Vyhlazeny posun se drzi jako float a na pixely se prevadi az na konci.
smooth_offset_x = 0.0
smooth_offset_y = 0.0

#mainloop
while True:
    x, y, z = sensor.acceleration

    bx = bx * (1.0 - BASELINE_ALPHA) + x * BASELINE_ALPHA
    by = by * (1.0 - BASELINE_ALPHA) + y * BASELINE_ALPHA
    bz = bz * (1.0 - BASELINE_ALPHA) + z * BASELINE_ALPHA

    dx = x - bx
    dy = y - by
    dz = z - bz

    # Mala odchylka kolem stredu se ignoruje, aby obraz nekmital.
    if abs(dx) < DEAD_ZONE:
        dx = 0.0
    if abs(dy) < DEAD_ZONE:
        dy = 0.0

    # Prevod fyzicke odchylky na cilovy posun v pixelech.
    target_offset_x = dx * PIXELS_PER_MS2_X
    target_offset_y = dy * PIXELS_PER_MS2_Y

    # Plynule priblizovani k cilovemu posunu omezi skakani.
    smooth_offset_x += (target_offset_x - smooth_offset_x) * DISPLAY_SMOOTHING
    smooth_offset_y += (target_offset_y - smooth_offset_y) * DISPLAY_SMOOTHING

    # Az tady se prevedou vyhlazene hodnoty na cele pixely.
    offset_x = clamp(int(round(smooth_offset_x)), -5, 5)
    offset_y = clamp(int(round(smooth_offset_y)), -5, 5)

    face.update(offset_x, offset_y)
    time.sleep(0.2)
