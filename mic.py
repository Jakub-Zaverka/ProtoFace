import board
import analogio
import time

MIC_PIN = board.A3
SAMPLE_SIZE = 20

class Microphone:
    def __init__(self):
        self.mic = analogio.AnalogIn(MIC_PIN)
        self.avg_value = self.__calibrate__()

    def get_value(self):
        return round(abs(self.mic.value - self.avg_value)/1000,2)
    
    def __calibrate__(self):
        total = 0
        for _ in range(SAMPLE_SIZE):
            total += self.mic.value
            time.sleep(0.05)
        return total / SAMPLE_SIZE
