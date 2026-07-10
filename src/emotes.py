"""Program prepina emote obliceje, prehrava GIFy a kresli fullscreen hodiny."""

# Importy pro praci s bitmapami, GIFy a casem.
import gc
import displayio
import gifio
import time

# Jednoduchy 5x7 font pouzity pro fullscreen hodiny na RGB matici.
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

BLINKING_SLOWER = 25
BOOP_PROXIMITY_THRESHOLD = 225
MIC_SPEAK_THRESHOLD = 15
MIC_RELEASE_THRESHOLD = 8
MIC_SPEAK_HOLD_FRAMES = 6
MIC_CONTROLS_MOUTH = False


# Zakladni stavebni bloky pro regiony a jejich zdroje.
def create_region(name, matrix_group, idle_source=None, hidden_when_idle=False):
    """Vytvori stav jedne vykreslovane oblasti obliceje."""
    return {
        "name": name,
        "matrix": matrix_group,
        "idle_source": idle_source,
        "hidden_when_idle": hidden_when_idle,
        "active": False,
        "elapsed": 0,
        "current_source": None,
        "duration": 0,
        # Stav GIF prehravani zustava mezi iteracemi hlavni smycky.
        "player": None,
        "is_gif": False,
        "loop": False,
        "frame_index": 0,
        "frame_count": 0,
    }


def _get_source_content(source):
    """Vrati obsah zdroje jako cestu nebo bitmapovy payload."""
    if isinstance(source, dict):
        return source["content"]
    return source


def _get_source_name(source):
    """Vrati kratke jmeno aktivniho zdroje pro debug a stav."""
    if isinstance(source, dict):
        return source["name"]
    if isinstance(source, str):
        return source.split("/")[-1]
    if source is None:
        return "idle"
    return "custom"


def _get_source_type(source):
    """Vrati logicky typ zdroje pouzity pri nahravani do regionu."""
    if isinstance(source, dict):
        return source.get("type", "image")
    return "image"


def _clear_region_player(region):
    """Uvolni GIF prehravac prirazeny k regionu."""
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
    """Nahraje novy zdroj do regionu a pripravi stav animace."""
    region["matrix"]["tile"].hidden = False
    source_type = _get_source_type(source)

    _clear_region_player(region)

    if source_type == "gif":
        # GIF se neprepocitava dopredu. Jen se otevre soubor a pripravi prvni frame.
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
    """Posune animovany region o jeden GIF frame."""
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
    """Ukonci aktivni emote a vrati region do idle stavu."""
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
    """Posune jeden region v case a pripadne do nej prepne novy zdroj."""
    emote_started = False

    if source is not None:
        # Kdyz prisel novy zdroj, region se prepne nebo pokracuje v animaci.
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


# Tovarny pro jednotny format emote zdroju.
def get_emote_name(region):
    """Vrati jmeno zdroje, ktery je v regionu prave aktivni."""
    return _get_source_name(region["current_source"])


def create_image_emote(path, name=None):
    """Zabali bitmapovy asset do struktury pouzivane controllerem."""
    return {
        "type": "image",
        "name": name or path.split("/")[-1],
        "content": path,
    }


def create_gif_emote(path, name=None, loop=False):
    """Zabali GIF asset do struktury pouzivane controllerem."""
    return {
        "type": "gif",
        "name": name or path.split("/")[-1],
        "content": path,
        "loop": loop,
    }


def _draw_char(bitmap, char, x, y, scale=2, color=1):
    """Nakresli jeden zvetseny znak 5x7 do bitmapy."""
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
    """Vykresli aktualni cas do bitmapy o velikosti `64x32`."""
    if device_clock is not None:
        text = device_clock.get_time()
    else:
        now = time.localtime()
        text = "{:02}:{:02}".format(now.tm_hour, now.tm_min)

    return create_time_bitmap_from_text(text)


def create_time_bitmap_from_text(text):
    """Vykresli predany casovy text do bitmapy o velikosti `64x32`."""
    bitmap = displayio.Bitmap(64, 32, 2)
    palette = displayio.Palette(2)
    palette[0] = 0x000000
    palette[1] = 0xFFFFFF

    # Font se zvetsi 2x, aby byl na 64x32 matici jeste dobre citelny.
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
    """Vytvori fullscreen emote se zobrazenym aktualnim casem."""
    return {
        "name": "clock",
        "content": create_time_bitmap(device_clock),
    }


class FaceEmoteController:
    """Ridi emote regionu obliceje a jejich reakce v kazde iteraci smycky."""

    def __init__(
        self,
        display,
        eye_matrix,
        nose_matrix,
        mouth_matrix,
        whole_matrix,
        *,
        secondary_faces=None,
        blink_enabled=True,
        blink_time_set=10,
        emote_timer=20,
        boop_timer=5,
        boop_rainbow_enabled=True,
        rainbow_override_enabled=False,
        blink_emote_timer=None,
        verbose=False,
    ):
        # Controller drzi odkazy na vsechny regiony a jejich casovani.
        self.display = display
        self.eye_matrix = eye_matrix
        self.nose_matrix = nose_matrix
        self.mouth_matrix = mouth_matrix
        self.whole_matrix = whole_matrix
        self.secondary_faces = secondary_faces or []
        self.verbose = verbose

        self.blink_enabled = blink_enabled
        self.blink_time_set = blink_time_set
        self.emote_timer = emote_timer
        self.boop_timer = boop_timer
        self.boop_rainbow_enabled = boop_rainbow_enabled
        self.rainbow_override_enabled = rainbow_override_enabled
        self.blink_emote_timer = (
            blink_emote_timer
            if blink_emote_timer is not None
            else max(1, blink_time_set // 6)
        )
        self.blink_time = 0
        self.mic_speak_hold = 0
        self.clock_emote = None
        self.clock_text = None

        # Zde jsou zaregistrovane vsechny assety, ktere controller umi pouzit.
        self.eye_idle_emote = create_image_emote("/faces/eye.bmp", "eye")
        self.eye_sleep_emote = create_image_emote("/faces/sleep.bmp", "sleep")
        self.eye_blink_emote = create_image_emote("/faces/eye_blink.bmp", "blink")
        self.eye_boop_emote = create_image_emote("/faces/eye_open.bmp", "boop")
        self.nose_idle_source = "/faces/nose.bmp"
        self.mouth_idle_emote = create_image_emote("/faces/mouth.bmp", "mouth")
        self.mouth_speak_emote = create_image_emote("/faces/mouth_speak.bmp", "speak")
        self.eye_load_emote = create_gif_emote("/faces/giphy.gif", "load", loop=False)
        self.cross_emote = create_image_emote("/faces/cross.bmp", "cross")
        self.whole_dice_roll = create_gif_emote("/faces/dice.gif", "dice", loop=False)
        self.color_test = create_image_emote("/faces/test_colors.bmp","color")
        # Template: sem pridej novy asset pro emote.
        # self.eye_happy_emote = create_image_emote("/faces/eye_happy.bmp", "happy")
        # self.mouth_smile_emote = create_image_emote("/faces/mouth_smile.bmp", "smile")
        # self.eye_blink_emote = create_gif_emote("/faces/eye_blink.gif", "blink", loop=False)

        # Kazdy region ma vlastni runtime stav a muze mit jiny zdroj i delku trvani.
        primary_regions = self._create_face_regions(
            "primary",
            eye_matrix,
            nose_matrix,
            mouth_matrix,
            whole_matrix,
        )
        self.region_sets = [primary_regions]
        for index, face in enumerate(self.secondary_faces):
            self.region_sets.append(
                self._create_face_regions(
                    "secondary{}".format(index + 1),
                    face["eye"],
                    face["nose"],
                    face["mouth"],
                    face["whole"],
                )
            )

        self.eye_region = primary_regions["eye"]
        self.nose_region = primary_regions["nose"]
        self.mouth_region = primary_regions["mouth"]
        self.whole_region = primary_regions["whole"]

        # Fullscreen vrstva je v idle stavu schovana a pri startu se nactou idle obrazky obliceje.
        for regions in self.region_sets:
            regions["whole"]["matrix"]["tile"].hidden = True
            self.display.load_bmp_into_matrix(
                regions["eye"]["matrix"],
                _get_source_content(self.eye_idle_emote),
            )
            self.display.load_bmp_into_matrix(
                regions["nose"]["matrix"],
                self.nose_idle_source,
            )
            self.display.load_bmp_into_matrix(
                regions["mouth"]["matrix"],
                _get_source_content(self.mouth_idle_emote),
            )

    def _create_face_regions(
        self,
        suffix,
        eye_matrix,
        nose_matrix,
        mouth_matrix,
        whole_matrix,
    ):
        """Vytvori jednu kompletni sadu regionu obliceje."""
        return {
            "eye": create_region(
                "eye_{}".format(suffix),
                eye_matrix,
                self.eye_idle_emote,
            ),
            "nose": create_region(
                "nose_{}".format(suffix),
                nose_matrix,
                self.nose_idle_source,
            ),
            "mouth": create_region(
                "mouth_{}".format(suffix),
                mouth_matrix,
                self.mouth_idle_emote,
            ),
            "whole": create_region(
                "whole_{}".format(suffix),
                whole_matrix,
                hidden_when_idle=True,
            ),
        }

    def _set_face_hidden(self, hidden):
        """Skryje nebo zobrazi tri zakladni casti obliceje najednou."""
        for regions in self.region_sets:
            regions["eye"]["matrix"]["tile"].hidden = hidden
            regions["nose"]["matrix"]["tile"].hidden = hidden
            regions["mouth"]["matrix"]["tile"].hidden = hidden

    def _update_region_sets(self, requests):
        """Aplikuje stejne pozadavky na vsechny fyzicke sady regionu."""
        started = {}
        for regions in self.region_sets:
            for name in ("nose", "mouth", "eye", "whole"):
                _, region_started = update_emote(
                    self.display,
                    regions[name],
                    source=requests[name]["source"],
                    duration=requests[name]["duration"],
                    verbose=self.verbose,
                )
                started[name] = started.get(name, False) or region_started
        return started

    def _create_requests(self):
        """Pripravi prazdne pozadavky pro regiony v aktualni iteraci."""
        return {
            "eye": {"source": None, "duration": 0},
            "nose": {"source": None, "duration": 0},
            "mouth": {"source": None, "duration": 0},
            "whole": {"source": None, "duration": 0},
        }

    def _apply_active_menu_emote(self, requests, active_menu_emote, device_clock):
        """Prevede otevreny emote z menu na pozadavky pro jednotlive regiony."""
        if active_menu_emote is None:
            return False

        active_menu_emote = str(active_menu_emote).strip().lower()

        # Emote vybrany v menu ma prioritu pred automatickymi reakcemi senzoru.
        if active_menu_emote == "clock":
            requests["whole"]["source"] = self._get_clock_emote(device_clock)
            requests["whole"]["duration"] = 1
            return True

        if active_menu_emote == "gif":
            requests["whole"]["source"] = self.eye_load_emote
            requests["whole"]["duration"] = 1
            return True
        
        if active_menu_emote == "dice":
            requests["whole"]["source"] = self.whole_dice_roll
            requests["whole"]["duration"] = 1
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
        
        if active_menu_emote == "color":
            requests["eye"]["source"] = self.color_test
            requests["eye"]["duration"] = 1
            requests["mouth"]["source"] = self.color_test
            requests["mouth"]["duration"] = 1
            return True

        return False

    def _get_clock_emote(self, device_clock):
        """Vrati cached clock emote a prekresli ho jen pri zmene casu."""
        if device_clock is not None:
            text = device_clock.get_time()
        else:
            now = time.localtime()
            text = "{:02}:{:02}".format(now.tm_hour, now.tm_min)

        if self.clock_emote is None or self.clock_text != text:
            self.clock_emote = {
                "name": "clock",
                "content": create_time_bitmap_from_text(text),
            }
            self.clock_text = text

        return self.clock_emote

    def update(
        self,
        *,
        active_menu_emote=None,
        device_clock=None,
        mic_value=None,
        proximity_value=None,
    ):
        """Zpracuje vstupy a posune vsechny aktivni emote o jeden krok."""
        # Nejdriv se poskladaji pozadavky na jednotlive regiony pro tuto iteraci.
        requests = self._create_requests()
        menu_emote_active = self._apply_active_menu_emote(
            requests,
            active_menu_emote,
            device_clock,
        )

        if menu_emote_active:
            # Pri aktivnim menu emote se preskoci automaticke reakce mikrofonu, boop a blikani.
            started = self._update_region_sets(requests)
            self._set_face_hidden(self.whole_region["active"])
            self._sync_color_effect()
            self.blink_time = 0
            return started

        # Mikrofon meni jen region ust a jen pokud neni aktivni fullscreen vrstva.
        if (
            MIC_CONTROLS_MOUTH
            and not menu_emote_active
            and mic_value is not None
            and not self.whole_region["active"]
        ):
            if mic_value >= MIC_SPEAK_THRESHOLD:
                self.mic_speak_hold = MIC_SPEAK_HOLD_FRAMES
            elif mic_value <= MIC_RELEASE_THRESHOLD and self.mic_speak_hold > 0:
                self.mic_speak_hold -= 1

            if self.mic_speak_hold > 0:
                requests["mouth"]["source"] = self.mouth_speak_emote
                requests["mouth"]["duration"] = MIC_SPEAK_HOLD_FRAMES
                if self.verbose:
                    print("speak")

        # Proximity senzor aktivuje otevrene oko jako boop reakci.
        if (
            not menu_emote_active
            and
            proximity_value is not None
            and not self.whole_region["active"]
            and requests["eye"]["source"] is None
        ):
            if proximity_value > BOOP_PROXIMITY_THRESHOLD:
                requests["eye"]["source"] = self.eye_boop_emote
                requests["eye"]["duration"] = self.boop_timer

        # Automaticke blikani bezi jen kdyz oko zrovna nic jineho nezobrazuje.
        if (
            self.blink_enabled
            and not menu_emote_active
            and not self.whole_region["active"]
            and requests["eye"]["source"] is None
        ):
            if not self.eye_region["active"]:
                self.blink_time += 1
                if self.blink_time >= self.blink_time_set + BLINKING_SLOWER:
                    requests["eye"]["source"] = self.eye_blink_emote
                    requests["eye"]["duration"] = self.blink_emote_timer
                    self.blink_time = 0
            elif get_emote_name(self.eye_region) != "blink":
                self.blink_time = 0

        # Nakonec se vsechny regiony posunou o jeden krok podle sestavenych pozadavku.
        started = self._update_region_sets(requests)

        self._set_face_hidden(self.whole_region["active"])
        self._sync_color_effect()

        if any(started.values()) and get_emote_name(self.eye_region) != "blink":
            self.blink_time = 0

        return started

    def any_active(self):
        """Vrati `True`, kdyz je v nekterem regionu aktivni emote."""
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
        """Vrati nejdulezitejsi region pro hlaseni aktualniho stavu."""
        # Prioritu ma fullscreen vrstva, pak jednotlive casti obliceje.
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
        """Vrati `True`, kdyz je aktivni boop emote oka."""
        return get_emote_name(self.eye_region) == "boop"

    def set_boop_rainbow_enabled(self, enabled):
        """Zapne nebo vypne rainbow efekt navazany na boop."""
        self.boop_rainbow_enabled = enabled
        self._sync_color_effect()

    def set_rainbow_override_enabled(self, enabled):
        """Zapne nebo vypne rainbow efekt pro vsechny aktivni emote."""
        self.rainbow_override_enabled = enabled
        self._sync_color_effect()

    def _sync_color_effect(self):
        """Synchronizuje rainbow efekt podle boop a override nastaveni."""
        if self.rainbow_override_enabled:
            self.display.set_color_effect("rainbow")
            return

        if (
            self.boop_rainbow_enabled
            and self.is_boop_active()
            and not self.whole_region["active"]
        ):
            self.display.set_color_effect("rainbow")
        else:
            self.display.set_color_effect("normal")

    def shutdown(self):
        """Uvolni aktivni prehravace driv, nez se vypne displej."""
        for regions in self.region_sets:
            for region in (
                regions["eye"],
                regions["nose"],
                regions["mouth"],
                regions["whole"],
            ):
                _clear_region_player(region)
