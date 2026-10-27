"""Generate packed RGB565 morphs on a host, without CircuitPython libraries."""
import ast
import itertools
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
STEPS = 6
GROUPS = {
    (32, 16): ['eye', 'sleep', 'eye_blink', 'eye_open', 'hearth', 'question', 'sad_eye', 'u', 'cross'],
    (64, 16): ['mouth', 'mouth_speak', 'blep', 'flat_mouth', 'sad_mouth', 'wwww'],
}


def pixels(name, width, height):
    data = (ROOT / 'src/faces' / (name + '.bmp')).read_bytes()
    offset = struct.unpack_from('<I', data, 10)[0]
    w, h = struct.unpack_from('<ii', data, 18)
    bpp = struct.unpack_from('<H', data, 28)[0]
    assert bpp == 24 and struct.unpack_from('<I', data, 30)[0] == 0
    stride = (w * 3 + 3) & ~3
    result = []
    for y in range(min(abs(h), height)):
        row = y if h < 0 else h - 1 - y
        for x in range(min(w, width)):
            b, g, r = data[offset + row * stride + x * 3:][:3]
            # Canonical RGB565, brightness and panel wiring applied on the board.
            color = ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)
            if color:
                result.append((x, y, color))
    return result


def generate():
    tree = ast.parse((ROOT / 'src/emotes.py').read_text(encoding='utf-8'))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name in ('_build_transition_moves', '_rgb565_lerp')]
    namespace = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<morph math>', 'exec'), namespace)
    output = ROOT / 'src/transitions'
    output.mkdir(exist_ok=True)
    total = 0
    count = 0
    for (width, height), names in GROUPS.items():
        for a, b in itertools.combinations(sorted(names), 2):
            old, new = pixels(a, width, height), pixels(b, width, height)
            moves = namespace['_build_transition_moves'](old, new)
            frames = [old]
            for step in range(1, STEPS):
                frame = {}
                for ox, oy, oc, nx, ny, nc in moves:
                    x = ox + ((nx - ox) * step + STEPS // 2) // STEPS
                    y = oy + ((ny - oy) * step + STEPS // 2) // STEPS
                    color = namespace['_rgb565_lerp'](oc, nc, step, STEPS)
                    if color:
                        frame[x, y] = color
                frames.append([(x, y, c) for (x, y), c in frame.items()])
            frames.append(new)
            data = bytearray(b'MPH1' + bytes((width, height, STEPS + 1)))
            for frame in frames:
                data += struct.pack('<H', len(frame))
                for x, y, color in frame:
                    data += struct.pack('<BBH', x, y, color)
            (output / (a + '--' + b + '.mph')).write_bytes(data)
            total += len(data)
            count += 1
    print(f'{count} transitions, {total} bytes ({total / 1024:.1f} KiB)')


if __name__ == '__main__':
    generate()
