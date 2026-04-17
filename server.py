from adafruit_httpserver import Request, Response, Server


class ServerClass:
    def __init__(self, wifi):
        if wifi is None:
            raise ValueError("wifi must not be None")

        self.wifi = wifi
        if self.wifi.pool is None:
            raise RuntimeError("wifi must be connected before starting the server")

        pool = self.wifi.pool
        self.server = Server(pool, "/static", debug=True)

        @self.server.route("/")
        def base(request: Request):
            return Response(request, "Hello from the CircuitPython HTTP Server!")

        self.server.start(str(self.wifi.radio.ipv4_address), 80)

    def poll(self):
        self.server.poll()
