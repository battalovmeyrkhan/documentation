from motor import Motor, FullStepMotor, HalfStepMotor
from machine import Pin
from time import sleep

btn = Pin(21, Pin.IN)
btn_reverse = Pin(20, Pin.IN)
m = FullStepMotor.frompins(0, 1, 2, 3, stepms=2)

class Dispencer(FullStepMotor):
    def __init__(self, stepms: int = 2):
        self.motor = FullStepMotor.frompins(0, 1, 2, 3, stepms=stepms)

    def dispense(self):
        self.motor.step(50)

    def dispense_reverse(self):
        self.motor.step(-50)

dispencer = Dispencer()

while True:
    if btn.value():
        dispencer.dispense()
        
    elif btn_reverse.value():
        dispencer.dispense_reverse()

