"""OLED menu state machine and rendering helpers for the device UI."""

from I2C_sim import OLEDDisplay

SCREEN_MAIN_MENU = "main_menu"
SCREEN_MAIN_SCREEN = "main_screen"
SCREEN_EMOTES_MENU = "emotes_menu"
SCREEN_EMOTE_DETAIL = "emote_detail"
SCREEN_SETTINGS_MENU = "settings_menu"
CLOCK_Y = 0
LINE_HEIGHT = 8
CHAR_WIDTH = 6
CLOCK_PADDING = 2
MAX_VISIBLE_LIST_ROWS = 6

EVENT_SETTING_SELECTED = "setting_selected"


class UI():
    """Manage OLED navigation state and emit selection events."""

    def __init__(self, display:OLEDDisplay):
        """Initialize menu structure, selection state and render flags."""
        self.display = display
        self.main_menu_items = ["Emotes", "Settings", "Debug"]
        self.emotes_menu_items = ["gif", "clock", "cross", "open eye", "Back", "test1", "test2", "test3", "test4", "test5"]
        self.settings_menu_items = ["Boop", "Mic", "Accelerometer","Wifi", "Verbose", "Back"]
        self.setting_values = {
            "Boop": False,
            "Wifi": False,
            "Accelerometer": False,
            "Verbose": False,
            "Mic":False
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

    def handle_input(self, confirm_click, next_click):
        """Update menu state from button clicks and return optional events."""
        if self.active_screen == SCREEN_MAIN_MENU:
            if next_click:
                self.main_selected_index = (
                    self.main_selected_index + 1
                ) % len(self.main_menu_items)
                self.main_scroll_offset = self.get_follow_scroll_offset(
                    self.main_selected_index,
                    self.main_scroll_offset,
                    len(self.main_menu_items),
                )
                self.needs_render = True

            if confirm_click:
                selected_item = self.main_menu_items[self.main_selected_index]
                if selected_item == "Emotes":
                    self.active_screen = SCREEN_EMOTES_MENU
                elif selected_item == "Settings":
                    self.active_screen = SCREEN_SETTINGS_MENU
                else:
                    self.active_screen = SCREEN_MAIN_SCREEN
                self.needs_render = True
            return None

        if self.active_screen == SCREEN_EMOTES_MENU:
            if next_click:
                self.emotes_selected_index = (
                    self.emotes_selected_index + 1
                ) % len(self.emotes_menu_items)
                self.emotes_scroll_offset = self.get_follow_scroll_offset(
                    self.emotes_selected_index,
                    self.emotes_scroll_offset,
                    len(self.emotes_menu_items),
                )
                self.needs_render = True

            if confirm_click:
                selected_item = self.emotes_menu_items[self.emotes_selected_index]
                if selected_item == "Back":
                    self.active_screen = SCREEN_MAIN_MENU
                else:
                    self.selected_emote = selected_item
                    self.active_screen = SCREEN_EMOTE_DETAIL
                    self.needs_render = True
                self.needs_render = True
            return None

        if self.active_screen == SCREEN_SETTINGS_MENU:
            if next_click:
                self.settings_selected_index = (
                    self.settings_selected_index + 1
                ) % len(self.settings_menu_items)
                self.settings_scroll_offset = self.get_follow_scroll_offset(
                    self.settings_selected_index,
                    self.settings_scroll_offset,
                    len(self.settings_menu_items),
                )
                self.needs_render = True

            if confirm_click:
                selected_item = self.settings_menu_items[self.settings_selected_index]
                if selected_item == "Back":
                    self.active_screen = SCREEN_MAIN_MENU
                else:
                    self.needs_render = True
                    return EVENT_SETTING_SELECTED, selected_item
                self.needs_render = True
            return None

        if next_click:
            if self.active_screen == SCREEN_MAIN_SCREEN:
                self.active_screen = SCREEN_MAIN_MENU
            elif self.active_screen == SCREEN_EMOTE_DETAIL:
                self.active_screen = SCREEN_EMOTES_MENU
            self.needs_render = True
        return None

    def set_setting_value(self, name, value):
        """Update one rendered setting value and request a redraw if changed."""
        if self.setting_values.get(name) != value:
            self.setting_values[name] = value
            self.needs_render = True

    def set_clock_text(self, value):
        """Update the rendered clock value and redraw only when it changes."""
        if self.clock_text != value:
            self.clock_text = value
            self.needs_render = True

    def get_active_menu_emote(self):
        """Return the currently opened emote detail or None outside that screen."""
        if self.active_screen == SCREEN_EMOTE_DETAIL:
            return self.selected_emote
        return None

    def get_follow_scroll_offset(self, selected_index, current_offset, item_count):
        """Keep the selected row inside the visible list window."""
        if item_count <= MAX_VISIBLE_LIST_ROWS:
            return 0

        if selected_index == 0:
            return 0

        if selected_index == item_count - 1:
            return max(0, item_count - MAX_VISIBLE_LIST_ROWS)

        if selected_index < current_offset:
            return selected_index

        if selected_index >= current_offset + MAX_VISIBLE_LIST_ROWS:
            return selected_index - MAX_VISIBLE_LIST_ROWS + 1

        return current_offset

    def get_visible_items(self, items, selected_index, scroll_offset):
        """Return the current visible list window and its effective offset."""
        if len(items) <= MAX_VISIBLE_LIST_ROWS:
            return items, 0

        scroll_offset = min(
            scroll_offset,
            max(0, len(items) - MAX_VISIBLE_LIST_ROWS),
        )
        visible_items = items[scroll_offset:scroll_offset + MAX_VISIBLE_LIST_ROWS]

        if selected_index < scroll_offset or selected_index >= scroll_offset + len(visible_items):
            scroll_offset = self.get_follow_scroll_offset(
                selected_index,
                scroll_offset,
                len(items),
            )
            visible_items = items[scroll_offset:scroll_offset + MAX_VISIBLE_LIST_ROWS]

        return visible_items, scroll_offset

    def render_ui(self):
        """Render the current menu or selected screen onto the OLED."""
        if not self.needs_render:
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

        self.needs_render = False

    def render_menu(self):
        """Render the top-level navigation menu."""
        self.main_scroll_offset = self.render_selectable_list(
            title="Menu",
            items=self.main_menu_items,
            selected_index=self.main_selected_index,
            scroll_offset=self.main_scroll_offset,
        )

    def render_main(self):
        """Render the placeholder main screen content."""
        self.render_screen_text("Main\nDOWN=BACK")

    def render_settings(self):
        """Render the settings submenu."""
        lines = ["Settings"]
        visible_items, self.settings_scroll_offset = self.get_visible_items(
            self.settings_menu_items,
            self.settings_selected_index,
            self.settings_scroll_offset,
        )

        for offset_index, item in enumerate(visible_items):
            index = self.settings_scroll_offset + offset_index
            prefix = ">" if index == self.settings_selected_index else " "
            if item == "Back":
                lines.append(f"{prefix} {item}")
            else:
                value = "ON" if self.setting_values.get(item, False) else "OFF"
                lines.append(f"{prefix} {item}: {value}")

        self.render_screen_text("\n".join(lines))

    def render_emotes(self):
        """Render the emotes submenu."""
        self.emotes_scroll_offset = self.render_selectable_list(
            title="Emotes",
            items=self.emotes_menu_items,
            selected_index=self.emotes_selected_index,
            scroll_offset=self.emotes_scroll_offset,
        )

    def render_emote_detail(self):
        """Render the currently selected emote detail screen."""
        self.render_screen_text(f"Emote:\n{self.selected_emote}\nDOWN=BACK")

    def render_selectable_list(self, title, items, selected_index, scroll_offset=0):
        """Render a simple selectable list with the current cursor highlighted."""
        lines = [title]
        visible_items, scroll_offset = self.get_visible_items(
            items,
            selected_index,
            scroll_offset,
        )

        for offset_index, item in enumerate(visible_items):
            index = scroll_offset + offset_index
            prefix = "-" if index == selected_index else " "
            lines.append(f"{prefix} {item}")

        self.render_screen_text("\n".join(lines))
        return scroll_offset

    def render_screen_text(self, text):
        """Render one OLED screen with a top-right clock and body content."""
        blocks = []
        lines = str(text).split("\n")

        for index, line in enumerate(lines):
            if index == 0:
                line = self.fit_first_line(line)
            blocks.append({"text": line, "x": 0, "y": index * LINE_HEIGHT})

        blocks.append({"text": self.clock_text, "x": self.get_clock_x(), "y": CLOCK_Y})
        self.display.show_text_blocks(blocks, clear=True)

    def get_clock_x(self):
        """Return the x coordinate needed to right-align the current clock text."""
        return self.display.width - (len(self.clock_text) * CHAR_WIDTH)

    def fit_first_line(self, text):
        """Trim the first row so it does not overlap the clock area."""
        max_width = self.get_clock_x() - CLOCK_PADDING
        max_chars = max(0, max_width // CHAR_WIDTH)
        return str(text)[:max_chars]
