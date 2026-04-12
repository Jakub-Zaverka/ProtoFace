import displayio

FONT_5X7 = {
    "0": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
}


def create_region(name, matrix_group, idle_source=None, hidden_when_idle=False):
    return {
        "name": name,
        "matrix": matrix_group,
        "idle_source": idle_source,
        "hidden_when_idle": hidden_when_idle,
        "active": False,
        "elapsed": 0,
        "current_source": None,
        "duration": 0,
    }


def _get_source_content(source):
    if isinstance(source, dict):
        return source["content"]
    return source


def _get_source_name(source):
    if isinstance(source, dict):
        return source["name"]
    if isinstance(source, str):
        return source.split("/")[-1]
    if source is None:
        return "idle"
    return "custom"


def update_emote(display, region, source=None, duration=0, verbose=False):
    emote_started = False

    if source is not None:
        if not region["active"] or region["current_source"] != source:
            region["matrix"]["tile"].hidden = False
            display.load_bmp_into_matrix(region["matrix"], _get_source_content(source))
            emote_started = True
            if verbose:
                print("emote")
                print(region["name"], _get_source_name(source))

        region["active"] = True
        region["elapsed"] = 0
        region["current_source"] = source
        region["duration"] = duration

    elif region["active"]:
        region["elapsed"] += 1

        if region["elapsed"] >= region["duration"]:
            region["active"] = False
            region["elapsed"] = 0
            region["current_source"] = None
            region["duration"] = 0
            region["matrix"]["tile"].hidden = region["hidden_when_idle"]

            if region["idle_source"] is not None:
                display.load_bmp_into_matrix(
                    region["matrix"],
                    _get_source_content(region["idle_source"]),
                )

    return region["active"], emote_started


def get_emote_name(region):
    return _get_source_name(region["current_source"])


def create_image_emote(path, name=None):
    return {
        "name": name or path.split("/")[-1],
        "content": path,
    }


def _draw_char(bitmap, char, x, y, scale=2, color=1):
    glyph = FONT_5X7[char]
    for row, row_bits in enumerate(glyph):
        for col, bit in enumerate(row_bits):
            if bit == "1":
                for dy in range(scale):
                    for dx in range(scale):
                        px = x + col * scale + dx
                        py = y + row * scale + dy
                        if 0 <= px < bitmap.width and 0 <= py < bitmap.height:
                            bitmap[px, py] = color


def create_time_bitmap(device_clock):
    text = device_clock.get_time()

    bitmap = displayio.Bitmap(64, 32, 2)
    palette = displayio.Palette(2)
    palette[0] = 0x000000
    palette[1] = 0xFFFFFF

    scale = 2
    char_width = 5 * scale
    char_height = 7 * scale
    spacing = 2

    text_width = len(text) * char_width + (len(text) - 1) * spacing
    start_x = (64 - text_width) // 2
    start_y = (32 - char_height) // 2

    x = start_x
    for char in text:
        _draw_char(bitmap, char, x, start_y, scale=scale, color=1)
        x += char_width + spacing

    return bitmap, palette


def create_clock_emote(device_clock):
    return {
        "name": "clock",
        "content": create_time_bitmap(device_clock),
    }
