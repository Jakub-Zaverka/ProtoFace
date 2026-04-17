from adafruit_httpserver import Request, Response, Server


class ServerClass:
    def __init__(self, wifi):
        if wifi is None:
            raise ValueError("wifi must not be None")

        self.wifi = wifi
        self.api_call = ""
        if self.wifi.pool is None:
            raise RuntimeError("wifi must be connected before starting the server")

        pool = self.wifi.pool
        self.server = Server(pool, "/static", debug=True)

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
        


        self.server.start(str(self.wifi.radio.ipv4_address), 80)

    def poll(self):
        self.server.poll()
