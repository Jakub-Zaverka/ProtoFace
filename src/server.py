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
        self.performance_provider = None
        self.time_handler = None
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

        @self.server.route("/api/perf")
        def api_perf(request: Request):
            return Response(request, self.serialize_performance(), content_type="application/json")

        @self.server.route("/api/time")
        def api_time(request: Request):
            return Response(request, self.handle_time_sync(request), content_type="application/json")
        
        # Poslech probiha primo na lokalni IP adrese zarizeni.
        self.server.start(str(self.wifi.server_ip_address()), 80)

    def poll(self):
        """Obslouzi jednu iteraci HTTP serveru bez blokovani hlavni smycky."""
        self.server.poll()

    def set_menu_snapshot(self, snapshot):
        """Ulozi posledni stav OLED menu pro HTTP endpoint."""
        self.menu_snapshot = snapshot

    def set_menu_action_handler(self, handler):
        """Zaregistruje callback, ktery umi hned zpracovat HTTP akci v UI."""
        self.menu_action_handler = handler

    def set_performance_provider(self, provider):
        """Zaregistruje callback vracejici posledni runtime metriky."""
        self.performance_provider = provider

    def set_time_handler(self, handler):
        """Zaregistruje callback pro nastaveni RTC z weboveho prohlizece."""
        self.time_handler = handler

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

    def serialize_performance(self):
        """Vrati posledni namerene runtime metriky jako JSON."""
        if self.performance_provider is None:
            return json.dumps({
                "ok": False,
                "error": "performance_unavailable",
            })

        payload = dict(self.performance_provider())
        payload["ok"] = True
        return json.dumps(payload)

    def handle_time_sync(self, request):
        """Prevezme lokalni cas z browseru a preda ho runtime hodinam."""
        if self.time_handler is None:
            return json.dumps({
                "ok": False,
                "error": "time_handler_unavailable",
            })

        try:
            values = self._read_query_values(
                request,
                ("year", "month", "day", "hour", "minute", "second"),
            )
            result = self.time_handler(
                int(values["year"]),
                int(values["month"]),
                int(values["day"]),
                int(values["hour"]),
                int(values["minute"]),
                int(values["second"]),
            )
        except Exception as error:
            return json.dumps({
                "ok": False,
                "error": str(error),
            })

        return json.dumps({
            "ok": True,
            "clock_text": "{:02}:{:02}".format(result.tm_hour, result.tm_min),
        })

    def _read_query_values(self, request, names):
        """Vytahne query parametry z Request objektu napric verzemi knihovny."""
        params = getattr(request, "query_params", None)
        if params is not None:
            return {name: params[name] for name in names}

        path = getattr(request, "path", "")
        raw_request = getattr(request, "raw_request", "")
        source = path or raw_request
        if " " in source:
            parts = source.split(" ")
            if len(parts) > 1:
                source = parts[1]

        query = ""
        if "?" in source:
            query = source.split("?", 1)[1]

        parsed = {}
        for part in query.split("&"):
            if not part or "=" not in part:
                continue
            key, value = part.split("=", 1)
            parsed[key] = value

        return {name: parsed[name] for name in names}

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
