"""Program sdili I2C sbernici mezi APDS9960 senzorem a OLED displejem SSD1306."""

# Na jedne sbernici bezi proximity senzor i OLED, proto se I2C inicializuje jen jednou.
import board
from adafruit_apds9960.apds9960 import APDS9960
import adafruit_ssd1306

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDRESS = 0x3C

_shared_i2c = None

# Lokalni 5x7 font slouzi pro textove menu bez zavislosti na externim font souboru.
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
    """Vrati sdilenou I2C sbernici pro vsechna pripojena zarizeni."""
    global _shared_i2c

    if _shared_i2c is None:
        # Na nekterych deskach je k dispozici primo STEMMA_I2C, jinak obecne I2C.
        if hasattr(board, "STEMMA_I2C"):
            _shared_i2c = board.STEMMA_I2C()
        else:
            _shared_i2c = board.I2C()

    return _shared_i2c


def scan_i2c():
    """Naskenuje I2C sbernici a vrati nalezene adresy."""
    try:
        i2c = get_i2c()

        # I2C scan vyzaduje lock, proto se po pouziti vzdy zase odemkne.
        while not i2c.try_lock():
            pass

        try:
            return [hex(address) for address in i2c.scan()]
        finally:
            i2c.unlock()
    except OSError:
        return []


class APDSSensor:
    """Cte proximity a barvu z APDS9960 na sdilene I2C sbernici."""
    def __init__(self):
        # Senzor se pri vytvoreni rovnou inicializuje a zapne potrebne kanaly.
        self.i2c = get_i2c()
        self.sensor = None
        self._initialize_sensor()

    def _initialize_sensor(self):
        """Inicializuje APDS9960 nebo ho znovu vytvori po chybe sbernice."""
        try:
            self.sensor = APDS9960(self.i2c)
            self.sensor.enable_proximity = True
            self.sensor.enable_color = True
            return True
        except (OSError, ValueError):
            self.sensor = None
            return False

    def scan(self):
        """Vrati adresy viditelne na I2C pro rychlou diagnostiku."""
        return scan_i2c()

    def get_value(self):
        """Vrati aktualni proximity hodnotu nebo `None` pri chybe I2C."""
        if self.sensor is None and not self._initialize_sensor():
            return None

        try:
            return self.sensor.proximity
        except OSError:
            # Pri obcasne chybe sbernice se senzor zkusí znovu vytvorit.
            self.sensor = None
            if not self._initialize_sensor():
                return None
            try:
                return self.sensor.proximity
            except OSError:
                self.sensor = None
                return None

    def get_color(self):
        """Vrati aktualni barevna data, pokud jsou dostupna."""
        if self.sensor is None and not self._initialize_sensor():
            return None

        try:
            if self.sensor.color_data_ready:
                return self.sensor.color_data
        except OSError:
            self.sensor = None
            if self._initialize_sensor():
                try:
                    if self.sensor.color_data_ready:
                        return self.sensor.color_data
                except OSError:
                    self.sensor = None
                    return None
        return None


class OLEDDisplay:
    """Vykresluje textove obrazovky na OLED SSD1306 pres sdilenou I2C."""
    def __init__(self, width=OLED_WIDTH, height=OLED_HEIGHT, address=OLED_ADDRESS):
        # OLED se drzi jako jednoducha textova vrstva, ne jako plne graficke UI.
        self.i2c = get_i2c()
        self.width = width
        self.height = height
        self.address = address
        self.display = None
        if self._initialize_display():
            self.clear()

    def _initialize_display(self):
        """Vytvori SSD1306 instanci, pokud je displej dostupny."""
        try:
            self.display = adafruit_ssd1306.SSD1306_I2C(
                self.width,
                self.height,
                self.i2c,
                addr=self.address,
            )
            self.display.write_cmd(0xA0)
            self.display.write_cmd(0xC0)
            return True
        except (OSError, ValueError):
            self.display = None
            return False

    def _ensure_display(self):
        """Vrati `True`, pokud je OLED aktualne pripraveny k zapisu."""
        if self.display is not None:
            return True
        return self._initialize_display()

    def scan(self):
        """Vrati adresy viditelne na I2C pro rychlou diagnostiku."""
        return scan_i2c()

    def clear(self):
        """Vymaze OLED framebuffer a ihned ho zobrazi."""
        if not self._ensure_display():
            return False

        try:
            self.display.fill(0)
            self.display.show()
            return True
        except OSError:
            self.display = None
            return False

    def get_value(self):
        """Vrati puvodni instanci `SSD1306_I2C`, pokud je dostupna."""
        if not self._ensure_display():
            return None
        return self.display

    def show_text(self, text, x=0, y=0, clear=True):
        """Vykresli text na zadanou pozici a pripadne nejdriv smaze displej."""
        if not self._ensure_display():
            return False

        try:
            if clear:
                self.display.fill(0)

            self._draw_text(str(text), x, y)

            self.display.show()
            return True
        except OSError:
            self.display = None
            return False

    def show_text_blocks(self, blocks, clear=True):
        """Vykresli vice textovych bloku a OLED obnovi jen jednou."""
        if not self._ensure_display():
            return False

        try:
            if clear:
                self.display.fill(0)

            # Bloky umoznuji kombinovat menu, hodiny a debug text v jednom flushi.
            for block in blocks:
                text = block.get("text", "")
                x = block.get("x", 0)
                y = block.get("y", 0)
                self._draw_text(str(text), x, y)

            self.display.show()
            return True
        except OSError:
            self.display = None
            return False

    def draw_status(self, boop=False, emote=False, emote_time=0, emote_name="", current_time = "00:00"):
        """Zobrazi jednoduchou stavovou obrazovku s emote a casem."""
        text = (
            f"Boop: {'ON' if boop else 'OFF'}\n"
            f"Emote: {'ON' if emote else 'OFF'}\n"
            f"{emote_name} {emote_time}\n"
            f"{current_time}"
        )
        return self.show_text(text)

    def _draw_text(self, text, x=0, y=0, color=1):
        """Kresli vice radku textu lokalnim 5x7 bitmapovym fontem."""
        cursor_x = x
        cursor_y = y

        # Text se automaticky zalamuje pri konci radku a zastavi se na spodku displeje.
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
        """Kresli jeden znak z lokalni tabulky bitmapoveho fontu."""
        glyph = _FONT_5X7.get(char)
        if glyph is None:
            glyph = _FONT_5X7.get(char.upper(), _FONT_5X7["?"])

        for column, bits in enumerate(glyph):
            for row in range(7):
                if bits & (1 << row):
                    if 0 <= x + column < self.width and 0 <= y + row < self.height:
                        self.display.pixel(x + column, y + row, color)
