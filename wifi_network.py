"""Simple Wi-Fi connection helper for the device runtime."""

import os

import socketpool
import wifi


class Wifi:
    """Store Wi-Fi credentials and open a shared socket pool."""

    def __init__(self, ssid=os.getenv("HOME_WIFI_SSID"), passw=os.getenv("HOME_WIFI_PASSWORD")):
        """Load Wi-Fi credentials from arguments or environment variables."""
        self.wifi_ssid = ssid
        self.wifi_password = passw
        self.pool = None
        if self.wifi_ssid is None:
            self.wifi_ssid = ""
            self.wifi_password = ""
            raise ValueError("SSID not found in environment variables")

    def connect(self):
        """Connect the radio and create a socket pool for network clients."""
        try:
            wifi.radio.connect(self.wifi_ssid, self.wifi_password)
        except ConnectionError:
            print("Failed to connect to WiFi with provided credentials")
            raise
        self.pool = socketpool.SocketPool(wifi.radio)
