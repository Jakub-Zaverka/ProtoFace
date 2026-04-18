"""Program pripojuje zarizeni k Wi-Fi, nastavuje hostname a pripravuje mDNS."""

# Sitova vrstva drzi credentials, pripojeni i sdileny socket pool pro dalsi moduly.
import os

import mdns
import socketpool
import wifi


class Wifi:
    """Drzi Wi-Fi konfiguraci a otevira sdileny socket pool pro sitove sluzby."""

    def __init__(
        self,
        ssid=None,
        passw=None,
        backup_ssid=None,
        backup_passw=None,
        hostname=None,
    ):
        """Nacte credentials z argumentu nebo z `settings.toml`."""
        # Pri beznem behu se hodnoty berou z `settings.toml`, ale jde je predat i rucne.
        self.wifi_ssid = ssid if ssid is not None else os.getenv("HOME_WIFI_SSID")
        self.wifi_password = (
            passw if passw is not None else os.getenv("HOME_WIFI_PASSWORD")
        )
        self.backup_wifi = (
            backup_ssid if backup_ssid is not None else os.getenv("BACKUP_WIFI_SSID")
        )
        self.backup_wifi_passw = (
            backup_passw
            if backup_passw is not None
            else os.getenv("BACKUP_WIFI_PASSWORD")
        )
        self.hostname = hostname if hostname is not None else os.getenv("DEVICE_HOSTNAME")
        if not self.hostname:
            self.hostname = "protogen"
        self.radio = wifi.radio
        self.pool = None
        self.mdns_server = None
        if self.wifi_ssid is None:
            self.wifi_ssid = ""
            self.wifi_password = ""
            raise ValueError("SSID not found in environment variables")

    def connect(self):
        """Pripoji radio k siti a vytvori socket pool pro klienty a server."""
        self.radio.hostname = self.hostname
        try:
            self.radio.connect(self.wifi_ssid, self.wifi_password)
        except ConnectionError:
            # Kdyz selze hlavni sit, zkus zalozni credentials.
            print("Failed to connect to main WiFi with provided credentials")
            try:
                self.radio.connect(self.backup_wifi, self.backup_wifi_passw)
            except:
                print("Failed to connect to backup WiFi with provided credentials")
                raise

        # Po uspesnem pripojeni se pripravi mDNS i socket pool pro HTTP server a NTP.
        self.mdns_server = mdns.Server(self.radio)
        self.mdns_server.hostname = self.hostname
        self.mdns_server.instance_name = self.hostname
        self.pool = socketpool.SocketPool(self.radio)

    def advertise_http(self, port):
        """Zainzeruje HTTP sluzbu pres mDNS."""
        if self.mdns_server is None:
            raise RuntimeError("Connect Wi-Fi before advertising services")
        self.mdns_server.advertise_service(
            service_type="_http",
            protocol="_tcp",
            port=port,
        )

    def base_url(self, port):
        """Vrati preferovanou lokalni URL s mDNS hostname."""
        return "http://{}.local:{}".format(self.hostname, port)

    def ip_url(self, port):
        """Vrati primou lokalni URL s IP adresou zarizeni."""
        return "http://{}:{}".format(self.radio.ipv4_address, port)
