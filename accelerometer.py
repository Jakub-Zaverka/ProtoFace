"""Helpers for reading and calibrating the onboard accelerometer."""

import adafruit_lis3dh
import time
from I2C_sim import get_i2c

SAMPLE_SIZE = 20
LIS3DH_ADDRESSES = (0x19, 0x18)


class Accelerometer:
    """Read acceleration values and expose movement relative to calibration."""

    def __init__(self):
        """Initialize state and capture the initial sensor baseline."""
        self.i2c = self._get_i2c()
        self.sensor = self._initialize_sensor()
        self.axis = [0, 0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.avg_x = 0
        self.avg_y = 0
        self.avg_z = 0
        self.__calibrate__()
        self.__get_messurements__()

    def _get_i2c(self):
        """Return the available hardware I2C bus."""
        return get_i2c()

    def _initialize_sensor(self):
        """Try supported LIS3DH I2C addresses and return the first match."""
        last_error = None
        for address in LIS3DH_ADDRESSES:
            try:
                sensor = adafruit_lis3dh.LIS3DH_I2C(self.i2c, address=address)
                sensor.range = adafruit_lis3dh.RANGE_2_G
                return sensor
            except ValueError as error:
                last_error = error

        detected_addresses = self._scan_i2c_addresses()
        raise ValueError(
            "LIS3DH nebyl nalezen na adresach 0x19 ani 0x18. "
            f"Na I2C jsou videt adresy: {detected_addresses}"
        ) from last_error

    def _scan_i2c_addresses(self):
        """Return currently detected I2C addresses for diagnostics."""
        while not self.i2c.try_lock():
            pass

        try:
            return [hex(address) for address in self.i2c.scan()]
        finally:
            self.i2c.unlock()
    
    def print_axis(self):
        """Print the latest raw axis values for quick debugging."""
        self.__get_messurements__()
        print(self.x, self.y, self.z)

    def __get_messurements__(self):
        """Refresh the cached raw acceleration values from the sensor."""
        self.axis = self.sensor.acceleration
        self.x = self.axis[0]
        self.y = self.axis[1]
        self.z = self.axis[2]

    def __calibrate__(self):
        """Average several samples to establish the resting baseline."""
        # kalibrace senzoru
        suma_x = suma_y = suma_z = 0
        for _ in range(SAMPLE_SIZE):
            self.axis = self.sensor.acceleration
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

    def derivation(self):
        """Return rounded acceleration deltas from the calibrated baseline."""
        self.__get_messurements__()
        derivation_x = self.x - self.avg_x
        derivation_y = self.y - self.avg_y
        derivation_z = self.z - self.avg_z

        # do cm/s^2
        # derivation_x *= 100
        # derivation_y *= 100
        # derivation_z *= 100

        #round
        derivation_x = round(derivation_x,2)
        derivation_y = round(derivation_y,2)
        derivation_z = round(derivation_z,2)
        return [derivation_x, derivation_y, derivation_z]
