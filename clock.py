import time
import rtc

import adafruit_ntp

DEBUG_DISABLE_SYNC = True


class _FallbackNTP:
    """Dummy NTP source used when real sync is disabled or unavailable."""

    def __init__(self):
        self.datetime = time.struct_time((1970, 1, 1, 0, 0, 0, 3, 1, -1))


class Clock:
    def __init__(
        self,
        wifi_client,
        *,
        server="tak.cesnet.cz",
        tz_offset=2,
        cache_seconds=3600,
    ):
        self.wifi = wifi_client
        self.server = server
        self.tz_offset = tz_offset
        self.cache_seconds = cache_seconds
        self._ntp = None
        self._synced = False
        self._fallback_ntp = _FallbackNTP()

    def sync_ntp(self):
        ntp_source = self._fallback_ntp

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

        rtc.RTC().datetime = ntp_source.datetime
        self._synced = True
        return rtc.RTC().datetime

    def resync(self):
        self._synced = False
        return self.sync_ntp()

    def get_datetime(self):
        if not self._synced:
            return self.sync_ntp()
        return rtc.RTC().datetime

    def get_time(self):
        self.get_datetime()
        now = time.localtime()
        return "{:02}:{:02}".format(now.tm_hour, now.tm_min)
