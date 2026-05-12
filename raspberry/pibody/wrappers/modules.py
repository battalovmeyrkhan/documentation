from ..modules.Buzzer import Buzzer as _Buzzer
from ..modules.PWM import PWM as _PWM
from ..modules.Joystick import Joystick as _Joystick
from ..modules.SoundSensor import SoundSensor as _SoundSensor
from ..modules.LEDTower import LEDTower as _LEDTower
from ..modules.RotaryEncoder import RotaryEncoder

from ..helper import get_pin, get_pins_by_slot


class Buzzer(_Buzzer):
    def __init__(self, slot):
        pin = get_pin(slot)        
        super().__init__(pin)

class PWM(_PWM):
    def __init__(self, slot):
        pin = get_pin(slot)
        super().__init__(pin)

class Joystick(_Joystick):
    def __init__(self, slot):
        pinX, pinY = get_pins_by_slot(slot)
        super().__init__(pinX, pinY)

class Encoder(RotaryEncoder):
    def __init__(self, slot):
        sda, scl = get_pins_by_slot(slot)
        super().__init__(clk=sda, dt=scl)
    
    def read(self):
        return self.value()

class SoundSensor(_SoundSensor):
    def __init__(self, slot):
        analog_pin, digital_pin = get_pins_by_slot(slot)
        super().__init__(analog_pin, digital_pin)

class LEDTower(_LEDTower):
    def __init__(self, slot=8):
        pin = get_pin(slot)
        super().__init__(pin)
