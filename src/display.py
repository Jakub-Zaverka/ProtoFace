"""Program vytvari regiony RGB matice a prekresluje do nich bitmapy a GIF snimky."""

# Tato vrstva drzi pixely RGB matice primo v RGB565, aby sly pouzit barevne assety.
import board
import displayio
import framebufferio
import rgbmatrix
import adafruit_imageload

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 32
PANEL_WIDTH = 64
RIGHT_PANEL_X_OFFSET = 64
BIT_DEPTH = 2
#Right je ve skutečnosti levý, tedy 0-63 displej
SCREEN_ENABLED = {
    "left": True,
    "right": True,
}
TILEGRID_ENABLED = {
    "nose": True,
    "eye": True,
    "mouth": True,
    "whole": True,
    "nose_right": True,
    "eye_right": True,
    "mouth_right": True,
    "whole_right": True,
}
RGB565_COLOR_COUNT = 65536
RGB565_CONVERTER = displayio.ColorConverter(
    input_colorspace=displayio.Colorspace.RGB565
)
SWAP_GREEN_BLUE = True
BRIGHTNESS_SCALE = 0.5
BRIGHTNESS_STEPS = (0.3, 0.4, 0.5, 0.7, 1.0)
COLOR_EFFECT_NORMAL = "normal"
COLOR_EFFECT_RAINBOW = "rainbow"
COLOR_EFFECT_SOLID = "solid"

RAINBOW_SPEED = 8
RAINBOW_X_SCALE = 10
RAINBOW_Y_SCALE = 16
RAINBOW_FRAME_SKIP = 3


def get_brightness_scale():
    """Vrati aktualni globalni faktor jasu RGB matice."""
    return BRIGHTNESS_SCALE


def get_brightness_scale_index():
    """Vrati index aktualniho kroku jasu RGB matice."""
    try:
        return BRIGHTNESS_STEPS.index(round(BRIGHTNESS_SCALE, 1))
    except ValueError:
        return 0


def set_brightness_scale_index(index):
    """Nastavi jas RGB matice podle indexu preddefinovaneho kroku."""
    global BRIGHTNESS_SCALE

    if index < 0 or index >= len(BRIGHTNESS_STEPS):
        index = 0
    BRIGHTNESS_SCALE = BRIGHTNESS_STEPS[index]
    return BRIGHTNESS_SCALE


def cycle_brightness_scale():
    """Posune globalni jas na dalsi preddefinovany krok."""
    return set_brightness_scale_index(
        (get_brightness_scale_index() + 1) % len(BRIGHTNESS_STEPS)
    )


class Display:
    """Obsluhuje HUB75 matici a jeji rozdeleni na vykreslovaci oblasti."""

    def __init__(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, bit_depth=BIT_DEPTH):
        """Inicializuje fyzickou RGB matici a korenovou `displayio` groupu."""
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.matrix_groups = []
        self.image_cache = {}
        self.color_effect = COLOR_EFFECT_NORMAL
        self.effect_tick = 0
        self.rainbow_frame_counter = 0
        self.rainbow_wheel = self._create_rainbow_wheel()
        self.dirty = False

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
        self.screen_groups = {
            "left": displayio.Group(x=0, y=0),
            "right": displayio.Group(x=RIGHT_PANEL_X_OFFSET, y=0),
        }
        self.group.append(self.screen_groups["left"])
        self.group.append(self.screen_groups["right"])
        self.window.root_group = self.group
        self.window.refresh()

    def create_matrix(
        self,
        name,
        position_x,
        position_y,
        matrix_width,
        matrix_height,
        screen="left",
        mirror_x=False,
        mirror_position_x=False,
    ):
        """Vytvori jednu bitmapovou oblast na RGB matici."""
        # Kazdy region ma vlastni RGB565 bitmapu, ale vsechny regiony sdili jednu root groupu.
        screen_group = self.screen_groups.get(screen)
        if screen_group is None:
            raise ValueError("Unknown screen group: {}".format(screen))

        bitmap = displayio.Bitmap(matrix_width, matrix_height, RGB565_COLOR_COUNT)
        base_bitmap = displayio.Bitmap(matrix_width, matrix_height, RGB565_COLOR_COUNT)
        tile_x = position_x
        if mirror_position_x:
            tile_x = PANEL_WIDTH - position_x - matrix_width

        tile = displayio.TileGrid(
            bitmap,
            pixel_shader=RGB565_CONVERTER,
            x=tile_x,
            y=position_y,
        )
        enabled = self.is_tilegrid_enabled(name, screen)
        tile.hidden = not enabled
        matrix = {
            "name": name,
            "bitmap": bitmap,
            "base_bitmap": base_bitmap,
            "active_pixels": [],
            "color_effect": COLOR_EFFECT_NORMAL,
            "solid_effect_color": 0,
            "tile": tile,
            "position_x": tile_x,
            "source_position_x": position_x,
            "position_y": position_y,
            "width": matrix_width,
            "height": matrix_height,
            "screen": screen,
            "mirror_x": mirror_x,
            "mirror_position_x": mirror_position_x,
            "enabled": enabled,
        }
        self.matrix_groups.append(matrix)
        screen_group.append(tile)
        return matrix

    def is_tilegrid_enabled(self, name, screen):
        """Vrati, jestli je konkretni vykreslovaci usek zapnuty."""
        return SCREEN_ENABLED.get(screen, True) and TILEGRID_ENABLED.get(name, True)

    def _enforce_tilegrid_enabled_flags(self):
        """Schova vypnute tilegridy i kdyz je controller pri emote znovu odkryl."""
        for matrix_group in self.matrix_groups:
            enabled = self.is_tilegrid_enabled(
                matrix_group["name"],
                matrix_group["screen"],
            )
            matrix_group["enabled"] = enabled
            if not enabled:
                self.set_matrix_hidden(matrix_group, True)

    def mark_dirty(self):
        """Oznaci framebuffer jako zmeneny pro nejblizsi refresh."""
        self.dirty = True

    def set_matrix_hidden(self, matrix_group, hidden):
        """Zmeni viditelnost oblasti a oznaci displej jen pri realne zmene."""
        hidden = bool(hidden)
        tile = matrix_group["tile"]
        if tile.hidden == hidden:
            return False
        tile.hidden = hidden
        self.mark_dirty()
        return True

    def set_matrix_position(self, matrix_group, x, y):
        """Posune oblast a oznaci displej jen pokud se poloha skutecne zmenila."""
        tile = matrix_group["tile"]
        x = int(x)
        y = int(y)
        if tile.x == x and tile.y == y:
            return False
        tile.x = x
        tile.y = y
        self.mark_dirty()
        return True

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
        self._update_matrix(matrix_group, matrix, normalize=True)

    def update_matrix_rgb565(self, matrix_group, matrix):
        """Prepise oblast uz pripravenymi RGB565 pixely bez dalsi konverze."""
        self._update_matrix(matrix_group, matrix, normalize=False)

    def get_active_pixels_rgb565(self, matrix_group):
        """Vrati jen rozsvicene RGB565 pixely oblasti pro pametove setrne prechody."""
        bitmap = matrix_group["base_bitmap"]
        pixels = []
        mirror_x = matrix_group.get("mirror_x", False)
        width = matrix_group["width"]
        for y in range(matrix_group["height"]):
            for x in range(width):
                color = bitmap[x, y]
                if color:
                    # `base_bitmap` uz obsahuje fyzicky zrcadlene X. Prechod ale
                    # pracuje v logickych souradnicich, proto zrcadleni vratime.
                    logical_x = width - 1 - x if mirror_x else x
                    pixels.append((logical_x, y, color))
        return pixels

    def draw_sparse_rgb565(self, matrix_group, pixels):
        """Vykresli seznam `(x, y, color)` jako jeden snimek prechodu."""
        matrix_group["base_bitmap"].fill(0)
        matrix_group["bitmap"].fill(0)
        matrix_group["active_pixels"] = []

        for x, y, color in pixels:
            if color and 0 <= x < matrix_group["width"] and 0 <= y < matrix_group["height"]:
                self._set_base_pixel_rgb565(matrix_group, x, y, color)
        self.mark_dirty()

    def _update_matrix(self, matrix_group, matrix, normalize=True):
        """Spolecna implementace kopirovani pixelu do bitmapove oblasti."""
        target_width = matrix_group["width"]
        target_height = matrix_group["height"]

        # Smaze predchozi obsah, aby po mensim obrazku nezustaly artefakty.
        matrix_group["base_bitmap"].fill(0)
        matrix_group["bitmap"].fill(0)
        matrix_group["active_pixels"] = []

        copy_height = min(len(matrix), target_height)

        # Kopiruje se jen oblast, ktera se realne vejde do cilove bitmapy.
        if not normalize:
            for y in range(copy_height):
                row = matrix[y]
                copy_width = min(len(row), target_width)

                for x in range(copy_width):
                    self._set_base_pixel_rgb565(matrix_group, x, y, row[x])
            self.mark_dirty()
            return

        for y in range(copy_height):
            row = matrix[y]
            copy_width = min(len(row), target_width)

            for x in range(copy_width):
                self._set_base_pixel(matrix_group, x, y, row[x])
        self.mark_dirty()

    def set_pixel(self, matrix_group, x, y, value):
        """Nastavi jeden pixel uvnitr dane oblasti."""
        self._set_base_pixel(matrix_group, x, y, value)
        self.mark_dirty()

    def fill_matrix(self, matrix_group, value):
        """Vyplni celou oblast jednou barvou."""
        color = self.normalize_color(value)
        matrix_group["base_bitmap"].fill(0)
        matrix_group["bitmap"].fill(0)
        matrix_group["active_pixels"] = []

        if color == 0:
            self.mark_dirty()
            return

        for y in range(matrix_group["height"]):
            for x in range(matrix_group["width"]):
                self._set_base_pixel_rgb565(matrix_group, x, y, color)

        self._render_effect_for_matrix(matrix_group)
        self.mark_dirty()

    def refresh(self):
        """Odesle zmeny bitmap do fyzickeho displeje."""
        self._enforce_tilegrid_enabled_flags()
        if self.color_effect == COLOR_EFFECT_RAINBOW:
            self.rainbow_frame_counter += 1
            if self.rainbow_frame_counter >= RAINBOW_FRAME_SKIP:
                self.rainbow_frame_counter = 0
                self.effect_tick = (self.effect_tick + 1) % 256
                self._render_all_effects(visible_only=True)
                self.mark_dirty()
        if not self.dirty:
            return False
        self.window.refresh()
        self.dirty = False
        return True

    def set_color_effect(self, effect):
        """Nastavi globalni barevny efekt pro vsechny regiony."""
        if effect not in (COLOR_EFFECT_NORMAL, COLOR_EFFECT_RAINBOW):
            raise ValueError("Unsupported color effect")
        if self.color_effect == effect:
            return

        self.color_effect = effect
        if effect == COLOR_EFFECT_RAINBOW:
            self.effect_tick = 0
            self.rainbow_frame_counter = 0
        self._render_all_effects()
        self.mark_dirty()

    def set_matrix_color_effect(self, matrix_group, effect, color=None):
        """Nastavi barevny efekt jednoho regionu, pokud neni aktivni globalni duha."""
        if effect not in (COLOR_EFFECT_NORMAL, COLOR_EFFECT_RAINBOW, COLOR_EFFECT_SOLID):
            raise ValueError("Unsupported matrix color effect")

        solid_color = matrix_group["solid_effect_color"]
        if effect == COLOR_EFFECT_SOLID:
            if color is None:
                raise ValueError("Solid color effect requires a color")
            solid_color = self.normalize_color(color)

        if (
            matrix_group["color_effect"] == effect
            and matrix_group["solid_effect_color"] == solid_color
        ):
            return

        matrix_group["color_effect"] = effect
        matrix_group["solid_effect_color"] = solid_color
        self._render_effect_for_matrix(matrix_group)
        self.mark_dirty()

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
        self._set_base_pixel_rgb565(matrix_group, x, y, color)

    def _set_base_pixel_rgb565(self, matrix_group, x, y, color):
        """Ulozi uz normalizovany RGB565 pixel bez opakovane konverze."""
        if matrix_group.get("mirror_x", False):
            x = matrix_group["width"] - 1 - x

        matrix_group["base_bitmap"][x, y] = color
        if color != 0:
            matrix_group["active_pixels"].append((x, y))
        matrix_group["bitmap"][x, y] = self._apply_color_effect(
            matrix_group,
            color,
            x,
            y,
        )

    def _render_all_effects(self, visible_only=False):
        """Prekresli vsechny regiony z ulozenych puvodnich pixelu."""
        for matrix_group in self.matrix_groups:
            if visible_only and matrix_group["tile"].hidden:
                continue
            self._render_effect_for_matrix(matrix_group)

    def _render_effect_for_matrix(self, matrix_group):
        """Prekresli jeden region podle aktualniho barevneho efektu."""
        base_bitmap = matrix_group["base_bitmap"]
        bitmap = matrix_group["bitmap"]
        effect = self._get_matrix_color_effect(matrix_group)

        if effect == COLOR_EFFECT_RAINBOW:
            wheel = self.rainbow_wheel
            tick_offset = self.effect_tick * RAINBOW_SPEED
            x_scale = RAINBOW_X_SCALE
            y_scale = RAINBOW_Y_SCALE
            for x, y in matrix_group["active_pixels"]:
                if base_bitmap[x, y] == 0:
                    bitmap[x, y] = 0
                else:
                    bitmap[x, y] = wheel[
                        (x * x_scale + y * y_scale + tick_offset) & 0xFF
                    ]
            return

        if effect == COLOR_EFFECT_SOLID:
            solid_color = matrix_group["solid_effect_color"]
            for x, y in matrix_group["active_pixels"]:
                bitmap[x, y] = solid_color if base_bitmap[x, y] != 0 else 0
            return

        for x, y in matrix_group["active_pixels"]:
            bitmap[x, y] = base_bitmap[x, y]

    def _get_matrix_color_effect(self, matrix_group):
        """Vrati efekt regionu; globalni duha ma vzdy vyssi prioritu."""
        if self.color_effect == COLOR_EFFECT_RAINBOW:
            return COLOR_EFFECT_RAINBOW
        return matrix_group["color_effect"]

    def _apply_color_effect(self, matrix_group, color, x, y):
        """Vrati pixel po aplikaci aktualniho efektu."""
        if color == 0:
            return color

        effect = self._get_matrix_color_effect(matrix_group)
        if effect == COLOR_EFFECT_RAINBOW:
            return self._rainbow_rgb565(x, y)
        if effect == COLOR_EFFECT_SOLID:
            return matrix_group["solid_effect_color"]
        return color

    def _create_rainbow_wheel(self):
        """Predpocita jednu periodu rainbow barev v RGB565."""
        wheel = []
        for index in range(256):
            pos = index
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

            wheel.append(self.rgb888_to_rgb565((red << 16) | (green << 8) | blue))
        return wheel

    def _rainbow_rgb565(self, x, y):
        """Vygeneruje RGB565 barvu z posunuteho color-wheel indexu."""
        pos = (
            x * RAINBOW_X_SCALE
            + y * RAINBOW_Y_SCALE
            + self.effect_tick * RAINBOW_SPEED
        ) & 0xFF

        return self.rainbow_wheel[pos]

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
        matrix_group["active_pixels"] = []

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
        self.mark_dirty()

    def load_bmp_into_matrix(self, matrix_group, source):
        """Nahraje BMP nebo pametovou bitmapu a premaluje ji do RGB565 bitmapy."""
        matrix = self.get_image_matrix_rgb565(source)
        self.update_matrix_rgb565(matrix_group, matrix)

    def get_image_matrix_rgb565(self, source):
        """Nacte obrazkovy zdroj do RGB565 radku a umozni jejich sdileni s prechody."""
        # Zdroj muze byt bud cesta k souboru, nebo dvojice `(bitmap, pixel_shader)`.
        if isinstance(source, str):
            cached_matrix = self.image_cache.get(source)
            if cached_matrix is not None:
                return cached_matrix

            if source.lower().endswith(".bmp"):
                try:
                    matrix = self._load_24bit_bmp_rows(source)
                    self.image_cache[source] = matrix
                    return matrix
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

        if isinstance(source, str):
            self.image_cache[source] = matrix

        return matrix
