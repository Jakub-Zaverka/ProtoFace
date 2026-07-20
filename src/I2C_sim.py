"""Program sdili I2C sbernici mezi APDS9960 senzorem a OLED displejem SSD1306."""

# Na jedne sbernici bezi proximity senzor i OLED, proto se I2C inicializuje jen jednou.
import board
from adafruit_apds9960.apds9960 import APDS9960
import adafruit_ssd1306

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDRESS = 0x3C
OLED_FONT_SCALE_STEPS = ((3, 2), (2, 1), (5, 2))
OLED_FONT_SCALE_INDEX = 0
FONT_GLYPH_WIDTH = 5
FONT_GLYPH_HEIGHT = 7

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


def _get_text_scale():
    """Vrati aktualni pomer zvetseni OLED fontu."""
    return OLED_FONT_SCALE_STEPS[OLED_FONT_SCALE_INDEX]


def _scale_extent(value):
    """Prepocita rozmer bitmapoveho fontu podle aktualniho zvetseni."""
    scale_num, scale_den = _get_text_scale()
    return (value * scale_num + scale_den - 1) // scale_den


def get_oled_font_scale_label():
    """Vrati kratky popisek aktualni velikosti OLED fontu."""
    scale_num, scale_den = _get_text_scale()
    if scale_num % scale_den == 0:
        return "{}x".format(scale_num // scale_den)
    return "{}.{}x".format(scale_num // scale_den, (scale_num * 10 // scale_den) % 10)


def get_oled_font_scale_index():
    """Vrati index aktualniho kroku velikosti OLED fontu."""
    return OLED_FONT_SCALE_INDEX


def get_oled_font_scale_count():
    """Vrati pocet dostupnych kroku velikosti OLED fontu."""
    return len(OLED_FONT_SCALE_STEPS)


def set_oled_font_scale_index(index):
    """Nastavi velikost OLED fontu podle indexu preddefinovaneho kroku."""
    global OLED_FONT_SCALE_INDEX

    if index < 0 or index >= len(OLED_FONT_SCALE_STEPS):
        index = 0
    OLED_FONT_SCALE_INDEX = index
    return get_oled_font_scale_label()


def cycle_oled_font_scale():
    """Prepne OLED font na dalsi preddefinovanou velikost."""
    return set_oled_font_scale_index(
        (OLED_FONT_SCALE_INDEX + 1) % len(OLED_FONT_SCALE_STEPS)
    )


def get_font_char_width():
    """Vrati sirku jednoho znaku vcetne mezery pro aktualni font."""
    return _scale_extent(FONT_GLYPH_WIDTH) + 1


def get_font_line_height():
    """Vrati vysku radku pro aktualni font."""
    return _scale_extent(FONT_GLYPH_HEIGHT) + 1


def get_font_render_height():
    """Vrati skutecnou vykreslovanou vysku znaku pro aktualni font."""
    return _scale_extent(FONT_GLYPH_HEIGHT)


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
                wrap = block.get("wrap", True)
                max_width = block.get("max_width", None)
                clip_x_min = block.get("clip_x_min", None)
                clip_x_max = block.get("clip_x_max", None)
                self._draw_text(
                    str(text),
                    x,
                    y,
                    wrap=wrap,
                    max_width=max_width,
                    clip_x_min=clip_x_min,
                    clip_x_max=clip_x_max,
                )

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

    def _draw_text(
        self,
        text,
        x=0,
        y=0,
        color=1,
        wrap=True,
        max_width=None,
        clip_x_min=None,
        clip_x_max=None,
    ):
        """Kresli vice radku textu lokalnim 5x7 bitmapovym fontem."""
        cursor_x = x
        cursor_y = y
        char_width = get_font_char_width()
        line_height = get_font_line_height()
        render_height = get_font_render_height()
        if max_width is None:
            max_width = self.width - x
        if clip_x_min is None:
            clip_x_min = x
        if clip_x_max is None:
            clip_x_max = x + max_width
        clip_x_min = max(0, clip_x_min)
        clip_x_max = min(self.width, clip_x_max)

        # Text se automaticky zalamuje pri konci radku a zastavi se na spodku displeje.
        for char in str(text):
            if char == "\n":
                cursor_x = x
                cursor_y += line_height
                continue

            self._draw_char(
                char,
                cursor_x,
                cursor_y,
                color=color,
                clip_x_min=clip_x_min,
                clip_x_max=clip_x_max,
            )
            cursor_x += char_width

            if wrap and cursor_x + char_width > x + max_width:
                cursor_x = x
                cursor_y += line_height
            elif not wrap and cursor_x >= x + max_width:
                continue

            if cursor_y + render_height > self.height:
                break

    def _draw_char(self, char, x, y, color=1, clip_x_min=0, clip_x_max=None):
        """Kresli jeden znak z lokalni tabulky bitmapoveho fontu."""
        if clip_x_max is None:
            clip_x_max = self.width

        glyph = _FONT_5X7.get(char)
        if glyph is None:
            glyph = _FONT_5X7.get(char.upper(), _FONT_5X7["?"])

        for column, bits in enumerate(glyph):
            for row in range(7):
                if bits & (1 << row):
                    self._draw_scaled_pixel(
                        x,
                        y,
                        column,
                        row,
                        color,
                        clip_x_min=clip_x_min,
                        clip_x_max=clip_x_max,
                    )

    def _draw_scaled_pixel(
        self,
        x,
        y,
        column,
        row,
        color=1,
        clip_x_min=0,
        clip_x_max=None,
    ):
        """Zvetsi jeden pixel bitmapoveho fontu podle aktualniho nastaveni."""
        if clip_x_max is None:
            clip_x_max = self.width

        scale_num, scale_den = _get_text_scale()
        start_x = (column * scale_num) // scale_den
        end_x = ((column + 1) * scale_num + scale_den - 1) // scale_den
        start_y = (row * scale_num) // scale_den
        end_y = ((row + 1) * scale_num + scale_den - 1) // scale_den

        for pixel_x in range(x + start_x, x + end_x):
            if pixel_x < clip_x_min or pixel_x >= clip_x_max:
                continue
            for pixel_y in range(y + start_y, y + end_y):
                if 0 <= pixel_y < self.height:
                    self.display.pixel(pixel_x, pixel_y, color)
