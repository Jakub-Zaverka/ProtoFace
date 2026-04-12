import time
import rtc

import adafruit_ntp


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

    def sync_ntp(self):
        if self.wifi.pool is None:
            raise RuntimeError("WiFi is not connected. Call connect() first.")

        if self._ntp is None:
            self._ntp = adafruit_ntp.NTP(
                self.wifi.pool,
                server=self.server,
                tz_offset=self.tz_offset,
                cache_seconds=self.cache_seconds,
            )

        rtc.RTC().datetime = self._ntp.datetime
        self._synced = True
        print(rtc.RTC().datetime)
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
