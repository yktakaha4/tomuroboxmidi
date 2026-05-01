from typing import Final

# C3 = MIDI 60 (Middle C, 261.6 Hz)

N20_VALID: Final[frozenset[int]] = frozenset(
    {
        60,
        62,
        64,
        65,
        67,
        69,
        71,  # C3-B3 (white keys)
        72,
        74,
        76,
        77,
        79,
        81,
        83,  # C4-B4 (white keys)
        84,
        86,
        88,
        89,
        91,
        93,  # C5-A5 (white keys)
    }
)

N40_VALID: Final[frozenset[int]] = frozenset(
    set(range(53, 106))
    - {54, 56, 58, 61}
    # 53=F2, 105=A6
    # excluded: F#2(54), G#2(56), A#2(58), C#3(61)
)

MODEL_MAP: Final[dict[str, frozenset[int]]] = {
    "n20": N20_VALID,
    "n40": N40_VALID,
}
