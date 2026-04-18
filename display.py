"""Program vytvari regiony RGB matice a prekresluje do nich bitmapy a GIF snimky."""

# Tato vrstva prevadi assety a bitmapy do male lokalni palety RGB matice.
import board
import displayio
import framebufferio
import rgbmatrix
import adafruit_imageload

DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 32
BIT_DEPTH = 4

PALETTE = displayio.Palette(4)
PALETTE[0] = 0x000000
PALETTE[1] = 0x101010
PALETTE[2] = 0x050505
PALETTE[3] = 0x020202


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
        # Kazdy region ma vlastni bitmapu, ale vsechny regiony sdili jednu root groupu.
        bitmap = displayio.Bitmap(matrix_width, matrix_height, len(PALETTE))
        tile = displayio.TileGrid(
            bitmap,
            pixel_shader=PALETTE,
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

    def to_bitmap(self, matrix, color_count=len(PALETTE)):
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
        """Vrati oblast jako vnoreny seznam indexu palety."""
        bitmap = matrix_group["bitmap"]
        width = matrix_group["width"]
        height = matrix_group["height"]

        return [
            [bitmap[x, y] for x in range(width)]
            for y in range(height)
        ]

    def color_to_palette_index(self, color):
        """Najde v lokalni palete nejblizsi barvu k zadanemu RGB vstupu."""
        # Matice pracuje s malou lokalni paletou, proto se hleda nejblizsi odstin.
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF

        best_index = 0
        best_distance = 1_000_000

        for i in range(len(PALETTE)):
            palette_color = PALETTE[i]
            pr = (palette_color >> 16) & 0xFF
            pg = (palette_color >> 8) & 0xFF
            pb = palette_color & 0xFF

            distance = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
            if distance < best_distance:
                best_distance = distance
                best_index = i

        return best_index

    def rgb565_to_rgb888(self, color):
        """Prevede jeden pixel z RGB565 na 24bit RGB."""
        r = (color >> 11) & 0x1F
        g = (color >> 5) & 0x3F
        b = color & 0x1F

        r = (r * 255) // 31
        g = (g * 255) // 63
        b = (b * 255) // 31

        return (r << 16) | (g << 8) | b

    def source_pixel_to_color(self, bitmap, pixel_shader, x, y):
        """Precte zdrojovy pixel a vrati ho jako RGB barvu."""
        pixel_value = bitmap[x, y]

        if isinstance(pixel_shader, displayio.Palette):
            return pixel_shader[pixel_value]

        return pixel_value

    def load_gif_frame_into_matrix(self, matrix_group, bitmap, pixel_shader=None):
        """Nahraje aktualni GIF frame do dane oblasti RGB matice."""
        matrix_group["bitmap"].fill(0)

        copy_width = min(bitmap.width, matrix_group["width"])
        copy_height = min(bitmap.height, matrix_group["height"])

        for y in range(copy_height):
            for x in range(copy_width):
                pixel_value = bitmap[x, y]

                # GIF frame z `gifio` byva RGB565, pokud GIF nema vlastni paletu.
                if pixel_shader is not None and isinstance(pixel_shader, displayio.Palette):
                    color = pixel_shader[pixel_value]
                else:
                    color = self.rgb565_to_rgb888(pixel_value)

                matrix_group["bitmap"][x, y] = self.color_to_palette_index(color)

    def load_bmp_into_matrix(self, matrix_group, source):
        """Nahraje BMP nebo pametovou bitmapu a premaluje ji do lokalni palety."""
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
                self.color_to_palette_index(
                    self.source_pixel_to_color(bitmap, pixel_shader, x, y)
                )
                for x in range(bitmap.width)
            ]
            for y in range(bitmap.height)
        ]

        self.update_matrix(matrix_group, matrix)
