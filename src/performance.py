"""Lehke runtime metriky pro CircuitPython hlavni smycku."""

import gc
import time


class PerformanceMonitor:
    """Meri periodu smycky, dobu prace, sekce kodu a volnou pamet."""

    def __init__(self, report_interval=5.0):
        self.report_interval = report_interval
        self.last_loop_start = None
        self.current_loop_start = None
        self.current_section_start = None
        self.current_section_name = None
        self.current_work_ms = 0.0
        self.current_sections = {}
        self.last_report_time = time.monotonic()
        self.reset_window()
        self.last_snapshot = {
            "loops": 0,
            "loop_avg_ms": 0.0,
            "loop_max_ms": 0.0,
            "work_avg_ms": 0.0,
            "work_max_ms": 0.0,
            "load_pct": 0.0,
            "mem_free": self._mem_free(),
            "mem_alloc": self._mem_alloc(),
            "slowest_section": "",
            "slowest_section_ms": 0.0,
        }

    def reset_window(self):
        self.loop_count = 0
        self.loop_total_ms = 0.0
        self.loop_max_ms = 0.0
        self.work_total_ms = 0.0
        self.work_max_ms = 0.0
        self.section_totals = {}
        self.section_max = {}

    def begin_loop(self):
        now = time.monotonic()
        if self.last_loop_start is not None:
            loop_ms = (now - self.last_loop_start) * 1000.0
            self.loop_total_ms += loop_ms
            if loop_ms > self.loop_max_ms:
                self.loop_max_ms = loop_ms

        self.last_loop_start = now
        self.current_loop_start = now
        self.current_work_ms = 0.0
        self.current_sections = {}
        self.current_section_start = None
        self.current_section_name = None

    def begin_section(self, name):
        self.end_section()
        self.current_section_name = name
        self.current_section_start = time.monotonic()

    def end_section(self):
        if self.current_section_start is None:
            return

        elapsed_ms = (time.monotonic() - self.current_section_start) * 1000.0
        name = self.current_section_name
        self.current_work_ms += elapsed_ms
        self.current_sections[name] = self.current_sections.get(name, 0.0) + elapsed_ms
        self.current_section_start = None
        self.current_section_name = None

    def end_work(self):
        self.end_section()
        self.loop_count += 1
        self.work_total_ms += self.current_work_ms
        if self.current_work_ms > self.work_max_ms:
            self.work_max_ms = self.current_work_ms

        for name, elapsed_ms in self.current_sections.items():
            self.section_totals[name] = self.section_totals.get(name, 0.0) + elapsed_ms
            if elapsed_ms > self.section_max.get(name, 0.0):
                self.section_max[name] = elapsed_ms

    def should_report(self):
        return time.monotonic() - self.last_report_time >= self.report_interval

    def snapshot(self):
        loops = max(1, self.loop_count)
        loop_avg_ms = self.loop_total_ms / loops
        work_avg_ms = self.work_total_ms / loops
        load_pct = 0.0
        if loop_avg_ms > 0.0:
            load_pct = min(100.0, (work_avg_ms / loop_avg_ms) * 100.0)

        slowest_section = ""
        slowest_section_ms = 0.0
        for name, elapsed_ms in self.section_max.items():
            if elapsed_ms > slowest_section_ms:
                slowest_section = name
                slowest_section_ms = elapsed_ms

        self.last_snapshot = {
            "loops": self.loop_count,
            "loop_avg_ms": loop_avg_ms,
            "loop_max_ms": self.loop_max_ms,
            "work_avg_ms": work_avg_ms,
            "work_max_ms": self.work_max_ms,
            "load_pct": load_pct,
            "mem_free": self._mem_free(),
            "mem_alloc": self._mem_alloc(),
            "slowest_section": slowest_section,
            "slowest_section_ms": slowest_section_ms,
        }
        return self.last_snapshot

    def report(self):
        snapshot = self.snapshot()
        self.last_report_time = time.monotonic()
        self.reset_window()
        return snapshot

    def format_debug_lines(self):
        snapshot = self.last_snapshot
        return [
            "Loop: {:.1f}/{:.1f}ms".format(
                snapshot["loop_avg_ms"],
                snapshot["loop_max_ms"],
            ),
            "Work: {:.1f}ms {:2.0f}%".format(
                snapshot["work_avg_ms"],
                snapshot["load_pct"],
            ),
            "Mem: {}B".format(snapshot["mem_free"]),
        ]

    def format_log_line(self):
        snapshot = self.last_snapshot
        return (
            "Perf loops={loops} loop_avg={loop_avg_ms:.1f}ms "
            "loop_max={loop_max_ms:.1f}ms work_avg={work_avg_ms:.1f}ms "
            "load={load_pct:.0f}% mem_free={mem_free}B slowest={slowest_section}:{slowest_section_ms:.1f}ms"
        ).format(**snapshot)

    def _mem_free(self):
        try:
            return gc.mem_free()
        except AttributeError:
            return 0

    def _mem_alloc(self):
        try:
            return gc.mem_alloc()
        except AttributeError:
            return 0
