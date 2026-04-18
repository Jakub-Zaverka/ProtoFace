"""Program synchronizuje RTC pres NTP a vraci cas pro OLED i RGB hodiny."""

# Hodiny pracuji i bez site, ale pri dostupne Wi-Fi se pokusi o NTP synchronizaci.
import time
import rtc

import adafruit_ntp

DEBUG_DISABLE_SYNC = False


class _FallbackNTP:
    """Dodava nahradni datum, kdyz realny NTP neni dostupny."""

    def __init__(self):
        self.datetime = time.struct_time((1970, 1, 1, 0, 0, 0, 3, 1, -1))


class Clock:
    """Synchronizuje RTC z NTP a formatuje cas pro zobrazeni v aplikaci."""

    def __init__(
        self,
        wifi_client,
        *,
        server="tak.cesnet.cz",
        tz_offset=2,
        cache_seconds=3600,
    ):
        """Ulozi NTP nastaveni a pripravi fallback pro pripad chyby."""
        self.wifi = wifi_client
        self.server = server
        self.tz_offset = tz_offset
        self.cache_seconds = cache_seconds
        self._ntp = None
        self._synced = False
        self._fallback_ntp = _FallbackNTP()

    def sync_ntp(self):
        """Synchronizuje RTC pres NTP nebo pouzije fallback zdroj."""
        ntp_source = self._fallback_ntp

        # Kdyz je sit dostupna, zkus se napojit na NTP a ziskat cerstvy cas.
        if not DEBUG_DISABLE_SYNC and self.wifi.pool is not None:
            try:
                if self._ntp is None:
                    self._ntp = adafruit_ntp.NTP(
                        self.wifi.pool,
                        server=self.server,
                        tz_offset=self.tz_offset,
                        cache_seconds=self.cache_seconds,
                    )
                ntp_source = self._ntp
            except Exception:
                ntp_source = self._fallback_ntp

        # Vysledek se zapise do RTC, odkud pak cte zbytek aplikace.
        rtc.RTC().datetime = ntp_source.datetime
        self._synced = True
        return rtc.RTC().datetime

    def resync(self):
        """Vynuti nove NTP srovnani casu."""
        self._synced = False
        return self.sync_ntp()

    def get_datetime(self):
        """Vrati aktualni datum a cas z RTC, pripadne nejdriv provede sync."""
        if not self._synced:
            return self.sync_ntp()
        return rtc.RTC().datetime

    def get_time(self):
        """Vrati aktualni cas ve formatu `HH:MM`."""
        self.get_datetime()
        now = time.localtime()
        return "{:02}:{:02}".format(now.tm_hour, now.tm_min)
