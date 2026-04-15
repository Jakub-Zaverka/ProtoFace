"""Helpers for reading and calibrating the onboard microphone."""

import board
import analogio
import time

MIC_PIN = board.A3
SAMPLE_SIZE = 20


class Microphone:
    """Read microphone amplitude relative to a calibrated idle level."""

    def __init__(self):
        """Initialize the analog microphone input and baseline value."""
        self.mic = analogio.AnalogIn(MIC_PIN)
        self.avg_value = self.__calibrate__()

    def get_value(self):
        """Return the current normalized microphone activity level."""
        return round(abs(self.mic.value - self.avg_value)/1000,2)
    
    def __calibrate__(self):
        """Average several samples to determine the idle microphone level."""
        total = 0
        for _ in range(SAMPLE_SIZE):
            total += self.mic.value
            time.sleep(0.05)
        return total / SAMPLE_SIZE
