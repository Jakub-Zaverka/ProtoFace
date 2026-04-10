import board
import adafruit_lis3dh
import time

i2c = board.I2C()
sensor = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)
sensor.range = adafruit_lis3dh.RANGE_2_G

SAMPLE_SIZE = 20

class Accelerometer:
    def __init__(self):
        self.axis = [0, 0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.avg_x = 0
        self.avg_y = 0
        self.avg_z = 0
        self.__calibrate__()
        self.__get_messurements__()
    
    def print_axis(self):
        self.__get_messurements__()
        print(self.x, self.y, self.z)

    def __get_messurements__(self):
        self.axis = sensor.acceleration
        self.x = self.axis[0]
        self.y = self.axis[1]
        self.z = self.axis[2]

    def __calibrate__(self):
        # kalibrace senzoru
        suma_x = suma_y = suma_z = 0
        for _ in range(SAMPLE_SIZE):
            self.axis = sensor.acceleration
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
