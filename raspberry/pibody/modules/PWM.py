from machine import PWM as _BASE_PWM
from machine import Pin


def u16_to_float(u16 : int):
    return u16 / 65536

class PWM(_BASE_PWM):    
   
    def __init__(self, pin:int):        
        super().__init__(Pin(pin))
        self._duty = u16_to_float(self.duty_u16())


    def duty(self, duty_cycle:float|None = None):
        """Set duty_cycle of PWM object in range from 0 to 1. """
        if duty_cycle == None:
            return self._duty
        if duty_cycle < 0 or duty_cycle > 1: 
            raise ValueError("duty_cycle must be in range from 0 to 1")
        self._duty = int(duty_cycle * 65536)
        return self.duty_u16(self._duty)


