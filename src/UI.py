"""Program ridi OLED menu, debug obrazovku a ovladani emote i nastaveni."""

# UI pracuje s OLED textovym vystupem a volitelnym HTTP ovladanim.
import time

from I2C_sim import get_font_char_width, get_font_line_height, OLEDDisplay
from server import ServerClass

# Konstanty pro nazvy obrazovek a geometrii textoveho layoutu.
SCREEN_MAIN_MENU = "main_menu"
SCREEN_MAIN_SCREEN = "main_screen"
SCREEN_EMOTES_MENU = "emotes_menu"
SCREEN_EMOTE_DETAIL = "emote_detail"
SCREEN_SETTINGS_MENU = "settings_menu"
SCREEN_DEBUG_MENU = "debug_menu"
CLOCK_Y = 0
CLOCK_PADDING = 2
TEXT_SCROLL_BASE_INTERVAL = 0.16
TEXT_SCROLL_SPEED_MULTIPLIER = 3
TEXT_SCROLL_INTERVAL = TEXT_SCROLL_BASE_INTERVAL
TEXT_SCROLL_HOLD_TICKS = 5

EVENT_SETTING_SELECTED = "setting_selected"


class UI():
    """Spravuje stav OLED menu a vraci akce vybrane uzivatelem."""

    def __init__(self, display:OLEDDisplay):
        """Inicializuje strukturu menu, kurzory a priznaky prekresleni."""
        self.display = display
        # Tyto seznamy urcuji, co se v menu skutecne zobrazi a v jakem poradi.
        self.main_menu_items = ["Emotes", "Settings", "Debug"]
        self.emotes_menu_items = ["Hearth", "Narrow", "Question", "Cross", "Open eye", "Sleep", "Blep", "Dead", "Clock", "Back"]
        self.settings_menu_items = [
            "Display",
            "Brightness",
            "Font",
            "Fan",
            "Boop",
            "Boop Calibrate",
            "Boop Rainbow",
            "Rainbow Override",
            "Mic",
            "Blink",
            "Accelerometer",
            "Wifi",
            # "Wifi Main",
            # "Wifi Backup",
            "Verbose",
            "Back",
        ]
        self.debug_lines = []
        self.setting_values = {
            "Display": False,
            "Boop": False,
            "Boop Calibrate": True,
            "Boop Rainbow": True,
            "Rainbow Override": False,
            "Wifi": False,
            # "Wifi Main": True,
            # "Wifi Backup": True,
            "Accelerometer": False,
            "Verbose": False,
            "Mic": False,
            "Blink": False,
            "Brightness": 0.5,
            "Font": "1.5x",
            "Fan": 0,
        }
        self.main_selected_index = 0
        self.emotes_selected_index = 0
        self.settings_selected_index = 0
        self.main_scroll_offset = 0
        self.emotes_scroll_offset = 0
        self.settings_scroll_offset = 0
        self.active_screen = SCREEN_MAIN_MENU
        self.selected_emote = None
        self.clock_text = "--:--"
        self.needs_render = True
        self.text_scroll_tick = 0
        self.text_scroll_last_update = 0.0
        self.text_scroll_active = False
        self.text_scroll_key = None

    def _consume_api_call(self, server: ServerClass, expected_value):
        """Spotrebuje jednu cekajici HTTP akci, pokud odpovida ocekavani."""
        if server is None or server.api_call != expected_value:
            return False
        server.api_call = ""
        return True

    def _move_selection(self, index_name, offset_name, items, step):
        """Posune kurzor v seznamu a udrzi spravny scroll viditelne casti."""
        # Vyber se pohybuje cyklicky od konce zase na zacatek.
        selected_index = (getattr(self, index_name) + step) % len(items)
        setattr(self, index_name, selected_index)
        setattr(
            self,
            offset_name,
            self.get_follow_scroll_offset(
                selected_index,
                getattr(self, offset_name),
                len(items),
            ),
        )
        self.needs_render = True

    def _open_main_selected_item(self):
        """Otevre vybranou polozku z hlavniho menu."""
        selected_item = self.main_menu_items[self.main_selected_index]
        if selected_item == "Emotes":
            self.active_screen = SCREEN_EMOTES_MENU
        elif selected_item == "Settings":
            self.active_screen = SCREEN_SETTINGS_MENU
        elif selected_item == "Debug":
            self.active_screen = SCREEN_DEBUG_MENU
        else:
            self.active_screen = SCREEN_MAIN_SCREEN
        self.needs_render = True

    def _open_selected_emote(self):
        """Otevre vybrany emote nebo se vrati do hlavniho menu."""
        selected_item = self.emotes_menu_items[self.emotes_selected_index]
        if selected_item == "Back":
            self.active_screen = SCREEN_MAIN_MENU
        else:
            self.selected_emote = selected_item
            self.active_screen = SCREEN_EMOTE_DETAIL
        self.needs_render = True

    def _select_setting_item(self):
        """Zpracuje potvrzeni na polozce v menu nastaveni."""
        selected_item = self.settings_menu_items[self.settings_selected_index]
        if selected_item == "Back":
            self.active_screen = SCREEN_MAIN_MENU
            self.needs_render = True
            return None

        self.needs_render = True
        return EVENT_SETTING_SELECTED, selected_item

    def _return_from_overlay_screen(self):
        """Vrati uzivatele z detailni nebo debug obrazovky zpet do menu."""
        if self.active_screen == SCREEN_MAIN_SCREEN:
            self.active_screen = SCREEN_MAIN_MENU
        elif self.active_screen == SCREEN_EMOTE_DETAIL:
            self.active_screen = SCREEN_EMOTES_MENU
        elif self.active_screen == SCREEN_DEBUG_MENU:
            self.active_screen = SCREEN_MAIN_MENU
        self.needs_render = True

    def handle_input(self, server:ServerClass ,confirm_click, next_click, prev_click=False, ):
        """Zpracuje tlacitka nebo HTTP prikazy a vrati pripadnou UI udalost."""
        # Chovani zavisi na tom, ktera obrazovka je prave otevrena.
        if self.active_screen == SCREEN_MAIN_MENU:
            if prev_click or self._consume_api_call(server, "up"):
                self._move_selection(
                    "main_selected_index",
                    "main_scroll_offset",
                    self.main_menu_items,
                    -1,
                )

            if next_click or self._consume_api_call(server, "down"):
                self._move_selection(
                    "main_selected_index",
                    "main_scroll_offset",
                    self.main_menu_items,
                    1,
                )

            if confirm_click or self._consume_api_call(server, "ok"):
                self._open_main_selected_item()
            return None

        if self.active_screen == SCREEN_EMOTES_MENU:
            if prev_click or self._consume_api_call(server, "up"):
                self._move_selection(
                    "emotes_selected_index",
                    "emotes_scroll_offset",
                    self.emotes_menu_items,
                    -1,
                )

            if next_click or self._consume_api_call(server, "down"):
                self._move_selection(
                    "emotes_selected_index",
                    "emotes_scroll_offset",
                    self.emotes_menu_items,
                    1,
                )

            if confirm_click or self._consume_api_call(server, "ok"):
                self._open_selected_emote()
            return None

        if self.active_screen == SCREEN_SETTINGS_MENU:
            if prev_click or self._consume_api_call(server, "up"):
                self._move_selection(
                    "settings_selected_index",
                    "settings_scroll_offset",
                    self.settings_menu_items,
                    -1,
                )

            if next_click or self._consume_api_call(server, "down"):
                self._move_selection(
                    "settings_selected_index",
                    "settings_scroll_offset",
                    self.settings_menu_items,
                    1,
                )

            if confirm_click or self._consume_api_call(server, "ok"):
                return self._select_setting_item()
            return None
        
        if self.active_screen == SCREEN_DEBUG_MENU:
            # Debug obrazovka nic nevybira. Jakykoliv vstup ji jen zavre.
            if (
                prev_click
                or next_click
                or confirm_click
                or self._consume_api_call(server, "up")
                or self._consume_api_call(server, "down")
                or self._consume_api_call(server, "ok")
            ):
                self._return_from_overlay_screen()
            return None

        if (
            next_click
            or prev_click
            or self._consume_api_call(server, "up")
            or self._consume_api_call(server, "down")
            or self._consume_api_call(server, "ok")
        ):
            self._return_from_overlay_screen()
        return None

    def set_setting_value(self, name, value):
        """Aktualizuje jednu zobrazovanou hodnotu nastaveni."""
        if self.setting_values.get(name) != value:
            self.setting_values[name] = value
            self.needs_render = True

    def set_clock_text(self, value):
        """Aktualizuje zobrazeny cas a prekresli UI jen pri zmene."""
        if self.clock_text != value:
            self.clock_text = value
            self.needs_render = True

    def set_debug_lines(self, lines):
        """Aktualizuje radky debug obrazovky a prekresli je jen pri zmene."""
        normalized_lines = [str(line) for line in lines]
        if self.debug_lines != normalized_lines:
            self.debug_lines = normalized_lines
            if self.active_screen == SCREEN_DEBUG_MENU:
                self.needs_render = True

    def get_line_height(self):
        """Vrati aktualni vysku radku OLED fontu."""
        return get_font_line_height()

    def get_char_width(self):
        """Vrati aktualni sirku znaku OLED fontu."""
        return get_font_char_width()

    def get_max_visible_list_rows(self):
        """Spocita pocet radku seznamu, ktere se vejdou pod nadpis."""
        total_rows = max(1, self.display.height // self.get_line_height())
        return max(1, total_rows - 1)

    def get_active_menu_emote(self):
        """Vrati emote otevreny v detailu nebo `None` mimo tuto obrazovku."""
        if self.active_screen == SCREEN_EMOTE_DETAIL:
            return self.selected_emote
        return None

    def get_http_menu_snapshot(self):
        """Vrati strukturovany stav aktualniho UI pro HTTP/JSON API."""
        visible_items = []
        selected_index = None
        scroll_offset = 0

        if self.active_screen == SCREEN_MAIN_MENU:
            visible_slice, scroll_offset = self.get_visible_items(
                self.main_menu_items,
                self.main_selected_index,
                self.main_scroll_offset,
            )
            selected_index = self.main_selected_index
            for offset_index, item in enumerate(visible_slice):
                index = scroll_offset + offset_index
                visible_items.append({
                    "index": index,
                    "label": item,
                    "selected": index == self.main_selected_index,
                })

        elif self.active_screen == SCREEN_EMOTES_MENU:
            visible_slice, scroll_offset = self.get_visible_items(
                self.emotes_menu_items,
                self.emotes_selected_index,
                self.emotes_scroll_offset,
            )
            selected_index = self.emotes_selected_index
            for offset_index, item in enumerate(visible_slice):
                index = scroll_offset + offset_index
                visible_items.append({
                    "index": index,
                    "label": item,
                    "selected": index == self.emotes_selected_index,
                })

        elif self.active_screen == SCREEN_SETTINGS_MENU:
            visible_slice, scroll_offset = self.get_visible_items(
                self.settings_menu_items,
                self.settings_selected_index,
                self.settings_scroll_offset,
            )
            selected_index = self.settings_selected_index
            for offset_index, item in enumerate(visible_slice):
                index = scroll_offset + offset_index
                entry = {
                    "index": index,
                    "label": item,
                    "selected": index == self.settings_selected_index,
                }
                if item != "Back":
                    entry["value"] = self.setting_values.get(item, False)
                    entry["display_value"] = self.format_setting_value(
                        item,
                        self.setting_values.get(item, False),
                    )
                visible_items.append(entry)

        elif self.active_screen == SCREEN_EMOTE_DETAIL:
            visible_items.append({
                "index": 0,
                "label": self.selected_emote,
                "selected": True,
            })

        elif self.active_screen == SCREEN_DEBUG_MENU:
            max_visible_rows = self.get_max_visible_list_rows()
            for index, line in enumerate(self.debug_lines[:max_visible_rows]):
                visible_items.append({
                    "index": index,
                    "label": line,
                    "selected": False,
                })

        return {
            "active_screen": self.active_screen,
            "main_selected_index": self.main_selected_index,
            "emotes_selected_index": self.emotes_selected_index,
            "settings_selected_index": self.settings_selected_index,
            "main_scroll_offset": self.main_scroll_offset,
            "emotes_scroll_offset": self.emotes_scroll_offset,
            "settings_scroll_offset": self.settings_scroll_offset,
            "selected_emote": self.selected_emote,
            "clock_text": self.clock_text,
            "selected_index": selected_index,
            "visible_items": visible_items,
            "scroll_offset": scroll_offset,
            "controls": ["up", "ok", "down", "back", "refresh"],
        }

    def get_follow_scroll_offset(self, selected_index, current_offset, item_count):
        """Spocita scroll tak, aby vybrany radek zustal ve viditelne casti."""
        max_visible_rows = self.get_max_visible_list_rows()
        # Kdyz se seznam vejde na obrazovku cely, scroll neni potreba.
        if item_count <= max_visible_rows:
            return 0

        if selected_index == 0:
            return 0

        if selected_index == item_count - 1:
            return max(0, item_count - max_visible_rows)

        if selected_index < current_offset:
            return selected_index

        if selected_index >= current_offset + max_visible_rows:
            return selected_index - max_visible_rows + 1

        return current_offset

    def get_visible_items(self, items, selected_index, scroll_offset):
        """Vrati aktualne viditelnou cast seznamu a jeji scroll offset."""
        max_visible_rows = self.get_max_visible_list_rows()
        if len(items) <= max_visible_rows:
            return items, 0

        scroll_offset = min(
            scroll_offset,
            max(0, len(items) - max_visible_rows),
        )
        visible_items = items[scroll_offset:scroll_offset + max_visible_rows]

        if selected_index < scroll_offset or selected_index >= scroll_offset + len(visible_items):
            scroll_offset = self.get_follow_scroll_offset(
                selected_index,
                scroll_offset,
                len(items),
            )
            visible_items = items[scroll_offset:scroll_offset + max_visible_rows]

        return visible_items, scroll_offset

    def render_ui(self):
        """Prekresli aktualni OLED obrazovku jen kdyz je to potreba."""
        # OLED se neprekresluje zbytecne v kazde iteraci, jen pri zmene stavu.
        if not self.needs_render and not self.should_animate_text_scroll():
            return

        if self.active_screen == SCREEN_MAIN_MENU:
            self.render_menu()
        elif self.active_screen == SCREEN_MAIN_SCREEN:
            self.render_main()
        elif self.active_screen == SCREEN_EMOTES_MENU:
            self.render_emotes()
        elif self.active_screen == SCREEN_EMOTE_DETAIL:
            self.render_emote_detail()
        elif self.active_screen == SCREEN_SETTINGS_MENU:
            self.render_settings()
        elif self.active_screen == SCREEN_DEBUG_MENU:
            self.render_debug()

        self.needs_render = False

    def should_animate_text_scroll(self):
        """Vrati `True`, kdyz je cas posunout dlouhe radky textu."""
        if not self.text_scroll_active:
            return False

        now = time.monotonic()
        if now - self.text_scroll_last_update < TEXT_SCROLL_INTERVAL:
            return False

        self.text_scroll_last_update = now
        self.text_scroll_tick += 1
        return True

    def render_menu(self):
        """Vykresli hlavni menu."""
        self.main_scroll_offset = self.render_selectable_list(
            title="Menu",
            items=self.main_menu_items,
            selected_index=self.main_selected_index,
            scroll_offset=self.main_scroll_offset,
        )

    def render_main(self):
        """Vykresli jednoduchou hlavni obrazovku."""
        self.render_screen_text("Main\nPREV/NEXT=BACK")

    def render_settings(self):
        """Vykresli menu nastaveni s aktualnimi hodnotami."""
        lines = ["Settings"]
        visible_items, self.settings_scroll_offset = self.get_visible_items(
            self.settings_menu_items,
            self.settings_selected_index,
            self.settings_scroll_offset,
        )

        for offset_index, item in enumerate(visible_items):
            index = self.settings_scroll_offset + offset_index
            prefix = ">" if index == self.settings_selected_index else " "
            # V menu nastaveni se u kazde polozky zobrazuje i aktualni stav.
            if item == "Back":
                lines.append(f"{prefix} {item}")
            else:
                value = self.format_setting_value(item, self.setting_values.get(item, False))
                lines.append(f"{prefix} {item}: {value}")

        self.render_screen_text("\n".join(lines))

    def format_setting_value(self, name, value):
        """Prevede interní hodnotu nastaveni na text pro OLED a web."""
        if name == "Brightness":
            return "{:.1f}".format(float(value))
        if name == "Font":
            return str(value)
        if name == "Fan":
            return "{}%".format(int(value))
        if name in (
            "Boop Calibrate",
            # "Wifi Main",
            # "Wifi Backup",
        ):
            return "RUN"
        return "ON" if bool(value) else "OFF"

    def render_emotes(self):
        """Vykresli seznam dostupnych emote."""
        self.emotes_scroll_offset = self.render_selectable_list(
            title="Emotes",
            items=self.emotes_menu_items,
            selected_index=self.emotes_selected_index,
            scroll_offset=self.emotes_scroll_offset,
        )

    def render_emote_detail(self):
        """Vykresli detail aktualne vybraneho emote."""
        self.render_screen_text(f"Emote:\n{self.selected_emote}\nPREV/NEXT=BACK")

    def render_debug(self):
        """Vykresli debug informace na OLED."""
        lines = ["Debug"]
        lines.extend(self.debug_lines[:self.get_max_visible_list_rows()])
        self.render_screen_text("\n".join(lines))

    def render_selectable_list(self, title, items, selected_index, scroll_offset=0):
        """Vykresli jednoduchy seznam se zvyraznenou vybranou polozkou."""
        lines = [title]
        visible_items, scroll_offset = self.get_visible_items(
            items,
            selected_index,
            scroll_offset,
        )

        for offset_index, item in enumerate(visible_items):
            index = scroll_offset + offset_index
            prefix = ">" if index == selected_index else " "
            lines.append(f"{prefix} {item}")

        self.render_screen_text("\n".join(lines))
        return scroll_offset

    def render_screen_text(self, text):
        """Vykresli textovou OLED obrazovku s hodinami vpravo nahore."""
        blocks = []
        lines = str(text).split("\n")
        has_scroll = False
        scroll_key = (
            self.active_screen,
            tuple(lines),
            self.get_char_width(),
            self.get_line_height(),
            self.clock_text,
        )
        if scroll_key != self.text_scroll_key:
            self.text_scroll_key = scroll_key
            self.text_scroll_tick = 0
            self.text_scroll_last_update = time.monotonic()

        # Prvni radek ma uzsi oblast, aby se neprekryl s hodinami vpravo.
        line_height = self.get_line_height()
        for index, line in enumerate(lines):
            if index == 0:
                max_width = self.get_clock_x() - CLOCK_PADDING
            else:
                max_width = self.display.width

            text_width = len(str(line)) * self.get_char_width()
            offset = self.get_text_scroll_offset(text_width, max_width)
            has_scroll = has_scroll or text_width > max_width
            blocks.append({
                "text": line,
                "x": -offset,
                "y": index * line_height,
                "wrap": False,
                "max_width": text_width,
                "clip_x_min": 0,
                "clip_x_max": max_width,
            })

        blocks.append({
            "text": self.clock_text,
            "x": self.get_clock_x(),
            "y": CLOCK_Y,
            "wrap": False,
        })
        self.text_scroll_active = has_scroll
        if not has_scroll:
            self.text_scroll_tick = 0
        self.display.show_text_blocks(blocks, clear=True)

    def get_text_scroll_offset(self, text_width, max_width):
        """Spocita vodorovny ping-pong posun pro dlouhy radek."""
        overflow = text_width - max_width
        if overflow <= 0:
            return 0

        span = overflow + TEXT_SCROLL_HOLD_TICKS
        phase = int(self.text_scroll_tick * TEXT_SCROLL_SPEED_MULTIPLIER) % (span * 2)
        if phase >= span:
            phase = (span * 2) - phase - 1
        return min(overflow, phase)

    def get_clock_x(self):
        """Vrati x souradnici pro zarovnani hodin doprava."""
        return self.display.width - (len(self.clock_text) * self.get_char_width())

    def fit_first_line(self, text):
        """Zkrati prvni radek tak, aby nelezl do oblasti hodin."""
        max_width = self.get_clock_x() - CLOCK_PADDING
        max_chars = max(0, max_width // self.get_char_width())
        return str(text)[:max_chars]

    def fit_display_line(self, text):
        """Zkrati radek tak, aby se pri velkem fontu nezalomil pres dalsi radek."""
        max_chars = max(1, self.display.width // self.get_char_width())
        return str(text)[:max_chars]

    def go_back(self):
        """Vrati se o jednu uroven vys v hierarchii menu."""
        if self.active_screen in (
            SCREEN_EMOTES_MENU,
            SCREEN_SETTINGS_MENU,
            SCREEN_DEBUG_MENU,
            SCREEN_MAIN_SCREEN,
        ):
            self.active_screen = SCREEN_MAIN_MENU
        elif self.active_screen == SCREEN_EMOTE_DETAIL:
            self.active_screen = SCREEN_EMOTES_MENU
        else:
            self.active_screen = SCREEN_MAIN_MENU
        self.needs_render = True
