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


class Display:
    """Obsluhuje HUB75 matici a jeji rozdeleni na vykreslovaci oblasti."""

    def __init__(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, bit_depth=BIT_DEPTH):
        """Inicializuje fyzickou RGB matici a korenovou `displayio` groupu."""
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.matrix_groups = []

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
        tile = displayio.TileGrid(
            bitmap,
            pixel_shader=RGB565_CONVERTER,
            x=position_x,
            y=position_y,
        )
        matrix = {
            "name": name,
            "bitmap": bitmap,
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
                bitmap[x, y] = value

        return bitmap

    def update_matrix(self, matrix_group, matrix):
        """Prepise obsah existujici oblasti pixely z 2D seznamu."""
        target_width = matrix_group["width"]
        target_height = matrix_group["height"]

        # Smaze predchozi obsah, aby po mensim obrazku nezustaly artefakty.
        matrix_group["bitmap"].fill(0)

        copy_height = min(len(matrix), target_height)

        # Kopiruje se jen oblast, ktera se realne vejde do cilove bitmapy.
        for y in range(copy_height):
            row = matrix[y]
            copy_width = min(len(row), target_width)

            for x in range(copy_width):
                matrix_group["bitmap"][x, y] = row[x]

    def set_pixel(self, matrix_group, x, y, value):
        """Nastavi jeden pixel uvnitr dane oblasti."""
        matrix_group["bitmap"][x, y] = value

    def fill_matrix(self, matrix_group, value):
        """Vyplni celou oblast jednou barvou."""
        matrix_group["bitmap"].fill(value)

    def refresh(self):
        """Odesle zmeny bitmap do fyzickeho displeje."""
        self.window.refresh()

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
        bitmap = matrix_group["bitmap"]
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

        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def rgb565_to_rgb888(self, color):
        """Prevede jeden pixel z RGB565 na 24bit RGB."""
        r = (color >> 11) & 0x1F
        g = (color >> 5) & 0x3F
        b = color & 0x1F

        r = (r * 255) // 31
        g = (g * 255) // 63
        b = (b * 255) // 31

        return (r << 16) | (g << 8) | b

    def source_pixel_to_rgb565(self, bitmap, pixel_shader, x, y):
        """Precte zdrojovy pixel a vrati ho jako RGB565."""
        pixel_value = bitmap[x, y]

        if isinstance(pixel_shader, displayio.Palette):
            return self.rgb888_to_rgb565(pixel_shader[pixel_value])

        if isinstance(pixel_shader, displayio.ColorConverter):
            return pixel_shader.convert(pixel_value)

        if pixel_value <= 0xFFFF:
            return pixel_value

        return self.rgb888_to_rgb565(pixel_value)

    def load_gif_frame_into_matrix(self, matrix_group, bitmap, pixel_shader=None):
        """Nahraje aktualni GIF frame do dane oblasti RGB matice."""
        matrix_group["bitmap"].fill(0)

        copy_width = min(bitmap.width, matrix_group["width"])
        copy_height = min(bitmap.height, matrix_group["height"])

        for y in range(copy_height):
            for x in range(copy_width):
                pixel_value = bitmap[x, y]

                # GIF frame z `gifio` byva RGB565, pripadne se vezme barva z palety GIFu.
                if pixel_shader is not None and isinstance(pixel_shader, displayio.Palette):
                    matrix_group["bitmap"][x, y] = self.rgb888_to_rgb565(
                        pixel_shader[pixel_value]
                    )
                else:
                    matrix_group["bitmap"][x, y] = pixel_value

    def load_bmp_into_matrix(self, matrix_group, source):
        """Nahraje BMP nebo pametovou bitmapu a premaluje ji do RGB565 bitmapy."""
        # Zdroj muze byt bud cesta k souboru, nebo dvojice `(bitmap, pixel_shader)`.
        if isinstance(source, str):
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
