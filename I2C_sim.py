"""Shared I2C helpers for the APDS9960 sensor and SSD1306 OLED."""

import board
from adafruit_apds9960.apds9960 import APDS9960
import adafruit_ssd1306

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDRESS = 0x3C

_shared_i2c = None

_FONT_5X7 = {
    " ": [0x00, 0x00, 0x00, 0x00, 0x00],
    "!": [0x00, 0x00, 0x5F, 0x00, 0x00],
    "-": [0x08, 0x08, 0x08, 0x08, 0x08],
    ".": [0x00, 0x60, 0x60, 0x00, 0x00],
    "/": [0x20, 0x10, 0x08, 0x04, 0x02],
    ":": [0x00, 0x36, 0x36, 0x00, 0x00],
    "?": [0x02, 0x01, 0x51, 0x09, 0x06],
    "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
    "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
    "2": [0x42, 0x61, 0x51, 0x49, 0x46],
    "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
    "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
    "5": [0x27, 0x45, 0x45, 0x45, 0x39],
    "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
    "7": [0x01, 0x71, 0x09, 0x05, 0x03],
    "8": [0x36, 0x49, 0x49, 0x49, 0x36],
    "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
    "A": [0x7E, 0x11, 0x11, 0x11, 0x7E],
    "B": [0x7F, 0x49, 0x49, 0x49, 0x36],
    "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C],
    "E": [0x7F, 0x49, 0x49, 0x49, 0x41],
    "F": [0x7F, 0x09, 0x09, 0x09, 0x01],
    "G": [0x3E, 0x41, 0x49, 0x49, 0x7A],
    "H": [0x7F, 0x08, 0x08, 0x08, 0x7F],
    "I": [0x00, 0x41, 0x7F, 0x41, 0x00],
    "J": [0x20, 0x40, 0x41, 0x3F, 0x01],
    "K": [0x7F, 0x08, 0x14, 0x22, 0x41],
    "L": [0x7F, 0x40, 0x40, 0x40, 0x40],
    "M": [0x7F, 0x02, 0x0C, 0x02, 0x7F],
    "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],
    "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],
    "P": [0x7F, 0x09, 0x09, 0x09, 0x06],
    "Q": [0x3E, 0x41, 0x51, 0x21, 0x5E],
    "R": [0x7F, 0x09, 0x19, 0x29, 0x46],
    "S": [0x46, 0x49, 0x49, 0x49, 0x31],
    "T": [0x01, 0x01, 0x7F, 0x01, 0x01],
    "U": [0x3F, 0x40, 0x40, 0x40, 0x3F],
    "V": [0x1F, 0x20, 0x40, 0x20, 0x1F],
    "W": [0x3F, 0x40, 0x38, 0x40, 0x3F],
    "X": [0x63, 0x14, 0x08, 0x14, 0x63],
    "Y": [0x07, 0x08, 0x70, 0x08, 0x07],
    "Z": [0x61, 0x51, 0x49, 0x45, 0x43],
    ">": [0x41, 0x22, 0x14, 0x08, 0x00],
    "<": [0x00, 0x08, 0x14, 0x22, 0x41],
    "=": [0x14, 0x14, 0x14, 0x14, 0x14]
}


def get_i2c():
    """Return a shared hardware I2C bus instance for JST-SH/STEMMA devices."""
    global _shared_i2c

    if _shared_i2c is None:
        if hasattr(board, "STEMMA_I2C"):
            _shared_i2c = board.STEMMA_I2C()
        else:
            _shared_i2c = board.I2C()

    return _shared_i2c


def scan_i2c():
    """Scan the shared I2C bus and return detected device addresses."""
    i2c = get_i2c()

    while not i2c.try_lock():
        pass

    try:
        return [hex(address) for address in i2c.scan()]
    finally:
        i2c.unlock()


class APDSSensor:
    """Wrapper around the APDS9960 sensor on the shared I2C bus."""
    def __init__(self):
        self.i2c = get_i2c()
        self.sensor = None
        self._initialize_sensor()

    def _initialize_sensor(self):
        """Create or recreate the APDS9960 instance after a bus error."""
        self.sensor = APDS9960(self.i2c)
        self.sensor.enable_proximity = True
        self.sensor.enable_color = True

    def scan(self):
        """Return visible I2C addresses for quick bus diagnostics."""
        return scan_i2c()

    def get_value(self):
        """Return the current proximity reading, or None on I2C failure."""
        try:
            return self.sensor.proximity
        except OSError:
            try:
                self._initialize_sensor()
                return self.sensor.proximity
            except OSError:
                return None

    def get_color(self):
        """Return current color data when available, otherwise None."""
        try:
            if self.sensor.color_data_ready:
                return self.sensor.color_data
        except OSError:
            try:
                self._initialize_sensor()
                if self.sensor.color_data_ready:
                    return self.sensor.color_data
            except OSError:
                return None
        return None


class OLEDDisplay:
    """Text-only SSD1306 OLED helper using the shared I2C bus."""
    def __init__(self, width=OLED_WIDTH, height=OLED_HEIGHT, address=OLED_ADDRESS):
        self.i2c = get_i2c()
        self.width = width
        self.height = height
        self.display = adafruit_ssd1306.SSD1306_I2C(
            width,
            height,
            self.i2c,
            addr=address,
        )
        self.clear()

    def scan(self):
        """Return visible I2C addresses for quick bus diagnostics."""
        return scan_i2c()

    def clear(self):
        """Clear the OLED framebuffer and update the display."""
        self.display.fill(0)
        self.display.show()

    def get_value(self):
        """Return the underlying SSD1306 display instance."""
        return self.display

    def show_text(self, text, x=0, y=0, clear=True):
        """Draw text at the given position and optionally clear first."""
        if clear:
            self.display.fill(0)

        self._draw_text(str(text), x, y)

        self.display.show()

    def show_text_blocks(self, blocks, clear=True):
        """Draw multiple text blocks and flush the OLED only once."""
        if clear:
            self.display.fill(0)

        for block in blocks:
            text = block.get("text", "")
            x = block.get("x", 0)
            y = block.get("y", 0)
            self._draw_text(str(text), x, y)

        self.display.show()

    def draw_status(self, boop=False, emote=False, emote_time=0, emote_name="", current_time = "00:00"):
        """Render a simple multiline status screen for boop and emote."""
        text = (
            f"Boop: {'ON' if boop else 'OFF'}\n"
            f"Emote: {'ON' if emote else 'OFF'}\n"
            f"{emote_name} {emote_time}\n"
            f"{current_time}"
        )
        self.show_text(text)

    def _draw_text(self, text, x=0, y=0, color=1):
        """Draw multiline text using the built-in 5x7 bitmap font."""
        cursor_x = x
        cursor_y = y

        for char in str(text):
            if char == "\n":
                cursor_x = x
                cursor_y += 8
                continue

            self._draw_char(char, cursor_x, cursor_y, color=color)
            cursor_x += 6

            if cursor_x + 5 > self.width:
                cursor_x = x
                cursor_y += 8

            if cursor_y + 7 > self.height:
                break

    def _draw_char(self, char, x, y, color=1):
        """Draw a single character from the local bitmap font table."""
        glyph = _FONT_5X7.get(char)
        if glyph is None:
            glyph = _FONT_5X7.get(char.upper(), _FONT_5X7["?"])

        for column, bits in enumerate(glyph):
            for row in range(7):
                if bits & (1 << row):
                    if 0 <= x + column < self.width and 0 <= y + row < self.height:
                        self.display.pixel(x + column, y + row, color)
