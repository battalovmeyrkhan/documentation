from .PWM import PWM
from math import e
from time import sleep

def volume2duty(volume):
    return (volume ** e / 2)

class Buzzer(PWM):
    def __init__(self, pin):
        super().__init__(pin)
        self._volume = 0.5
        self.freq(560)

    def volume(self, volume=None):
        if volume is None:
            return self._volume
        if not 0 <= volume <= 1.0:
            raise ValueError("Volume must be between 0 and 1.0")
        self._volume = volume
        duty = volume ** e
        self.duty(duty / 2)

    def make_sound(self, freq, volume, duration):
        self.freq(freq)
        self.duty(volume2duty(volume))
        sleep(duration)
        self.duty(0)

    def beep(self):
        self.make_sound(1000, self._volume, 0.1)
    
    def boop(self):
        self.make_sound(500, self._volume, 0.1)
        
    def on(self):
        self.volume(self._volume)

    def off(self):
        self.duty(0)

