_SLOT_MAP = {
    'A': (0, 1),
    'B': (2, 3),
    'C': (28, 22),
    'D': (4, 5),
    'E': (6, 7),
    'F': (26, 27),
    'G': (16, 17),
    'H': (18, 19),
}

# Functions-helpers
def get_pins_by_slot(slot):
    if type(slot) == str:
        slot = slot.upper()[0]
        if slot not in _SLOT_MAP:
            raise ValueError(f"Invalid slot '{slot}'. Use A, B, C, D, E, or F")
        sda, scl = _SLOT_MAP[slot]
        return (sda, scl)
    elif type(slot) == tuple:
        return slot
    else:
        raise ValueError("Wrong slot type")

def get_pin(slot):
    if type(slot) == int:
        return slot
    elif type(slot) == str:
        return get_pins_by_slot(slot)[0]
    else:
        raise ValueError("Wrong slot type")
