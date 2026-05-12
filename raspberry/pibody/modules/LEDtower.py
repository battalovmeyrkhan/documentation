from machine import Pin
from neopixel import NeoPixel

class LEDTower(NeoPixel):
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    PINK = (255, 192, 203)
    LIME = (0, 255, 128)
    TEAL = (0, 128, 128)
    BROWN = (139, 69, 19)

    def __init__(self, pin=8, led_num=8):
        super().__init__(Pin(pin), led_num)
        self.fill(self.BLACK)
        self.write()

    
    
