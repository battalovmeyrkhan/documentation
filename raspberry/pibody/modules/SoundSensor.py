from machine import Pin, ADC

adc_pins = [26, 27, 28]

class SoundSensor():
    def __init__(self, analog_pin, digital_pin):
        """Sound Sensor Module can return analog or digital value of sound. Threshold of Digital value of sound is defined by a switch on a module."""
        self._digital = Pin(digital_pin, Pin.IN)
        if analog_pin not in adc_pins:
            print("Recommended to use sound sensor on slots C or F. Ignore it if you plan on using only read_digital() function")
        else:
            self._analog = ADC(Pin(analog_pin))
    
    def read_digital(self) -> int: 
        """
            Returns digital value of sound sensor: 0 or 1
        """
        return self._digital.value()
    
    def read_analog(self) -> float:
        """
            Returns analog value of sound sensor: from 0 to 1.
        """
        return self._analog.read_u16() / 65536
    
    
    def read(self) -> tuple:
        """
            Returns tuple with digital and analog values of sound sensor. (d, a)
        """
        d = self.read_digital()
        a = self.read_analog()
        return (d, a)
