import board
import displayio
import framebufferio
import rgbmatrix
import adafruit_imageload


class FaceDisplay:
    EYE_SIZE = (32, 32)
    NOSE_SIZE = (32, 32)
    MOUTH_SIZE = (64, 32)

    def __init__(self):
        displayio.release_displays()

        self.matrix = rgbmatrix.RGBMatrix(
            width=64,
            height=32,
            bit_depth=4,
            rgb_pins=[
                board.MTX_R1,
                board.MTX_B1,
                board.MTX_G1,
                board.MTX_R2,
                board.MTX_B2,
                board.MTX_G2,
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

        self.display = framebufferio.FramebufferDisplay(
            self.matrix,
            auto_refresh=False,
        )

        palette_nose = displayio.Palette(2)
        palette_nose[0] = 0x000000
        palette_nose[1] = 0x100000

        palette_eye = displayio.Palette(2)
        palette_eye[0] = 0x000000
        palette_eye[1] = 0x001000

        palette_mouth = displayio.Palette(2)
        palette_mouth[0] = 0x000000
        palette_mouth[1] = 0x000010

        self.nose_bitmap = displayio.Bitmap(self.NOSE_SIZE[0], self.NOSE_SIZE[1], 2)
        self.eye_bitmap = displayio.Bitmap(self.EYE_SIZE[0], self.EYE_SIZE[1], 2)
        self.mouth_bitmap = displayio.Bitmap(self.MOUTH_SIZE[0], self.MOUTH_SIZE[1], 2)

        nose_tile = displayio.TileGrid(
            self.nose_bitmap,
            pixel_shader=palette_nose,
            x=0,
            y=0,
        )
        eye_tile = displayio.TileGrid(
            self.eye_bitmap,
            pixel_shader=palette_eye,
            x=32,
            y=0,
        )
        mouth_tile = displayio.TileGrid(
            self.mouth_bitmap,
            pixel_shader=palette_mouth,
            x=0,
            y=16,
        )

        group = displayio.Group()
        group.append(nose_tile)
        group.append(eye_tile)
        group.append(mouth_tile)
        self.display.root_group = group

        self.nose_matrix = self._create_matrix(*self.NOSE_SIZE)
        self.eye_matrix = self._create_matrix(*self.EYE_SIZE)
        self.mouth_matrix = self._create_matrix(*self.MOUTH_SIZE)

        # Kazda cast muze byt bud "rect", nebo "bmp".
        # U bmp se libovolny nenulovy pixel prevede na hodnotu 1.
        self.face_parts = [
            {
                "type": "rect",
                "matrix": self.eye_matrix,
                "base_x": 20,
                "base_y": 3,
                "width": 8,
                "height": 4,
                "value": 1,
            },
            {
                "type": "rect",
                "matrix": self.nose_matrix,
                "base_x": 5,
                "base_y": 5,
                "width": 6,
                "height": 2,
                "value": 1,
            },
            {
                "type": "rect",
                "matrix": self.mouth_matrix,
                "base_x": 0,
                "base_y": 8,
                "width": 20,
                "height": 4,
                "value": 1,
            },
        ]

    def _create_matrix(self, width, height):
        return [[0 for _ in range(width)] for _ in range(height)]

    def clear_matrix(self, matrix, value=0):
        for y in range(len(matrix)):
            for x in range(len(matrix[0])):
                matrix[y][x] = value

    def load_bmp_matrix(self, file_path):
        """
        Nacte BMP do 2D matice 0/1.
        Kazdy nenulovy pixel se bere jako zapnuty.
        """
        bitmap, _palette = adafruit_imageload.load(
            file_path,
            bitmap=displayio.Bitmap,
            palette=displayio.Palette,
        )

        image_matrix = []
        for y in range(bitmap.height):
            row = []
            for x in range(bitmap.width):
                row.append(1 if bitmap[x, y] else 0)
            image_matrix.append(row)
        return image_matrix

    def draw_rectangle(self, matrix, x, y, width, height, value):
        for row in range(y, y + height):
            for col in range(x, x + width):
                matrix[row][col] = value

    def draw_image(self, matrix, x, y, image_matrix, value=1):
        image_height = len(image_matrix)
        image_width = len(image_matrix[0])

        for row in range(image_height):
            for col in range(image_width):
                if image_matrix[row][col]:
                    matrix[y + row][x + col] = value

    def copy_matrix_to_bitmap(self, data, bitmap):
        for y in range(len(data)):
            for x in range(len(data[0])):
                bitmap[x, y] = data[y][x]

    def clamp(self, value, min_value, max_value):
        return max(min_value, min(value, max_value))

    def get_rect_position(
        self,
        matrix,
        base_x,
        base_y,
        offset_x,
        offset_y,
        rect_width,
        rect_height,
    ):
        rect_x = self.clamp(base_x + offset_x, 0, len(matrix[0]) - rect_width)
        rect_y = self.clamp(base_y + offset_y, 0, len(matrix) - rect_height)
        return rect_x, rect_y

    def draw_offset_shape(
        self,
        part,
        offset_x,
        offset_y,
    ):
        matrix = part["matrix"]
        base_x = part["base_x"]
        base_y = part["base_y"]
        value = part.get("value", 1)

        if part["type"] == "rect":
            shape_width = part["width"]
            shape_height = part["height"]
        else:
            shape_width = len(part["image"][0])
            shape_height = len(part["image"])

        rect_x, rect_y = self.get_rect_position(
            matrix,
            base_x,
            base_y,
            offset_x,
            offset_y,
            shape_width,
            shape_height,
        )

        if part["type"] == "rect":
            self.draw_rectangle(
                matrix,
                rect_x,
                rect_y,
                part["width"],
                part["height"],
                value,
            )
        else:
            self.draw_image(
                matrix,
                rect_x,
                rect_y,
                part["image"],
                value,
            )

    def set_part_bmp(self, index, file_path, base_x=None, base_y=None, value=1):
        """
        Prepnuti casti z rect na bmp.
        index: poradi v self.face_parts
        file_path: cesta k BMP souboru na CIRCUITPY
        """
        image_matrix = self.load_bmp_matrix(file_path)
        part = self.face_parts[index]
        part["type"] = "bmp"
        part["image"] = image_matrix
        part["value"] = value

        if base_x is not None:
            part["base_x"] = base_x
        if base_y is not None:
            part["base_y"] = base_y

    def update(self, offset_x, offset_y):
        self.clear_matrix(self.eye_matrix)
        self.clear_matrix(self.nose_matrix)
        self.clear_matrix(self.mouth_matrix)

        for part in self.face_parts:
            self.draw_offset_shape(part, offset_x, offset_y)

        self.copy_matrix_to_bitmap(self.nose_matrix, self.nose_bitmap)
        self.copy_matrix_to_bitmap(self.eye_matrix, self.eye_bitmap)
        self.copy_matrix_to_bitmap(self.mouth_matrix, self.mouth_bitmap)
        self.display.refresh()
