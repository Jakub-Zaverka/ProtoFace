"""Program cte akcelerometr LIS3DH a vraci pohyb proti zkalibrovane poloze."""

# Modul meri relativni pohyb, ne absolutni polohu v prostoru.
import adafruit_lis3dh
import time
from I2C_sim import get_i2c

SAMPLE_SIZE = 20
LIS3DH_ADDRESSES = (0x19, 0x18)


class Accelerometer:
    """Meri zrychleni a pocita odchylku od klidove polohy."""

    def __init__(self):
        """Inicializuje senzor a ulozi vychozi klidove hodnoty."""
        # Pri startu se nejdriv najde spravna I2C adresa a pak se udela kalibrace.
        self.i2c = self._get_i2c()
        self._missing_reported = False
        self.sensor = self._initialize_sensor()
        self.axis = [0, 0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.avg_x = 0
        self.avg_y = 0
        self.avg_z = 0
        if self.sensor is not None:
            self.__calibrate__()
            self.__get_messurements__()

    def _get_i2c(self):
        """Vrati dostupnou hardwarovou I2C sbernici."""
        return get_i2c()

    def _initialize_sensor(self):
        """Zkusi podporovane adresy LIS3DH a vrati prvni funkcni variantu."""
        # Nektere moduly pouzivaji 0x19, jine 0x18.
        for address in LIS3DH_ADDRESSES:
            try:
                sensor = adafruit_lis3dh.LIS3DH_I2C(self.i2c, address=address)
                sensor.range = adafruit_lis3dh.RANGE_2_G
                self._missing_reported = False
                return sensor
            except (OSError, ValueError):
                pass

        detected_addresses = self._scan_i2c_addresses()
        if not self._missing_reported:
            print(
                "LIS3DH nebyl nalezen na adresach 0x19 ani 0x18. "
                f"Na I2C jsou videt adresy: {detected_addresses}"
            )
            self._missing_reported = True
        return None

    def _scan_i2c_addresses(self):
        """Vrati aktualne nalezene I2C adresy pro diagnostiku."""
        try:
            while not self.i2c.try_lock():
                pass

            try:
                return [hex(address) for address in self.i2c.scan()]
            finally:
                self.i2c.unlock()
        except OSError:
            return []
    
    def print_axis(self):
        """Vypise posledni surove osy pro rychly debug."""
        self.__get_messurements__()
        print(self.x, self.y, self.z)

    def __get_messurements__(self):
        """Aktualizuje ulozene surove hodnoty os ze senzoru."""
        if self.sensor is None:
            return False

        try:
            self.axis = self.sensor.acceleration
        except OSError:
            self.sensor = self._initialize_sensor()
            return False

        self.x = self.axis[0]
        self.y = self.axis[1]
        self.z = self.axis[2]
        return True

    def __calibrate__(self):
        """Zprumeruje vice vzorku a urci klidovou polohu senzoru."""
        suma_x = suma_y = suma_z = 0
        # Klidova poloha vznikne jako prumer nekolika po sobe jdoucich vzorku.
        for _ in range(SAMPLE_SIZE):
            if self.sensor is None:
                return False

            try:
                self.axis = self.sensor.acceleration
            except OSError:
                self.sensor = self._initialize_sensor()
                return False

            self.x = self.axis[0]
            self.y = self.axis[1]
            self.z = self.axis[2]
            suma_x += self.x
            suma_y += self.y
            suma_z += self.z
            time.sleep(0.05)
        
        self.avg_x = suma_x/SAMPLE_SIZE
        self.avg_y = suma_y/SAMPLE_SIZE
        self.avg_z = suma_z/SAMPLE_SIZE
        return True

    def derivation(self):
        """Vrati zaokrouhlenou odchylku od zkalibrovaneho zakladniho stavu."""
        if self.sensor is None:
            self.sensor = self._initialize_sensor()
            if self.sensor is None or not self.__calibrate__():
                return None

        if not self.__get_messurements__():
            return None

        derivation_x = self.x - self.avg_x
        derivation_y = self.y - self.avg_y
        derivation_z = self.z - self.avg_z

        # Aplikace pouziva jen relativni pohyb, prevod jednotek tu neni potreba.
        # derivation_x *= 100
        # derivation_y *= 100
        # derivation_z *= 100

        # Zaokrouhleni zjednodusi prahovani pohybu v hlavni smycce.
        derivation_x = round(derivation_x,2)
        derivation_y = round(derivation_y,2)
        derivation_z = round(derivation_z,2)
        return [derivation_x, derivation_y, derivation_z]
