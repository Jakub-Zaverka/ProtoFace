"""Program vytvari regiony RGB matice a prekresluje do nich bitmapy a GIF snimky."""

# Tato vrstva drzi pixely RGB matice primo v RGB565, aby sly pouzit barevne assety.
import board
import displayio
import framebufferio
import rgbmatrix
import adafruit_imageload

DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 32
BIT_DEPTH = 4
RGB565_COLOR_COUNT = 65536
RGB565_CONVERTER = displayio.ColorConverter(
    input_colorspace=displayio.Colorspace.RGB565
)
SWAP_GREEN_BLUE = True
BRIGHTNESS_SCALE = 0.5
BRIGHTNESS_STEPS = (0.3, 0.4, 0.5, 0.7, 1.0)
COLOR_EFFECT_NORMAL = "normal"
COLOR_EFFECT_RAINBOW = "rainbow"

RAINBOW_SPEED = 4


def get_brightness_scale():
    """Vrati aktualni globalni faktor jasu RGB matice."""
    return BRIGHTNESS_SCALE


def cycle_brightness_scale():
    """Posune globalni jas na dalsi preddefinovany krok."""
    global BRIGHTNESS_SCALE

    try:
        current_index = BRIGHTNESS_STEPS.index(round(BRIGHTNESS_SCALE, 1))
    except ValueError:
        current_index = 0

    BRIGHTNESS_SCALE = BRIGHTNESS_STEPS[(current_index + 1) % len(BRIGHTNESS_STEPS)]
    return BRIGHTNESS_SCALE


class Display:
    """Obsluhuje HUB75 matici a jeji rozdeleni na vykreslovaci oblasti."""

    def __init__(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, bit_depth=BIT_DEPTH):
        """Inicializuje fyzickou RGB matici a korenovou `displayio` groupu."""
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.matrix_groups = []
        self.color_effect = COLOR_EFFECT_NORMAL
        self.effect_tick = 0

        # Pri znovuvytvoreni displeje se musi nejdriv uvolnit predchozi instance.
        displayio.release_displays()
        matrix = rgbmatrix.RGBMatrix(
            width=self.width,
            height=self.height,
            bit_depth=self.bit_depth,
            rgb_pins=[
                board.MTX_R1,
                board.MTX_G1,
                board.MTX_B1,
                board.MTX_R2,
                board.MTX_G2,
                board.MTX_B2,
            ],
            addr_pins=[
                board.MTX_ADDRA,
                board.MTX_ADDRB,
                board.MTX_ADDRC,
                board.MTX_ADDRD,
            ],
            clock_pin=board.MTX_CLK,
            latch_pin=board.MTX_LAT,
            output_enable_pin=board.MTX_OE,
        )

        # `auto_refresh=False` nechava aktualizaci plne pod kontrolou hlavni smycky.
        self.window = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
        self.group = displayio.Group()
        self.window.root_group = self.group
        self.window.refresh()

    def create_matrix(self, name, position_x, position_y, matrix_width, matrix_height):
        """Vytvori jednu bitmapovou oblast na RGB matici."""
        # Kazdy region ma vlastni RGB565 bitmapu, ale vsechny regiony sdili jednu root groupu.
        bitmap = displayio.Bitmap(matrix_width, matrix_height, RGB565_COLOR_COUNT)
        base_bitmap = displayio.Bitmap(matrix_width, matrix_height, RGB565_COLOR_COUNT)
        tile = displayio.TileGrid(
            bitmap,
            pixel_shader=RGB565_CONVERTER,
            x=position_x,
            y=position_y,
        )
        matrix = {
            "name": name,
            "bitmap": bitmap,
            "base_bitmap": base_bitmap,
            "tile": tile,
            "position_x": position_x,
            "position_y": position_y,
            "width": matrix_width,
            "height": matrix_height,
        }
        self.matrix_groups.append(matrix)
        self.group.append(tile)
        return matrix

    def to_bitmap(self, matrix, color_count=RGB565_COLOR_COUNT):
        """Prevede 2D seznam pixelu na `displayio.Bitmap`."""
        height = len(matrix)
        width = len(matrix[0])
        bitmap = displayio.Bitmap(width, height, color_count)

        for y, row in enumerate(matrix):
            if len(row) != width:
                raise ValueError("All rows in matrix must have the same width.")

            for x, value in enumerate(row):
                bitmap[x, y] = self.normalize_color(value)

        return bitmap

    def update_matrix(self, matrix_group, matrix):
        """Prepise obsah existujici oblasti pixely z 2D seznamu."""
        target_width = matrix_group["width"]
        target_height = matrix_group["height"]

        # Smaze predchozi obsah, aby po mensim obrazku nezustaly artefakty.
        matrix_group["base_bitmap"].fill(0)
        matrix_group["bitmap"].fill(0)

        copy_height = min(len(matrix), target_height)

        # Kopiruje se jen oblast, ktera se realne vejde do cilove bitmapy.
        for y in range(copy_height):
            row = matrix[y]
            copy_width = min(len(row), target_width)

            for x in range(copy_width):
                self._set_base_pixel(matrix_group, x, y, row[x])

    def set_pixel(self, matrix_group, x, y, value):
        """Nastavi jeden pixel uvnitr dane oblasti."""
        self._set_base_pixel(matrix_group, x, y, value)

    def fill_matrix(self, matrix_group, value):
        """Vyplni celou oblast jednou barvou."""
        color = self.normalize_color(value)
        matrix_group["base_bitmap"].fill(color)
        self._render_effect_for_matrix(matrix_group)

    def refresh(self):
        """Odesle zmeny bitmap do fyzickeho displeje."""
        if self.color_effect == COLOR_EFFECT_RAINBOW:
            self.effect_tick = (self.effect_tick + 1) % 256
            self._render_all_effects()
        self.window.refresh()

    def set_color_effect(self, effect):
        """Nastavi globalni barevny efekt pro vsechny regiony."""
        if effect not in (COLOR_EFFECT_NORMAL, COLOR_EFFECT_RAINBOW):
            raise ValueError("Unsupported color effect")
        if self.color_effect == effect:
            return

        self.color_effect = effect
        if effect == COLOR_EFFECT_RAINBOW:
            self.effect_tick = 0
        self._render_all_effects()

    def deinit(self):
        """Uvolni RGB matici tak, aby sla pozdeji znovu vytvorit."""
        if getattr(self, "window", None) is not None:
            try:
                self.window.root_group = None
            except AttributeError:
                pass

        self.matrix_groups = []
        self.group = None
        self.window = None
        displayio.release_displays()

    def matrix_to_list(self, matrix_group):
        """Vrati oblast jako vnoreny seznam RGB565 pixelu."""
        bitmap = matrix_group["base_bitmap"]
        width = matrix_group["width"]
        height = matrix_group["height"]

        return [
            [bitmap[x, y] for x in range(width)]
            for y in range(height)
        ]

    def rgb888_to_rgb565(self, color):
        """Prevede jeden pixel z 24bit RGB na RGB565."""
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF

        if SWAP_GREEN_BLUE:
            g, b = b, g

        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        return self.apply_brightness_rgb565(rgb565)

    def apply_brightness_rgb565(self, color):
        """Aplikuje globalni faktor jasu na RGB565 pixel."""
        scale = BRIGHTNESS_SCALE
        if scale >= 1.0:
            return color
        if scale <= 0.0:
            return 0

        r = (color >> 11) & 0x1F
        g = (color >> 5) & 0x3F
        b = color & 0x1F

        r = min(31, max(0, int(r * scale)))
        g = min(63, max(0, int(g * scale)))
        b = min(31, max(0, int(b * scale)))

        return (r << 11) | (g << 5) | b

    def normalize_color(self, color):
        """Prevede vstupni barvu na RGB565 a podpori i 24bit RGB cisla."""
        if color is None:
            return 0

        color = int(color)
        if color < 0:
            return 0

        if color <= 0xFFFF:
            return self.apply_brightness_rgb565(color)

        return self.rgb888_to_rgb565(color)

    def rgb565_to_rgb888(self, color):
        """Prevede jeden pixel z RGB565 na 24bit RGB."""
        r = (color >> 11) & 0x1F
        g = (color >> 5) & 0x3F
        b = color & 0x1F

        r = (r * 255) // 31
        g = (g * 255) // 63
        b = (b * 255) // 31

        return (r << 16) | (g << 8) | b

    def _set_base_pixel(self, matrix_group, x, y, value):
        """Ulozi puvodni pixel a vykresli jeho aktualni efektovou podobu."""
        color = self.normalize_color(value)
        matrix_group["base_bitmap"][x, y] = color
        matrix_group["bitmap"][x, y] = self._apply_color_effect(color, x, y)

    def _render_all_effects(self):
        """Prekresli vsechny regiony z ulozenych puvodnich pixelu."""
        for matrix_group in self.matrix_groups:
            self._render_effect_for_matrix(matrix_group)

    def _render_effect_for_matrix(self, matrix_group):
        """Prekresli jeden region podle aktualniho barevneho efektu."""
        base_bitmap = matrix_group["base_bitmap"]
        bitmap = matrix_group["bitmap"]
        width = matrix_group["width"]
        height = matrix_group["height"]

        for y in range(height):
            for x in range(width):
                bitmap[x, y] = self._apply_color_effect(base_bitmap[x, y], x, y)

    def _apply_color_effect(self, color, x, y):
        """Vrati pixel po aplikaci aktualniho efektu."""
        if self.color_effect != COLOR_EFFECT_RAINBOW or color == 0:
            return color

        return self._rainbow_rgb565(x, y)

    def _rainbow_rgb565(self, x, y):
        """Vygeneruje RGB565 barvu z posunuteho color-wheel indexu."""
        pos = (x * 6 + y * 10 + self.effect_tick * RAINBOW_SPEED) & 0xFF

        if pos < 85:
            red = 255 - pos * 3
            green = pos * 3
            blue = 0
        elif pos < 170:
            pos -= 85
            red = 0
            green = 255 - pos * 3
            blue = pos * 3
        else:
            pos -= 170
            red = pos * 3
            green = 0
            blue = 255 - pos * 3

        return self.rgb888_to_rgb565((red << 16) | (green << 8) | blue)

    def source_pixel_to_rgb565(self, bitmap, pixel_shader, x, y):
        """Precte zdrojovy pixel a vrati ho jako RGB565."""
        pixel_value = bitmap[x, y]

        if isinstance(pixel_shader, displayio.Palette):
            return self.rgb888_to_rgb565(pixel_shader[pixel_value])

        if isinstance(pixel_shader, displayio.ColorConverter):
            return self.apply_brightness_rgb565(pixel_shader.convert(pixel_value))

        if pixel_value <= 0xFFFF:
            return self.apply_brightness_rgb565(pixel_value)

        return self.rgb888_to_rgb565(pixel_value)

    def _load_24bit_bmp_rows(self, source):
        """Nacte nepresne 24bit BMP a vrati jeho pixely jako RGB565 radky."""
        with open(source, "rb") as file_handle:
            header = file_handle.read(54)
            if len(header) < 54 or header[0:2] != b"BM":
                raise ValueError("Unsupported BMP header")

            data_offset = int.from_bytes(header[10:14], "little")
            width = self._read_signed_le32(header[18:22])
            height = self._read_signed_le32(header[22:26])
            bits_per_pixel = int.from_bytes(header[28:30], "little")
            compression = int.from_bytes(header[30:34], "little")

            if bits_per_pixel != 24 or compression != 0:
                raise ValueError("BMP is not uncompressed 24-bit")

            top_down = height < 0
            width = abs(width)
            height = abs(height)
            row_stride = ((width * 3) + 3) & ~3

            file_handle.seek(data_offset)
            raw_rows = [file_handle.read(row_stride) for _ in range(height)]

        rows = []
        source_rows = raw_rows if top_down else reversed(raw_rows)
        for raw_row in source_rows:
            row = []
            for x in range(width):
                pixel_offset = x * 3
                blue = raw_row[pixel_offset]
                green = raw_row[pixel_offset + 1]
                red = raw_row[pixel_offset + 2]
                rgb888 = (red << 16) | (green << 8) | blue
                row.append(self.rgb888_to_rgb565(rgb888))
            rows.append(row)

        return rows

    def _read_signed_le32(self, raw_bytes):
        """Vrati 32bit little-endian cislo se znamenkem bez `signed=True`."""
        value = int.from_bytes(raw_bytes, "little")
        if value & 0x80000000:
            value -= 0x100000000
        return value

    def load_gif_frame_into_matrix(self, matrix_group, bitmap, pixel_shader=None):
        """Nahraje aktualni GIF frame do dane oblasti RGB matice."""
        matrix_group["base_bitmap"].fill(0)
        matrix_group["bitmap"].fill(0)

        copy_width = min(bitmap.width, matrix_group["width"])
        copy_height = min(bitmap.height, matrix_group["height"])

        for y in range(copy_height):
            for x in range(copy_width):
                pixel_value = bitmap[x, y]

                # GIF frame z `gifio` byva RGB565, pripadne se vezme barva z palety GIFu.
                if pixel_shader is not None and isinstance(pixel_shader, displayio.Palette):
                    self._set_base_pixel(
                        matrix_group,
                        x,
                        y,
                        pixel_shader[pixel_value],
                    )
                else:
                    self._set_base_pixel(matrix_group, x, y, pixel_value)

    def load_bmp_into_matrix(self, matrix_group, source):
        """Nahraje BMP nebo pametovou bitmapu a premaluje ji do RGB565 bitmapy."""
        # Zdroj muze byt bud cesta k souboru, nebo dvojice `(bitmap, pixel_shader)`.
        if isinstance(source, str):
            if source.lower().endswith(".bmp"):
                try:
                    self.update_matrix(matrix_group, self._load_24bit_bmp_rows(source))
                    return
                except ValueError:
                    pass

            bitmap, pixel_shader = adafruit_imageload.load(
                source,
                bitmap=displayio.Bitmap,
                palette=displayio.Palette,
            )
        elif isinstance(source, tuple) and len(source) == 2:
            bitmap, pixel_shader = source
        else:
            raise TypeError("source must be a BMP path or a (bitmap, pixel_shader) tuple")

        matrix = [
            [
                self.source_pixel_to_rgb565(bitmap, pixel_shader, x, y)
                for x in range(bitmap.width)
            ]
            for y in range(bitmap.height)
        ]

        self.update_matrix(matrix_group, matrix)
