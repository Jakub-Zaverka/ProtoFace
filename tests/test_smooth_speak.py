"""Host checks for the shared, clock-driven mouth player (no board required)."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


def load_emotes():
    spec = importlib.util.spec_from_file_location(
        "emotes_under_test", Path(__file__).resolve().parents[1] / "src/emotes.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "displayio": types.ModuleType("displayio"),
        "gifio": types.ModuleType("gifio"),
    }):
        spec.loader.exec_module(module)
    return module


emotes = load_emotes()


class Display:
    def __init__(self):
        self.draws = []
        self.images = {"idle.bmp": [[1, 0, 0]], "speak.bmp": [[0, 0, 1]]}

    def load_transition(self, first, second, width, height):
        return [[(0, 0, 1)]] + [[(1, 0, 1)] for _ in range(5)] + [[(2, 0, 1)]]

    def get_image_matrix_rgb565(self, path):
        return self.images[path]

    def set_matrix_hidden(self, matrix, hidden):
        pass

    def draw_sparse_rgb565(self, matrix, pixels):
        self.draws.append((matrix, pixels))


class SmoothSpeakTests(unittest.TestCase):
    def setUp(self):
        self.c = emotes.FaceEmoteController.__new__(emotes.FaceEmoteController)
        c = self.c
        c.display = Display()
        c.verbose = False
        c.mouth_matrix = {"width": 3, "height": 1}
        c.mouth_idle_emote = emotes.create_image_emote("idle.bmp", "mouth")
        c.mouth_speak_emote = emotes.create_image_emote("speak.bmp", "speak")
        c.region_sets = [{"mouth": emotes.create_region("mouth", {"side": side})}
                         for side in ("left", "right")]
        c.mouth_region = c.region_sets[0]["mouth"]
        c.speak_frames = c._prepare_speak_frames()
        c.speak_level = 0.0
        c.speak_last_time = 0.0
        c.speak_last_frame = 0
        c.speak_managed = True
        c.smooth_speak_enabled = True
        c.smooth_transitions_enabled = False

    def tick(self, now, speaking=True):
        return self.c._update_shared_speak({
            "source": self.c.mouth_speak_emote if speaking else None,
            "duration": 6}, now)

    def test_exact_endpoints(self):
        self.assertEqual(self.c.speak_frames[0], [(0, 0, 1)])
        self.assertEqual(self.c.speak_frames[-1], [(2, 0, 1)])

    def test_shared_frame_and_no_redundant_draw(self):
        self.tick(0.1)
        draws = self.c.display.draws
        self.assertEqual(len(draws), 2)
        self.assertIs(draws[0][1], draws[1][1])
        self.tick(0.101)
        self.assertEqual(len(draws), 2)

    def test_same_progress_at_different_loop_rates(self):
        self.tick(0.1)
        expected = self.c.speak_level
        self.setUp()
        for now in (0.02, 0.04, 0.06, 0.08, 0.1):
            self.tick(now)
        self.assertAlmostEqual(self.c.speak_level, expected)

    def test_reverse_without_restart_and_complete_idle(self):
        self.tick(0.1)
        self.tick(0.15, speaking=False)
        self.assertAlmostEqual(self.c.speak_level, 0.25)
        self.tick(0.3, speaking=False)
        self.assertEqual(self.c.speak_level, 0)
        for regions in self.c.region_sets:
            self.assertFalse(regions["mouth"]["active"])
            self.assertIsNone(regions["mouth"]["current_source"])
        self.assertIs(self.c.display.draws[-1][1], self.c.speak_frames[0])

    def test_stall_skips_to_endpoint(self):
        self.tick(2.0)
        self.assertEqual(len(self.c.display.draws), 2)
        self.assertIs(self.c.display.draws[0][1], self.c.speak_frames[-1])

    def test_region_dispatch_updates_mouth_only_once(self):
        for regions in self.c.region_sets:
            for name in ("nose", "eye", "whole"):
                regions[name] = emotes.create_region(name, {})
        requests = {name: {"source": None, "duration": 0}
                    for name in ("nose", "eye", "whole", "mouth")}
        requests["mouth"]["source"] = self.c.mouth_speak_emote
        with patch.object(emotes, "update_emote", return_value=(False, False)) as generic:
            with patch.object(emotes.time, "monotonic", return_value=0.1):
                self.c._update_region_sets(requests)
            self.assertEqual(generic.call_count, 6)
            self.assertEqual(len(self.c.display.draws), 2)
            # Other expressions keep their existing controller on both sides.
            requests["mouth"]["source"] = emotes.create_image_emote("blep.bmp", "blep")
            generic.reset_mock()
            self.c._update_region_sets(requests)
            self.assertEqual(generic.call_count, 8)
            self.assertFalse(self.c.speak_managed)

    def test_generic_transition_is_allowed_to_finish(self):
        for regions in self.c.region_sets:
            for name in ("nose", "eye", "whole"):
                regions[name] = emotes.create_region(name, {})
        self.c.speak_managed = False
        self.c.mouth_region["current_source"] = self.c.mouth_speak_emote
        self.c.mouth_region["transition_moves"] = [(0, 0, 1, 2, 0, 1)]
        requests = {name: {"source": None, "duration": 0}
                    for name in ("nose", "eye", "whole", "mouth")}
        requests["mouth"]["source"] = self.c.mouth_speak_emote
        with patch.object(emotes, "update_emote", return_value=(False, False)) as generic:
            self.c._update_region_sets(requests)
            self.assertEqual(generic.call_count, 8)
            self.assertEqual(self.c.display.draws, [])

    def test_disabled_smoothing_is_immediate(self):
        self.c.smooth_speak_enabled = False
        self.tick(0.001)
        self.assertEqual(self.c.speak_level, 1.0)
        self.tick(0.002, speaking=False)
        self.assertEqual(self.c.speak_level, 0.0)


if __name__ == "__main__":
    unittest.main()
