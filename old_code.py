import board
import analogio
import pwmio
import time

led = pwmio.PWMOut(board.A1, frequency=1000)
pot = analogio.AnalogIn(board.A2)

while True:
    led.duty_cycle = pot.value
    time.sleep(0.01)
