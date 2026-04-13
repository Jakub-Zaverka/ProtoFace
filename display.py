"""Helpers for creating regions on the RGB matrix and drawing BMP content."""

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
    """Simple wrapper around the RGB matrix display."""

    def __init__(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, bit_depth=BIT_DEPTH):
        """Initialize the physical display and root group."""
        self.width = width
        self.height = height
        self.bit_depth = bit_depth
        self.matrix_groups = []

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

        self.window = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
        self.group = displayio.Group()
        self.window.root_group = self.group
        self.window.refresh()

    def create_matrix(self, name, position_x, position_y, matrix_width, matrix_height):
        """Create a bitmap-backed matrix region on the display."""
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
        """Convert a 2D list of pixels into a displayio bitmap."""
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
        """Copy a 2D list of pixels into an existing matrix region."""
        target_width = matrix_group["width"]
        target_height = matrix_group["height"]

        # Smazat starý obsah, aby po menším obrázku nezůstaly artefakty.
        matrix_group["bitmap"].fill(0)

        copy_height = min(len(matrix), target_height)

        for y in range(copy_height):
            row = matrix[y]
            copy_width = min(len(row), target_width)

            for x in range(copy_width):
                matrix_group["bitmap"][x, y] = row[x]


    def set_pixel(self, matrix_group, x, y, value):
        """Set a single pixel inside a matrix region."""
        matrix_group["bitmap"][x, y] = value

    def fill_matrix(self, matrix_group, value):
        """Fill an entire matrix region with one color value."""
        matrix_group["bitmap"].fill(value)

    def refresh(self):
        """Push pending bitmap changes to the display."""
        self.window.refresh()

    def matrix_to_list(self, matrix_group):
        """Return a matrix region as a nested Python list of palette indices."""
        bitmap = matrix_group["bitmap"]
        width = matrix_group["width"]
        height = matrix_group["height"]

        return [
            [bitmap[x, y] for x in range(width)]
            for y in range(height)
        ]

    def color_to_palette_index(self, color):
        """Map an RGB color to the closest color in the display palette."""
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

    def source_pixel_to_color(self, bitmap, pixel_shader, x, y):
        """Read one source pixel as an RGB integer."""
        pixel_value = bitmap[x, y]

        if isinstance(pixel_shader, displayio.Palette):
            return pixel_shader[pixel_value]

        return pixel_value

    def load_bmp_into_matrix(self, matrix_group, source):
        """Load a BMP path or in-memory bitmap and remap it into the current palette."""
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
