import board
import busio
from adafruit_apds9960.apds9960 import APDS9960
import adafruit_ssd1306
from adafruit_gfx.gfx import GFX

I2C_SCL_PIN = board.A1
I2C_SDA_PIN = board.A2
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
}


def get_i2c():
    global _shared_i2c

    if _shared_i2c is None:
        _shared_i2c = busio.I2C(I2C_SCL_PIN, I2C_SDA_PIN)

    return _shared_i2c


def scan_i2c():
    i2c = get_i2c()

    while not i2c.try_lock():
        pass

    addresses = [hex(address) for address in i2c.scan()]
    i2c.unlock()
    return addresses


class APDSSensor:
    def __init__(self):
        self.i2c = get_i2c()
        self.sensor = APDS9960(self.i2c)
        self.sensor.enable_proximity = True
        self.sensor.enable_color = True

    def scan(self):
        return scan_i2c()

    def get_value(self):
        return self.sensor.proximity

    def get_color(self):
        if self.sensor.color_data_ready:
            return self.sensor.color_data
        return None


class OLEDDisplay:
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
        self.gfx = self._create_gfx()
        self.clear()

    def scan(self):
        return scan_i2c()

    def clear(self):
        self.display.fill(0)
        self.display.show()

    def get_value(self):
        return self.display

    def show_text(self, text, x=0, y=0, clear=True):
        if clear:
            self.display.fill(0)

        self._draw_text(str(text), x, y)

        self.display.show()

    def draw_status(self, boop=False, emote=False, emote_time=0):
        self.display.fill(0)
        self.gfx.round_rect(0, 0, self.width, self.height, 6, 1)
        self.gfx.hline(4, 14, self.width - 8, 1)

        self._draw_text("STATUS", 34, 4)

        self.gfx.circle(14, 28, 7, 1)
        if boop:
            self.gfx.fill_circle(14, 28, 4, 1)
        self._draw_text("BOOP", 28, 24)
        self._draw_text("ON" if boop else "OFF", 84, 24)

        self.gfx.rect(6, 40, self.width - 12, 18, 1)
        if emote:
            self.gfx.fill_rect(8, 42, self.width - 16, 14, 1)
            self._draw_text("EMOTE", 12, 46, color=0)
        else:
            self._draw_text("EMOTE", 12, 46)

        self._draw_text(str(emote_time), 96, 46, color=0 if emote else 1)
        self.display.show()

    def _create_gfx(self):
        return GFX(
            self.width,
            self.height,
            pixel=self._pixel,
            hline=self._hline,
            vline=self._vline,
            fill_rect=self._fill_rect,
            text=self._draw_text,
        )

    def _pixel(self, x, y, color=1):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.display.pixel(x, y, color)

    def _hline(self, x, y, width, color=1):
        for offset in range(width):
            self._pixel(x + offset, y, color)

    def _vline(self, x, y, height, color=1):
        for offset in range(height):
            self._pixel(x, y + offset, color)

    def _fill_rect(self, x, y, width, height, color=1):
        for row in range(height):
            self._hline(x, y + row, width, color)

    def _draw_text(self, text, x=0, y=0, color=1):
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
        glyph = _FONT_5X7.get(char)
        if glyph is None:
            glyph = _FONT_5X7.get(char.upper(), _FONT_5X7["?"])

        for column, bits in enumerate(glyph):
            for row in range(7):
                if bits & (1 << row):
                    self._pixel(x + column, y + row, color)
