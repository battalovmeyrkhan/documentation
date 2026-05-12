from machine import PWM, Pin

class Servo:
    def __init__(self, pin):
        self.servo = PWM(Pin(pin))

        self._freq = 50
        self.servo.freq(self._freq)

    def freq(self, frequency=None):
        if frequency is None:
            return self._freq
        else:
            self._freq = frequency
            self.servo.freq(frequency)

    def duty_u16(self, duty_cycle):
        duty_percent = duty_cycle / 65535
        pulse_ms = duty_percent * (1 / self._freq * 1000)
        angle = (pulse_ms - 0.5) / (2.5 - 0.5) * 180

        if 0 <= angle and angle <= 180:
            self._angle = angle
        else:
            self._angle = None

        self._duty_cycle = duty_cycle
        self.servo.duty_u16(duty_cycle)


    def angle(self, angle=None):
        if angle is None:
            return self._angle
        else:
            self._angle = angle
            proportion = angle / 180
            pulse_width = proportion * 2 + 0.5
            duty = int(pulse_width * 65535 / (1 / self._freq * 1000))
            self._duty_cycle = duty
            self.servo.duty_u16(duty)

    def on(self):
        self.servo.init()
        
    def off(self):
        self.servo.deinit()
