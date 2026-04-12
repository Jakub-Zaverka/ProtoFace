import os

import socketpool
import wifi

import adafruit_ntp



class Wifi:
    def __init__(self, ssid = os.getenv("HOME_WIFI_SSID"), passw = os.getenv("HOME_WIFI_PASSWORD") ):
        self.wifi_ssid = ssid
        self.wifi_password = passw
        if self.wifi_ssid is None:
            self.wifi_ssid = ""
            self.wifi_password = ""
            raise ValueError("SSID not found in environment variables")
    
    def connect(self):
        try:
            wifi.radio.connect(self.wifi_ssid, self.wifi_password)
        except ConnectionError:
            print("Failed to connect to WiFi with provided credentials")
            raise
        self.pool = socketpool.SocketPool(wifi.radio)
    
    def get_time_ntp(self):
        self.ntp = adafruit_ntp.NTP(self.pool,server="tak.cesnet.cz", tz_offset=0, cache_seconds=3600)
        print(self.ntp.datetime)
