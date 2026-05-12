from machine import Pin

_DIR_CW = const(0x10)  # Clockwise step
_DIR_CCW = const(0x20)  # Counter-clockwise step

# Rotary Encoder States
_R_START = const(0x0)
_R_CW_1 = const(0x1)
_R_CW_2 = const(0x2)
_R_CW_3 = const(0x3)
_R_CCW_1 = const(0x4)
_R_CCW_2 = const(0x5)
_R_CCW_3 = const(0x6)
_R_ILLEGAL = const(0x7)

_transition_table = [

    # |------------- NEXT STATE -------------|            |CURRENT STATE|
    # CLK/DT    CLK/DT     CLK/DT    CLK/DT
    #   00        01         10        11
    [_R_START, _R_CCW_1, _R_CW_1,  _R_START],             # _R_START
    [_R_CW_2,  _R_START, _R_CW_1,  _R_START],             # _R_CW_1
    [_R_CW_2,  _R_CW_3,  _R_CW_1,  _R_START],             # _R_CW_2
    [_R_CW_2,  _R_CW_3,  _R_START, _R_START | _DIR_CW],   # _R_CW_3
    [_R_CCW_2, _R_CCW_1, _R_START, _R_START],             # _R_CCW_1
    [_R_CCW_2, _R_CCW_1, _R_CCW_3, _R_START],             # _R_CCW_2
    [_R_CCW_2, _R_START, _R_CCW_3, _R_START | _DIR_CCW],  # _R_CCW_3
    [_R_START, _R_START, _R_START, _R_START]]             # _R_ILLEGAL

_transition_table_half_step = [
    [_R_CW_3,            _R_CW_2,  _R_CW_1,  _R_START],
    [_R_CW_3 | _DIR_CCW, _R_START, _R_CW_1,  _R_START],
    [_R_CW_3 | _DIR_CW,  _R_CW_2,  _R_START, _R_START],
    [_R_CW_3,            _R_CCW_2, _R_CCW_1, _R_START],
    [_R_CW_3,            _R_CW_2,  _R_CCW_1, _R_START | _DIR_CW],
    [_R_CW_3,            _R_CCW_2, _R_CW_3,  _R_START | _DIR_CCW],
    [_R_START,           _R_START, _R_START, _R_START],
    [_R_START,           _R_START, _R_START, _R_START]]

_STATE_MASK = const(0x07)
_DIR_MASK = const(0x30)

IRQ_RISING_FALLING = Pin.IRQ_RISING | Pin.IRQ_FALLING

def _wrap(value, incr, lower_bound, upper_bound):
    range = upper_bound - lower_bound + 1
    value = value + incr

    if value < lower_bound:
        value += range * ((lower_bound - value) // range + 1)

    return lower_bound + (value - lower_bound) % range


def _bound(value, incr, lower_bound, upper_bound):
    return min(upper_bound, max(lower_bound, value + incr))


def _trigger(rotary_instance):
    for listener in rotary_instance._listener:
        listener()


class RotaryEncoder(object):

    RANGE_UNBOUNDED = const(1)
    RANGE_WRAP = const(2)
    RANGE_BOUNDED = const(3)

    def __init__(
            self, 
            clk,
            dt,
            min_val=0, 
            max_val=10, 
            incr=1, 
            reverse=False, 
            range_mode=RANGE_UNBOUNDED, 
            half_step=False, 
            invert=False,
            pull_up=False
            ):
        
        self._clk_pin = clk
        self._dt_pin = dt
        self._min_val = min_val
        self._max_val = max_val
        self._incr = incr
        self._reverse = -1 if reverse else 1
        self._range_mode = range_mode
        self._value = min_val
        self._state = _R_START
        self._half_step = half_step
        self._invert = invert
        self._listener = []
        self._direction = 0
        self._old_value = 0
        
        
        if pull_up:
            self._pin_clk = Pin(self._clk_pin, Pin.IN, Pin.PULL_UP)
            self._pin_dt = Pin(self._dt_pin, Pin.IN, Pin.PULL_UP)
        else:
            self._pin_clk = Pin(self._clk_pin, Pin.IN)
            self._pin_dt = Pin(self._dt_pin, Pin.IN)
        self._hal_enable_irq()

    def _hal_enable_irq(self):
        self._pin_clk.irq(self._process_rotary_pins, IRQ_RISING_FALLING)
        self._pin_dt.irq(self._process_rotary_pins, IRQ_RISING_FALLING)

    def _hal_disable_irq(self):
        self._pin_clk.irq(None, 0)
        self._pin_dt.irq(None, 0)  

    def set(self, value=None, min_val=None, incr=None,
            max_val=None, reverse=None, range_mode=None):
        """Set encoder's configuration"""
        # disable DT and CLK pin interrupts
        self._hal_disable_irq()

        if value is not None:
            self._value = value
        if min_val is not None:
            self._min_val = min_val
        if max_val is not None:
            self._max_val = max_val
        if incr is not None:
            self._incr = incr
        if reverse is not None:
            self._reverse = -1 if reverse else 1
        if range_mode is not None:
            self._range_mode = range_mode
        self._state = _R_START

        # enable DT and CLK pin interrupts
        self._hal_enable_irq()

    def bound(self, min_val, max_val):
        """Bounds Encoder values in a range from min_val to max_val"""
        self._hal_disable_irq()
        self._value = min_val
        self._min_val = min_val
        self._max_val = max_val
        self._range_mode = self.RANGE_BOUNDED        
        self._hal_enable_irq()

    def wrap(self, min_val, max_val):
        """Wraps Encoder values in a range from min_val to max_val"""
        self._hal_disable_irq()
        self._value = min_val
        self._min_val = min_val
        self._max_val = max_val
        self._range_mode = self.RANGE_WRAP        
        self._hal_enable_irq()

    def free(self):
        """Default state of Encoder, resets bound and wrap mode."""
        self._hal_disable_irq()
        self._range_mode = self.RANGE_UNBOUNDED        
        self._hal_enable_irq()

    def toggle_direction(self):
        """Changes directions of encoder rotation"""
        self._hal_disable_irq()
        self._reverse = 1 if self._reverse == -1 else -1     
        self._hal_enable_irq()

    def set_incr(self, incr):
        """Changes increment value of encoder to incr. Default incr value: 1"""
        self._hal_disable_irq()
        self._incr = incr
        self._hal_enable_irq()
    
    def set_value(self, value):
        """Set's value of encoder to value variable"""
        self._hal_disable_irq()
        self._value = value
        self._hal_enable_irq()

    def bar(self, width=20, fill_char="#", empty_char=" "):
        """Prints encoder value in a bar format"""
        pos = int((self._value - self._min_val) / (self._max_val - self._min_val) * width)
        filled = fill_char * pos
        empty = empty_char * (width - pos)
        return f"[{filled}{empty}] {self._value}"
    
    def live_bar(self, width=20, fill_char="#", empty_char=" "):
        pos = int((self._value - self._min_val) / (self._max_val - self._min_val) * width)
        filled = fill_char * pos
        empty = empty_char * (width - pos)
        print(f"\r[{filled}{empty}] {self._value}   ", end="")

    def value(self):
        """Returns current value of encoder"""
        return self._value

    def old_value(self):
        return self._old_value

    def direction(self):
        """Returns last rotation direction of encoder"""
        return self._direction
    
    def reset(self):
        """Resets value of encoder to 0"""
        self._value = 0

    def close(self):
        """Disables encoder"""
        self._hal_disable_irq()

    def add_listener(self, l):
        """Append function as an argument. This function will be invoked once encoder is rotated"""
        self._listener.append(l)

    def remove_listener(self, l):
        """Removes function from listener. This function will no longer be invoked once encoder is rotated"""
        if l not in self._listener:
            raise ValueError('{} is not an installed listener'.format(l))
        self._listener.remove(l)
        
    def _process_rotary_pins(self, pin):
        self._old_value = self._value
        clk_dt_pins = (self._pin_clk.value() <<
                       1) | self._pin_dt.value()
                       
        if self._invert:
            clk_dt_pins = ~clk_dt_pins & 0x03
        # Determine next state
        if self._half_step:
            self._state = _transition_table_half_step[self._state &
                                                      _STATE_MASK][clk_dt_pins]
        else:
            self._state = _transition_table[self._state &
                                            _STATE_MASK][clk_dt_pins]
        direction = self._state & _DIR_MASK

        incr = 0
        if direction == _DIR_CW:
            incr = self._incr
            self._direction = 1
        elif direction == _DIR_CCW:
            incr = -self._incr
            self._direction = -1

        incr *= self._reverse

        if self._range_mode == self.RANGE_WRAP:
            self._value = _wrap(
                self._value,
                incr,
                self._min_val,
                self._max_val)
        elif self._range_mode == self.RANGE_BOUNDED:
            self._value = _bound(
                self._value,
                incr,
                self._min_val,
                self._max_val)
        else:
            self._value = self._value + incr

        try:
            if self._old_value != self._value and len(self._listener) != 0:
                _trigger(self)
        except:
            pass
