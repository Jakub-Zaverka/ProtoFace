"""Compact offline-generated morph frames; cache shared by both face sides."""


class PackedFrame:
    def __init__(self, data):
        self.data = data

    def __iter__(self):
        data = self.data
        for i in range(0, len(data), 4):
            yield data[i], data[i + 1], data[i + 2] | (data[i + 3] << 8)


def load_frames(display, first, second, width, height):
    a = first.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    b = second.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    reverse = a > b
    a, b = sorted((a, b))
    key = (a, b, width, height)
    cache = getattr(display, 'transition_cache', None)
    if cache is None:
        cache = {}
        display.transition_cache = cache
    frames = cache.get(key)
    if frames is None:
        try:
            with open('/transitions/' + a + '--' + b + '.mph', 'rb') as handle:
                header = handle.read(7)
                if header[:4] != b'MPH1' or header[4:6] != bytes((width, height)):
                    raise ValueError('Invalid morph header')
                frames = []
                for _ in range(header[6]):
                    raw_count = handle.read(2)
                    if len(raw_count) != 2:
                        raise ValueError('Truncated morph')
                    count = raw_count[0] | (raw_count[1] << 8)
                    raw = handle.read(count * 4)
                    if len(raw) != count * 4:
                        raise ValueError('Truncated morph frame')
                    data = bytearray(raw)
                    for i in range(0, len(data), 4):
                        color = data[i + 2] | (data[i + 3] << 8)
                        # Expand canonical RGB565; use the same panel conversion as BMP.
                        r, g, b = (color >> 11) & 31, (color >> 5) & 63, color & 31
                        color = display.rgb888_to_rgb565(((r * 255 // 31) << 16)
                                                       | ((g * 255 // 63) << 8) | (b * 255 // 31))
                        data[i + 2], data[i + 3] = color & 255, color >> 8
                    frames.append(PackedFrame(data))
        except OSError:
            return None
        # Bound RAM; active animations keep references even after cache eviction.
        if len(cache) >= 6:
            cache.clear()
        cache[key] = frames
    return frames[::-1] if reverse else frames
