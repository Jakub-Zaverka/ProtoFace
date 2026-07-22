"""Program nastavuje Wi-Fi klienta/AP, hostname a sitove sluzby."""

# Sitova vrstva drzi credentials, pripojeni i sdileny socket pool pro dalsi moduly.
import os

import mdns
import socketpool
import wifi

DEFAULT_FALLBACK_CHANNEL = 1
DEFAULT_AP_SSID = "Alan_Protogen-"
DEFAULT_AP_CHANNEL = 1


class Wifi:
    """Drzi Wi-Fi konfiguraci a otevira sdileny socket pool pro sitove sluzby."""

    def __init__(
        self,
        ssid=None,
        passw=None,
        backup_ssid=None,
        backup_passw=None,
        ap_ssid=None,
        ap_passw=None,
        ap_channel=DEFAULT_AP_CHANNEL,
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
        self.ap_ssid = ap_ssid if ap_ssid is not None else os.getenv("AP_SSID")
        self.ap_password = (
            ap_passw if ap_passw is not None else os.getenv("AP_PASSWORD")
        )
        self.ap_channel = ap_channel
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
        if not self.ap_ssid:
            self.ap_ssid = DEFAULT_AP_SSID
        if self.ap_password is None:
            self.ap_password = ""

    def connect(self, profile="auto"):
        """Zpetna kompatibilita: vychozi runtime pouziva broadcast AP."""
        return self.Wifi_Broadcast()

    def Wifi_Connect(self, profile="auto"):
        """Pripoji radio k existujici Wi-Fi siti a vytvori socket pool."""
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

    def Wifi_Broadcast(self):
        """Broadcastuje vlastni AP misto pripojeni k existujici Wi-Fi siti."""
        self.radio.hostname = self.hostname
        self.pool = None
        self.mdns_server = None
        self.connected_profile = "broadcast"
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
                self.ap_ssid,
                self.ap_password,
                channel=self.ap_channel,
                max_connections=4,
            )
            self.pool = socketpool.SocketPool(self.radio)
            self.current_channel = self.ap_channel
            print(
                "WiFi_Broadcast AP started: {} channel {}".format(
                    self.ap_ssid,
                    self.ap_channel,
                )
            )
            return True
        except Exception as error:
            print("Failed to start WiFi_Broadcast AP: {}".format(error))
            self.pool = None
            self.connected_profile = None
            self.set_fallback_channel()
            return False

    def disconnect(self):
        """Odpoji Wi-Fi sluzbu, ale ponecha radio na fallback kanalu pro ESP-NOW."""
        self.pool = None
        self.mdns_server = None
        self.connected_profile = None
        try:
            if self.radio.connected:
                self.radio.stop_station()
        except Exception as error:
            print("Failed to stop WiFi station: {}".format(error))
        try:
            if self.radio.ap_active:
                self.radio.stop_ap()
        except Exception as error:
            print("Failed to stop WiFi AP: {}".format(error))
        self.set_fallback_channel()

    def is_connected(self):
        """Vrati `True`, kdyz Wi-Fi radio aktivne poskytuje sitovou sluzbu."""
        return self.is_active()

    def is_station_connected(self):
        """Vrati `True`, kdyz je radio pripojene jako klient k Wi-Fi AP."""
        try:
            return self.radio.connected
        except Exception:
            return False

    def is_active(self):
        """Vrati `True`, kdyz bezi klient nebo vlastni AP."""
        try:
            return self.pool is not None and (
                self.radio.connected or self.radio.ap_active
            )
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
            return False
        self.mdns_server.advertise_service(
            service_type="_http",
            protocol="_tcp",
            port=port,
        )
        return True

    def base_url(self, port):
        """Vrati preferovanou lokalni URL s mDNS hostname."""
        return "http://{}.local:{}".format(self.hostname, port)

    def ip_url(self, port):
        """Vrati primou lokalni URL s IP adresou zarizeni."""
        return "http://{}:{}".format(self.server_ip_address(), port)

    def server_ip_address(self):
        """Vrati IP adresu, na ktere ma poslouchat HTTP server."""
        try:
            if self.radio.ap_active:
                return self.radio.ipv4_address_ap
        except Exception:
            pass
        return self.radio.ipv4_address
