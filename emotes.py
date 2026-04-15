"""Emote assets and runtime logic for face regions shown on the matrix."""

import gc
import displayio
import gifio
import time

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
    """Create bookkeeping state for one drawable face region."""
    return {
        "name": name,
        "matrix": matrix_group,
        "idle_source": idle_source,
        "hidden_when_idle": hidden_when_idle,
        "active": False,
        "elapsed": 0,
        "current_source": None,
        "duration": 0,
        # Keep animated-source state alive between main-loop ticks.
        "player": None,
        "is_gif": False,
        "loop": False,
        "frame_index": 0,
        "frame_count": 0,
    }


def _get_source_content(source):
    """Normalize a source object to raw bitmap content or a file path."""
    if isinstance(source, dict):
        return source["content"]
    return source


def _get_source_name(source):
    """Return a short human-readable name for a source payload."""
    if isinstance(source, dict):
        return source["name"]
    if isinstance(source, str):
        return source.split("/")[-1]
    if source is None:
        return "idle"
    return "custom"


def _get_source_type(source):
    """Return the logical source type used by the region loader."""
    if isinstance(source, dict):
        return source.get("type", "image")
    return "image"


def _clear_region_player(region):
    """Release any GIF player currently attached to the region."""
    player = region["player"]
    if player is not None:
        player.deinit()
        region["player"] = None
        gc.collect()

    region["is_gif"] = False
    region["loop"] = False
    region["frame_index"] = 0
    region["frame_count"] = 0


def _load_source_into_region(display, region, source):
    """Load a new source into the region and initialize animation state."""
    region["matrix"]["tile"].hidden = False
    source_type = _get_source_type(source)

    _clear_region_player(region)

    if source_type == "gif":
        path = _get_source_content(source)
        player = gifio.OnDiskGif(path)
        player.next_frame()

        display.load_gif_frame_into_matrix(
            region["matrix"],
            player.bitmap,
            player.palette,
        )

        region["player"] = player
        region["is_gif"] = True
        region["loop"] = source.get("loop", False)
        region["frame_index"] = 0
        region["frame_count"] = player.frame_count
        return

    display.load_bmp_into_matrix(region["matrix"], _get_source_content(source))


def _tick_gif_region(display, region):
    """Advance an animated region by exactly one GIF frame."""
    player = region["player"]
    if player is None:
        return False

    if region["frame_count"] <= 1:
        return region["loop"]

    if region["frame_index"] + 1 >= region["frame_count"]:
        if not region["loop"]:
            return False

        path = _get_source_content(region["current_source"])
        player.deinit()

        player = gifio.OnDiskGif(path)
        player.next_frame()

        region["player"] = player
        region["frame_index"] = 0
        region["frame_count"] = player.frame_count

        display.load_gif_frame_into_matrix(
            region["matrix"],
            player.bitmap,
            player.palette,
        )
        return True

    player.next_frame()
    region["frame_index"] += 1

    display.load_gif_frame_into_matrix(
        region["matrix"],
        player.bitmap,
        player.palette,
    )
    return True


def _reset_region_to_idle(display, region):
    """Stop the active source and restore the region idle image."""
    _clear_region_player(region)

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


def update_emote(display, region, source=None, duration=0, verbose=False):
    """Advance one region and swap in a new source when requested."""
    emote_started = False

    if source is not None:
        if not region["active"] or region["current_source"] != source:
            _load_source_into_region(display, region, source)
            emote_started = True
            if verbose:
                print("emote")
                print(region["name"], _get_source_name(source))
        elif region["is_gif"]:
            if not _tick_gif_region(display, region):
                _load_source_into_region(display, region, source)

        region["active"] = True
        region["elapsed"] = 0
        region["current_source"] = source
        region["duration"] = duration

    elif region["active"]:
        region["elapsed"] += 1

        if region["is_gif"]:
            if not _tick_gif_region(display, region):
                _reset_region_to_idle(display, region)
        elif region["elapsed"] >= region["duration"]:
            _reset_region_to_idle(display, region)

    return region["active"], emote_started


def get_emote_name(region):
    """Return the display name of the source currently active in a region."""
    return _get_source_name(region["current_source"])


def create_image_emote(path, name=None):
    """Wrap an image path in the emote source structure used by the controller."""
    return {
        "type": "image",
        "name": name or path.split("/")[-1],
        "content": path,
    }


def create_gif_emote(path, name=None, loop=False):
    """Wrap a GIF path in the emote source structure used by the controller."""
    return {
        "type": "gif",
        "name": name or path.split("/")[-1],
        "content": path,
        "loop": loop,
    }


def _draw_char(bitmap, char, x, y, scale=2, color=1):
    """Draw one scaled 5x7 glyph into a bitmap."""
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


def create_time_bitmap(device_clock=None):
    """Render the current device time into a 64x32 bitmap."""
    if device_clock is not None:
        text = device_clock.get_time()
    else:
        now = time.localtime()
        text = "{:02}:{:02}".format(now.tm_hour, now.tm_min)

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
    """Create a fullscreen emote source containing the current time."""
    return {
        "name": "clock",
        "content": create_time_bitmap(device_clock),
    }


class FaceEmoteController:
    """Manage face-region emotes and their per-loop update rules."""

    def __init__(
        self,
        display,
        eye_matrix,
        nose_matrix,
        mouth_matrix,
        whole_matrix,
        *,
        blink_enabled=True,
        blink_time_set=10,
        emote_timer=20,
        boop_timer=5,
        blink_emote_timer=None,
        verbose=False,
    ):
        self.display = display
        self.eye_matrix = eye_matrix
        self.nose_matrix = nose_matrix
        self.mouth_matrix = mouth_matrix
        self.whole_matrix = whole_matrix
        self.verbose = verbose

        self.blink_enabled = blink_enabled
        self.blink_time_set = blink_time_set
        self.emote_timer = emote_timer
        self.boop_timer = boop_timer
        self.blink_emote_timer = (
            blink_emote_timer
            if blink_emote_timer is not None
            else max(1, blink_time_set // 6)
        )
        self.blink_time = 0

        self.eye_idle_emote = create_image_emote("/faces/eye.bmp", "eye")
        self.eye_sleep_emote = create_image_emote("/faces/sleep.bmp", "sleep")
        self.eye_blink_emote = create_image_emote("/faces/eye_blink.bmp", "blink")
        self.eye_boop_emote = create_image_emote("/faces/eye_open.bmp", "boop")
        self.nose_idle_source = "/faces/nose.bmp"
        self.mouth_idle_emote = create_image_emote("/faces/mouth.bmp", "mouth")
        self.mouth_speak_emote = create_image_emote("/faces/mouth_speak.bmp", "speak")
        self.eye_load_emote = create_gif_emote("/faces/giphy.gif", "load", loop=False)
        self.cross_emote = create_image_emote("/faces/cross.bmp", "cross")
        # Template: sem pridej novy asset pro emote.
        # self.eye_happy_emote = create_image_emote("/faces/eye_happy.bmp", "happy")
        # self.mouth_smile_emote = create_image_emote("/faces/mouth_smile.bmp", "smile")
        # self.eye_blink_emote = create_gif_emote("/faces/eye_blink.gif", "blink", loop=False)


        self.eye_region = create_region("eye", eye_matrix, self.eye_idle_emote)
        self.nose_region = create_region("nose", nose_matrix, self.nose_idle_source)
        self.mouth_region = create_region("mouth", mouth_matrix, self.mouth_idle_emote)
        self.whole_region = create_region("whole", whole_matrix, hidden_when_idle=True)

        self.whole_matrix["tile"].hidden = True
        self.display.load_bmp_into_matrix(
            self.eye_matrix,
            _get_source_content(self.eye_idle_emote),
        )
        self.display.load_bmp_into_matrix(
            self.nose_matrix,
            self.nose_idle_source,
        )
        self.display.load_bmp_into_matrix(
            self.mouth_matrix,
            _get_source_content(self.mouth_idle_emote),
        )

    def _set_face_hidden(self, hidden):
        """Hide or show the three face-part regions together."""
        self.eye_matrix["tile"].hidden = hidden
        self.nose_matrix["tile"].hidden = hidden
        self.mouth_matrix["tile"].hidden = hidden

    def _create_requests(self):
        """Build an empty per-region request map for the current frame."""
        return {
            "eye": {"source": None, "duration": 0},
            "nose": {"source": None, "duration": 0},
            "mouth": {"source": None, "duration": 0},
            "whole": {"source": None, "duration": 0},
        }

    def _apply_active_menu_emote(self, requests, active_menu_emote, device_clock):
        """Map the currently opened emote detail to persistent region requests."""
        if active_menu_emote is None:
            return False

        active_menu_emote = str(active_menu_emote).strip().lower()

        if active_menu_emote == "clock":
            requests["whole"]["source"] = create_clock_emote(device_clock)
            requests["whole"]["duration"] = 1
            return True

        if active_menu_emote == "gif":
            requests["eye"]["source"] = self.eye_load_emote
            requests["eye"]["duration"] = 1
            return True

        if active_menu_emote == "cross":
            requests["eye"]["source"] = self.cross_emote
            requests["eye"]["duration"] = 1
            return True
        
        if active_menu_emote == "sleep":
            requests["eye"]["source"] = self.eye_sleep_emote
            requests["eye"]["duration"] = 1
            return True

        if active_menu_emote == "open eye":
            requests["eye"]["source"] = self.eye_boop_emote
            requests["eye"]["duration"] = 1
            requests["mouth"]["source"] = self.mouth_speak_emote
            requests["mouth"]["duration"] = 1
            return True

        return False

    def update(
        self,
        *,
        active_menu_emote=None,
        device_clock=None,
        mic_value=None,
        proximity_value=None,
    ):
        """Update region requests from inputs and advance all active emotes."""
        requests = self._create_requests()
        menu_emote_active = self._apply_active_menu_emote(
            requests,
            active_menu_emote,
            device_clock,
        )

        if menu_emote_active:
            started = {}
            for name, region in (
                ("nose", self.nose_region),
                ("mouth", self.mouth_region),
                ("eye", self.eye_region),
                ("whole", self.whole_region),
            ):
                _, started[name] = update_emote(
                    self.display,
                    region,
                    source=requests[name]["source"],
                    duration=requests[name]["duration"],
                    verbose=self.verbose,
                )

            self._set_face_hidden(self.whole_region["active"])
            self.blink_time = 0
            return started

        # Template pro novy trigger:
        # if podminka and not self.whole_region["active"]:
        #     requests["eye"]["source"] = self.eye_happy_emote
        #     requests["eye"]["duration"] = self.emote_timer
        #
        # Dostupne regiony:
        #   requests["eye"]
        #   requests["nose"]
        #   requests["mouth"]
        #   requests["whole"]
        #
        # Kdyz chces fullscreen emote, pouzij requests["whole"].
        # Kdyz nechces prepsat uz zvoleny eye emote, pridej:
        #   and requests["eye"]["source"] is None

        if not menu_emote_active and mic_value is not None and not self.whole_region["active"]:
            if mic_value > 5:
                requests["mouth"]["source"] = self.mouth_speak_emote
                requests["mouth"]["duration"] = 1
                if self.verbose:
                    print("speak")

        if (
            not menu_emote_active
            and
            proximity_value is not None
            and not self.whole_region["active"]
            and requests["eye"]["source"] is None
        ):
            if proximity_value > 200:
                requests["eye"]["source"] = self.eye_boop_emote
                requests["eye"]["duration"] = self.boop_timer

        if (
            self.blink_enabled
            and not menu_emote_active
            and not self.whole_region["active"]
            and requests["eye"]["source"] is None
        ):
            if not self.eye_region["active"]:
                self.blink_time += 1
                if self.blink_time >= self.blink_time_set:
                    requests["eye"]["source"] = self.eye_blink_emote
                    requests["eye"]["duration"] = self.blink_emote_timer
                    self.blink_time = 0
            elif get_emote_name(self.eye_region) != "blink":
                self.blink_time = 0

        started = {}
        for name, region in (
            ("nose", self.nose_region),
            ("mouth", self.mouth_region),
            ("eye", self.eye_region),
            ("whole", self.whole_region),
        ):
            _, started[name] = update_emote(
                self.display,
                region,
                source=requests[name]["source"],
                duration=requests[name]["duration"],
                verbose=self.verbose,
            )

        self._set_face_hidden(self.whole_region["active"])

        if any(started.values()) and get_emote_name(self.eye_region) != "blink":
            self.blink_time = 0

        return started

    def any_active(self):
        """Return True when any face region currently shows a timed emote."""
        return any(
            region["active"]
            for region in (
                self.eye_region,
                self.nose_region,
                self.mouth_region,
                self.whole_region,
            )
        )

    def get_status_region(self):
        """Return the highest-priority region for status reporting."""
        if self.whole_region["active"]:
            return self.whole_region
        if self.eye_region["active"]:
            return self.eye_region
        if self.nose_region["active"]:
            return self.nose_region
        if self.mouth_region["active"]:
            return self.mouth_region
        return self.eye_region

    def is_boop_active(self):
        """Return True while the boop eye emote is currently active."""
        return get_emote_name(self.eye_region) == "boop"
