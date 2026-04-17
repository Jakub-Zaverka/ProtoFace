"""Simple Wi-Fi connection helper for the device runtime."""

import os

import mdns
import socketpool
import wifi


class Wifi:
    """Store Wi-Fi credentials and open a shared socket pool."""

    def __init__(
        self,
        ssid=None,
        passw=None,
        backup_ssid=None,
        backup_passw=None,
        hostname=None,
    ):
        """Load Wi-Fi credentials from arguments or environment variables."""
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
        """Connect the radio and create a socket pool for network clients."""
        self.radio.hostname = self.hostname
        try:
            self.radio.connect(self.wifi_ssid, self.wifi_password)
        except ConnectionError:
            print("Failed to connect to main WiFi with provided credentials")
            try:
                self.radio.connect(self.backup_wifi, self.backup_wifi_passw)
            except:
                print("Failed to connect to backup WiFi with provided credentials")
                raise

        self.mdns_server = mdns.Server(self.radio)
        self.mdns_server.hostname = self.hostname
        self.mdns_server.instance_name = self.hostname
        self.pool = socketpool.SocketPool(self.radio)

    def advertise_http(self, port):
        """Advertise a future HTTP interface over mDNS."""
        if self.mdns_server is None:
            raise RuntimeError("Connect Wi-Fi before advertising services")
        self.mdns_server.advertise_service(
            service_type="_http",
            protocol="_tcp",
            port=port,
        )

    def base_url(self, port):
        """Return the preferred local URL for the device."""
        return "http://{}.local:{}".format(self.hostname, port)

    def ip_url(self, port):
        """Return the direct local IP URL for the device."""
        return "http://{}:{}".format(self.radio.ipv4_address, port)
