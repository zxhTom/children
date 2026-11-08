"""Generate private Home Screen icons with Python's standard library."""
from pathlib import Path
import math
import struct
import zlib

OUT = Path(__file__).resolve().parent.parent / "backend" / "static"


def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)


def icon(size):
    rows = []
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            u = (px + .5) / size
            v = (py + .5) / size
            light = max(0, 1 - math.hypot(u - .12, v - .08))
            base = [int(192 + 38 * light), int(100 + 45 * light), int(73 + 41 * light)]
            x = (u - .5) / .28
            y = (.54 - v) / .28
            heart = (x*x + y*y - 1)**3 - x*x*y**3 <= 0
            if heart:
                base = [255, 250, 244]
            # A small sparkle inside the heart links the icon to the handbook's mark.
            sx = (u - .5) / .12
            sy = (v - .50) / .12
            sparkle = abs(sx) + abs(sy) < .52 and (abs(sx) < .14 or abs(sy) < .14 or abs(sx) + abs(sy) < .35)
            if heart and sparkle:
                base = [193, 106, 78]
            row.extend((*base, 255))
        rows.append(bytes(row))
    data = b''.join(rows)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', size, size, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(data, 9)) + chunk(b'IEND', b'')
    (OUT / f'app-icon-{size}.png').write_bytes(png)


if __name__ == '__main__':
    for dimension in (192, 512):
        icon(dimension)
