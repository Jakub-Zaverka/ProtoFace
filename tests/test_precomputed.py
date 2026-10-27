import builtins
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("precomputed", ROOT / "src/precomputed.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Display:
    def rgb888_to_rgb565(self, color):
        return ((color >> 8) & 0xf800) | ((color >> 5) & 0x7e0) | ((color >> 3) & 31)


class PackedTests(unittest.TestCase):
    def test_all_assets_forward_reverse_cache_and_bounds(self):
        original_open = builtins.open
        def asset_open(path, mode):
            return original_open(ROOT / "src" / path.lstrip("/"), mode)
        display = Display()
        paths = list((ROOT / "src/transitions").glob("*.mph"))
        self.assertEqual(len(paths), 51)
        with patch("builtins.open", side_effect=asset_open):
            for path in paths:
                a, b = path.stem.split("--")
                header = path.read_bytes()[:7]
                width, height = header[4:6]
                frames = module.load_frames(display, a + ".bmp", b + ".bmp", width, height)
                self.assertEqual(len(frames), 7)
                reverse = module.load_frames(display, b + ".bmp", a + ".bmp", width, height)
                self.assertIs(frames[0], reverse[-1])
                self.assertIs(frames[-1], reverse[0])
                for frame in frames:
                    for x, y, color in frame:
                        self.assertTrue(0 <= x < width and 0 <= y < height)
                        self.assertTrue(0 <= color <= 65535)
                self.assertLessEqual(len(display.transition_cache), 6)

    def test_timed_transition_skips_old_frames(self):
        from test_smooth_speak import emotes
        display = Display()
        display.transition_now = 1.0
        display.draws = []
        display.draw_sparse_rgb565 = lambda matrix, frame: display.draws.append(frame)
        frames = [[(0, 0, i)] for i in range(7)]
        region = {"matrix": {}, "transition_moves": {"frames": frames, "start": 1.0},
                  "transition_frame": -1}
        self.assertTrue(emotes._tick_image_transition(display, region))
        self.assertIs(display.draws[-1], frames[0])
        self.assertTrue(emotes._tick_image_transition(display, region))
        self.assertEqual(len(display.draws), 1)
        display.transition_now = 2.0
        self.assertFalse(emotes._tick_image_transition(display, region))
        self.assertIs(display.draws[-1], frames[-1])
        self.assertIsNone(region["transition_moves"])


if __name__ == "__main__":
    unittest.main()
