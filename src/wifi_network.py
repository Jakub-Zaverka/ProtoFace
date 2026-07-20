"""Program pripojuje zarizeni k Wi-Fi, nastavuje hostname a pripravuje mDNS."""

# Sitova vrstva drzi credentials, pripojeni i sdileny socket pool pro dalsi moduly.
import os

import mdns
import socketpool
import wifi

DEFAULT_FALLBACK_CHANNEL = 1


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
        self.connected_profile = None
        self.current_channel = None
        if self.wifi_ssid is None:
            self.wifi_ssid = ""
            self.wifi_password = ""
        if self.backup_wifi is None:
            self.backup_wifi = ""
            self.backup_wifi_passw = ""

    def connect(self, profile="auto"):
        """Pripoji radio k siti a vytvori socket pool pro klienty a server."""
        self.radio.hostname = self.hostname
        self.pool = None
        self.mdns_server = None
        self.connected_profile = None
        try:
            if self.radio.ap_active:
                self.radio.stop_ap()
        except Exception:
            pass

        for name, ssid, password in self._get_profiles(profile):
            if not ssid:
                print("WiFi {} SSID is not configured".format(name))
                continue

            channel = self.find_network_channel(ssid)
            if channel is None:
                print("WiFi {} network not found: {}".format(name, ssid))
                continue

            try:
                if self.radio.ap_active:
                    self.radio.stop_ap()
                self.radio.connect(ssid, password, channel=channel)
            except Exception as error:
                print("Failed to connect to {} WiFi: {}".format(name, error))
                continue

            try:
                # Po uspesnem pripojeni se pripravi mDNS i socket pool pro HTTP server a NTP.
                self.mdns_server = mdns.Server(self.radio)
                self.mdns_server.hostname = self.hostname
                self.mdns_server.instance_name = self.hostname
                self.pool = socketpool.SocketPool(self.radio)
                self.connected_profile = name
                self.current_channel = channel
                return True
            except Exception as error:
                print("Failed to prepare {} WiFi services: {}".format(name, error))
                self.pool = None
                self.mdns_server = None
                self.connected_profile = None
                continue

        self.set_fallback_channel()
        return False

    def disconnect(self):
        """Odpoji Wi-Fi klienta, ale ponecha radio na fallback kanalu pro ESP-NOW."""
        self.pool = None
        self.mdns_server = None
        self.connected_profile = None
        try:
            if self.radio.connected:
                self.radio.stop_station()
        except Exception as error:
            print("Failed to stop WiFi station: {}".format(error))
        self.set_fallback_channel()

    def is_connected(self):
        """Vrati `True`, kdyz je radio pripojene k Wi-Fi AP."""
        try:
            return self.radio.connected
        except Exception:
            return False

    def find_network_channel(self, ssid):
        """Najde kanal site podle SSID nebo vrati `None`."""
        networks = None
        try:
            networks = self.radio.start_scanning_networks()
            for network in networks:
                if network.ssid == ssid:
                    return network.channel
        except Exception as error:
            print("Failed to scan WiFi networks: {}".format(error))
        finally:
            try:
                self.radio.stop_scanning_networks()
            except Exception:
                pass
        return None

    def set_fallback_channel(self, channel=DEFAULT_FALLBACK_CHANNEL):
        """Nastavi radio na znamy kanal, kdyz neni dostupna zadna Wi-Fi sit."""
        self.current_channel = channel
        try:
            if self.radio.connected:
                self.radio.stop_station()
        except Exception:
            pass

        try:
            if self.radio.ap_active:
                self.radio.stop_ap()
        except Exception:
            pass

        try:
            self.radio.start_ap(
                "{}-fallback".format(self.hostname),
                "",
                channel=channel,
                max_connections=1,
            )
            print("WiFi fallback channel set to {}".format(channel))
            return True
        except Exception as error:
            print("Failed to set WiFi fallback channel {}: {}".format(channel, error))
            return False

    def _get_profiles(self, profile):
        """Vrati seznam Wi-Fi profilu pro pokus o pripojeni."""
        profiles = {
            "main": (("main", self.wifi_ssid, self.wifi_password),),
            "backup": (("backup", self.backup_wifi, self.backup_wifi_passw),),
            "auto": (
                ("main", self.wifi_ssid, self.wifi_password),
                ("backup", self.backup_wifi, self.backup_wifi_passw),
            ),
        }
        return profiles.get(profile, profiles["auto"])

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
