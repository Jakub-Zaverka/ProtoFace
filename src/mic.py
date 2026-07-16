"""Program cte mikrofon pres ADS1115 na I2C a vraci hlasitost proti klidu."""

# Mikrofon tu slouzi jen jako jednoducha detekce aktivity, ne pro zpracovani audia.
import time
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from I2C_sim import get_i2c

ADS_ADDRESS = 0x48
ADS_CHANNEL = getattr(ADS, "P0", 0)
ADS_GAIN = 1
ADS_DATA_RATE = 860
SAMPLE_SIZE = 20


class Microphone:
    """Meri odchylku mikrofonu z ADS1115 od zkalibrovaneho klidoveho stavu."""

    def __init__(self):
        """Inicializuje ADS1115 kanal mikrofonu a zmeri baseline."""
        # Pri startu se ulozi klidova hodnota, ke ktere se pozdeji porovnava aktualni signal.
        self.ads = None
        self.mic = None
        self._initialize_sensor()
        self.avg_value = self.__calibrate__()

    def _initialize_sensor(self):
        """Vytvori ADS1115 na sdilene I2C sbernici."""
        self.ads = ADS.ADS1115(get_i2c(), address=ADS_ADDRESS)
        self.ads.gain = ADS_GAIN
        self.ads.data_rate = ADS_DATA_RATE
        self.mic = AnalogIn(self.ads, ADS_CHANNEL)

    def get_value(self):
        """Vrati aktualni normalizovanou uroven aktivity mikrofonu."""
        # Vysledkem je jednoducha relativni odchylka vhodna pro prahovani mluvicich ust.
        try:
            return round(abs(self.mic.value - self.avg_value) / 1000, 2)
        except OSError:
            self._initialize_sensor()
            self.avg_value = self.__calibrate__()
            return 0
    
    def __calibrate__(self):
        """Zprumeruje vice vzorku a urci klidovou uroven mikrofonu."""
        total = 0
        for _ in range(SAMPLE_SIZE):
            total += self.mic.value
            time.sleep(0.05)
        return total / SAMPLE_SIZE
