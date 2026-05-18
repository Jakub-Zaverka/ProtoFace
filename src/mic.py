"""Program cte analogovy mikrofon a vraci hlasitost proti klidove hladine."""

# Mikrofon tu slouzi jen jako jednoducha detekce aktivity, ne pro zpracovani audia.
import board
import analogio
import time

MIC_PIN = board.A3
SAMPLE_SIZE = 20


class Microphone:
    """Meri odchylku mikrofonu od zkalibrovaneho klidoveho stavu."""

    def __init__(self):
        """Inicializuje analogovy vstup mikrofonu a zmeri baseline."""
        # Pri startu se ulozi klidova hodnota, ke ktere se pozdeji porovnava aktualni signal.
        self.mic = analogio.AnalogIn(MIC_PIN)
        self.avg_value = self.__calibrate__()

    def get_value(self):
        """Vrati aktualni normalizovanou uroven aktivity mikrofonu."""
        # Vysledkem je jednoducha relativni odchylka vhodna pro prahovani mluvicich ust.
        return round(abs(self.mic.value - self.avg_value)/1000,2)
    
    def __calibrate__(self):
        """Zprumeruje vice vzorku a urci klidovou uroven mikrofonu."""
        total = 0
        for _ in range(SAMPLE_SIZE):
            total += self.mic.value
            time.sleep(0.05)
        return total / SAMPLE_SIZE
