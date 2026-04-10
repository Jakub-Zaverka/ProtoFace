import board
import displayio
import framebufferio
import rgbmatrix

DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 32
BIT_DEPTH = 4

PALETTE = displayio.Palette(2)
PALETTE[0] = 0x000000
PALETTE[1] = 0x101010


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
        if len(matrix) != matrix_group["height"]:
            raise ValueError("Matrix height does not match the created bitmap.")

        for y, row in enumerate(matrix):
            if len(row) != matrix_group["width"]:
                raise ValueError("Matrix width does not match the created bitmap.")

            for x, value in enumerate(row):
                matrix_group["bitmap"][x, y] = value

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
        bitmap = matrix_group["bitmap"]
        width = matrix_group["width"]
        height = matrix_group["height"]

        return [
            [bitmap[x, y] for x in range(width)]
            for y in range(height)
        ]
