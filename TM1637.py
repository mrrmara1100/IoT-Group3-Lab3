# TM1637 4-digit 7-segment display driver for MicroPython (ESP32)
#
# Upload this file to the ESP32 (Thonny: File -> Save as -> MicroPython device,
# name it TM1637.py) so that "import TM1637" works in the task files.
#
# Usage:
#   import TM1637
#   from machine import Pin
#   tm = TM1637.TM1637(clk=Pin(22), dio=Pin(21))
#   tm.brightness(7)     # 0 (dim) .. 7 (bright)
#   tm.number(42)        # shows "  42"
#   tm.show("----")      # shows text (digits, '-', space, some letters)
#   tm.clear()

from machine import Pin
from time import sleep_us

_CMD_DATA = 0x40   # data command: write to display, auto-increment address
_CMD_ADDR = 0xC0   # address command: start at digit 0
_CMD_DISP = 0x88   # display control: display ON + brightness (0-7)
_DELAY_US = 10     # bit delay

# Segment bits: 0b(DP)GFEDCBA
#      A
#     ---
#  F |   | B
#     -G-
#  E |   | C
#     ---
#      D
_DIGITS = (0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F)
_CHARS = {
    " ": 0x00, "-": 0x40, "_": 0x08,
    "A": 0x77, "B": 0x7C, "C": 0x39, "D": 0x5E, "E": 0x79, "F": 0x71,
    "H": 0x76, "L": 0x38, "N": 0x54, "O": 0x3F, "P": 0x73, "R": 0x50,
    "S": 0x6D, "U": 0x3E, "Y": 0x6E,
}


class TM1637:
    def __init__(self, clk, dio, brightness=7):
        self.clk = clk
        self.dio = dio
        self._brightness = max(0, min(7, brightness))
        self.clk.init(Pin.OUT, value=1)
        self.dio.init(Pin.OUT, value=1)
        sleep_us(_DELAY_US)
        self.clear()

    # ---------- low-level protocol ----------
    def _start(self):
        # Start condition: DIO goes LOW while CLK is HIGH
        self.dio(0)
        sleep_us(_DELAY_US)
        self.clk(0)
        sleep_us(_DELAY_US)

    def _stop(self):
        # Stop condition: DIO goes HIGH while CLK is HIGH
        self.dio(0)
        sleep_us(_DELAY_US)
        self.clk(1)
        sleep_us(_DELAY_US)
        self.dio(1)
        sleep_us(_DELAY_US)

    def _write_byte(self, b):
        # Send 8 bits, least significant bit first
        for i in range(8):
            self.dio((b >> i) & 1)
            sleep_us(_DELAY_US)
            self.clk(1)
            sleep_us(_DELAY_US)
            self.clk(0)
            sleep_us(_DELAY_US)
        # 9th clock: the TM1637 pulls DIO low to acknowledge
        self.dio.init(Pin.IN)
        self.clk(1)
        sleep_us(_DELAY_US)
        self.clk(0)
        sleep_us(_DELAY_US)
        self.dio.init(Pin.OUT, value=0)

    def _send_command(self, cmd):
        self._start()
        self._write_byte(cmd)
        self._stop()

    # ---------- public API ----------
    def write(self, segments, pos=0):
        """Write raw segment bytes starting at digit position pos (0-3)."""
        self._send_command(_CMD_DATA)
        self._start()
        self._write_byte(_CMD_ADDR | pos)
        for seg in segments:
            self._write_byte(seg)
        self._stop()
        self._send_command(_CMD_DISP | self._brightness)

    def brightness(self, val=None):
        """Set brightness 0-7, or return the current value if val is None."""
        if val is None:
            return self._brightness
        self._brightness = max(0, min(7, val))
        self._send_command(_CMD_DISP | self._brightness)

    def clear(self):
        self.write([0, 0, 0, 0])

    def encode_char(self, ch):
        if "0" <= ch <= "9":
            return _DIGITS[ord(ch) - ord("0")]
        return _CHARS.get(ch.upper(), 0x00)

    def show(self, text):
        """Show up to 4 characters, left aligned."""
        text = str(text)[:4]
        segs = [self.encode_char(c) for c in text]
        segs += [0x00] * (4 - len(segs))
        self.write(segs)

    def number(self, num):
        """Show an integer from -999 to 9999, right aligned."""
        num = max(-999, min(9999, int(num)))
        self.show("{:>4d}".format(num))
