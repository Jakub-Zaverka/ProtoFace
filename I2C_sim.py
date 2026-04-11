import board
import busio
import time
import analogio

i2c = busio.I2C(board.A1, board.A2)  # SCL, SDA

mic = analogio.AnalogIn(board.A3)



while not i2c.try_lock():
    pass

print("I2C adresy:", [hex(x) for x in i2c.scan()])

i2c.unlock()

while True:
    print(mic.value)
    time.sleep(0.01)
