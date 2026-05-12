from machine import I2C, SoftI2C, Pin
from pibody.helper import get_pins_by_slot

from BME280 import BME280
from MPU6050 import MPU6050
from LSM6DS3 import LSM6DS3
from VEML6040 import VEML6040
from VL53L0X import VL53L0X
from SSD1306 import SSD1306



def get_i2c(slot, hard_i2c=False):
    if type(slot) == I2C or type(slot) == SoftI2C:
        return slot
    sda, scl = get_pins_by_slot(slot)
    if hard_i2c:
        return I2C(scl=Pin(scl), sda=Pin(sda))
    else:
        return SoftI2C(scl=Pin(scl), sda=Pin(sda))



class ClimateSensor(BME280):
    def __init__(self, slot, hard_i2c=False):
        super().__init__(get_i2c(slot, hard_i2c))


def GyroAccel(slot, hard_i2c=False):
    i2c = get_i2c(slot, hard_i2c)
    if 0x68 in i2c.scan():
        return MPU6050(i2c)
    elif 0x6A in i2c.scan():
        return LSM6DS3(i2c)
    else:
        raise ValueError(f"Invalid i2c address '{i2c.scan()}' for slot '{slot}'")  

class ColorSensor(VEML6040):
    def __init__(self, slot, hard_i2c=False):
        super().__init__(get_i2c(slot, hard_i2c))

class DistanceSensor(VL53L0X):
    def __init__(self, slot, hard_i2c=False):
        super().__init__(get_i2c(slot, hard_i2c))

class OLED(SSD1306):
    def __init__(self, slot, hard_i2c=False, width=128, height=64):
        super().__init__(get_i2c(slot, hard_i2c), width=width, height=height)

