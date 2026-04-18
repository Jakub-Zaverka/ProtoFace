"""Program vystavuje jednoduche HTTP endpointy pro dalkove ovladani menu."""

# Server neprovadi slozitou logiku. Jen preklada HTTP requesty na jednoduche prikazy pro UI.
from adafruit_httpserver import Request, Response, Server


class ServerClass:
    """Prijima HTTP prikazy a uklada posledni akci pro zpracovani v UI."""
    def __init__(self, wifi):
        if wifi is None:
            raise ValueError("wifi must not be None")

        self.wifi = wifi
        self.api_call = ""
        if self.wifi.pool is None:
            raise RuntimeError("wifi must be connected before starting the server")

        # Server bezi nad uz vytvorenym socket poolem z Wi-Fi vrstvy.
        pool = self.wifi.pool
        self.server = Server(pool, "/static", debug=True)

        # Kazdy endpoint jen ulozi pozadovanou akci, kterou si pak vyzvedne UI.
        @self.server.route("/")
        def base(request: Request):
            return Response(request, "Hello from the CircuitPython HTTP Server!")
        
        @self.server.route("/up")
        def up(request: Request):
            self.api_call="up"
            return Response(request, "Up")
        
        @self.server.route("/down")
        def down(request: Request):
            self.api_call="down"
            return Response(request, "Down")
        
        @self.server.route("/ok")
        def ok(request: Request):
            self.api_call="ok"
            return Response(request, "Ok")
        
        # Poslech probiha primo na lokalni IP adrese zarizeni.
        self.server.start(str(self.wifi.radio.ipv4_address), 80)

    def poll(self):
        """Obslouzi jednu iteraci HTTP serveru bez blokovani hlavni smycky."""
        self.server.poll()
