from machine import Pin
from machine import ADC as _ADC
from pibody.helper import get_pin

class LED(Pin):
    def __init__(self, slot):
        pin = get_pin(slot)
        super().__init__(pin, Pin.OUT)
    
class ButtonLike(Pin):
    def __init__(self, slot):
        pin = get_pin(slot)
        super().__init__(pin, Pin.IN)

    def read(self):
        """Returns value of sensor: 0 or 1"""
        return super().value()
    
class ADC(_ADC):
    def __init__(self, slot):
        pin = get_pin(slot)
        super().__init__(Pin(pin))
    
    def read(self):
        """Returns value of sensor from 0 to 1"""
        return self.read_u16() / 65535
    

