"""Program vystavuje jednoduche HTTP endpointy pro dalkove ovladani menu."""

# Server neprovadi slozitou logiku. Jen preklada HTTP requesty na jednoduche prikazy pro UI.
import json

from adafruit_httpserver import Request, Response, Server


class ServerClass:
    """Prijima HTTP prikazy a uklada posledni akci pro zpracovani v UI."""
    def __init__(self, wifi):
        if wifi is None:
            raise ValueError("wifi must not be None")

        self.wifi = wifi
        self.api_call = ""
        self.menu_snapshot = None
        self.menu_action_handler = None
        if self.wifi.pool is None:
            raise RuntimeError("wifi must be connected before starting the server")

        # Server bezi nad uz vytvorenym socket poolem z Wi-Fi vrstvy.
        pool = self.wifi.pool
        self.server = Server(pool, "/static", debug=True)

        # Kazdy endpoint jen ulozi pozadovanou akci, kterou si pak vyzvedne UI.
        @self.server.route("/")
        def base(request: Request):
            return Response(request, self.get_index_html(), content_type="text/html")
        
        @self.server.route("/up")
        def up(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.handle_menu_action("up")), content_type="application/json")
        
        @self.server.route("/down")
        def down(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.handle_menu_action("down")), content_type="application/json")
        
        @self.server.route("/ok")
        def ok(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.handle_menu_action("ok")), content_type="application/json")

        @self.server.route("/menu")
        def menu(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.menu_snapshot), content_type="application/json")

        @self.server.route("/api/menu")
        def api_menu(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.menu_snapshot), content_type="application/json")

        @self.server.route("/api/action/up")
        def api_up(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.handle_menu_action("up")), content_type="application/json")

        @self.server.route("/api/action/down")
        def api_down(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.handle_menu_action("down")), content_type="application/json")

        @self.server.route("/api/action/ok")
        def api_ok(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.handle_menu_action("ok")), content_type="application/json")

        @self.server.route("/api/action/back")
        def api_back(request: Request):
            return Response(request, self.serialize_menu_snapshot(self.handle_menu_action("back")), content_type="application/json")
        
        # Poslech probiha primo na lokalni IP adrese zarizeni.
        self.server.start(str(self.wifi.radio.ipv4_address), 80)

    def poll(self):
        """Obslouzi jednu iteraci HTTP serveru bez blokovani hlavni smycky."""
        self.server.poll()

    def set_menu_snapshot(self, snapshot):
        """Ulozi posledni stav OLED menu pro HTTP endpoint."""
        self.menu_snapshot = snapshot

    def set_menu_action_handler(self, handler):
        """Zaregistruje callback, ktery umi hned zpracovat HTTP akci v UI."""
        self.menu_action_handler = handler

    def handle_menu_action(self, action):
        """Zpracuje HTTP akci a vrati uz aktualizovany snapshot menu."""
        if self.menu_action_handler is not None:
            return self.menu_action_handler(action)

        self.api_call = action
        return self.menu_snapshot

    def serialize_menu_snapshot(self, snapshot):
        """Vrati snapshot menu jako JSON string vhodny pro HTTP response."""
        payload = snapshot
        if payload is None:
            payload = {
                "ok": False,
                "error": "menu_snapshot_unavailable",
            }
        else:
            payload = dict(payload)
            payload["ok"] = True

        return json.dumps(payload)

    def get_index_html(self):
        """Nacte jednoduchou ovladaci webovou stranku pro menu."""
        try:
            with open("/static/index.html", "r", encoding="utf-8") as file_handle:
                return file_handle.read()
        except OSError:
            return (
                "<!doctype html><html><body><h1>Menu UI unavailable</h1>"
                "<p>Missing /static/index.html</p></body></html>"
            )
