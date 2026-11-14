"""Overseer's mascot: a hooded spectre holding a reaper's scythe, in a cloud of green skulls.

One drawing, kept as plain shapes in a 64 by 64 space, serves every place the
mascot appears: the window draws it on a Tk canvas at any size, and `png` and
`ico` rasterise the same shapes for the window icon and the Windows shortcut.
Keeping one source means the icon on the Desktop and the figure in the window
can never drift apart. Standard library only: the PNG is written with zlib and
struct, the ICO wraps PNG images, which Windows has read since Vista.

    python -m overseer.mascot OUT.png [SIZE]     write the mascot as a PNG
    python -m overseer.mascot OUT.ico            write the multi-size icon
"""
import math
import struct
import sys
import zlib

WOOD, WOOD_DARK, WOOD_LIGHT = '#8a5a2b', '#4a2c12', '#b07a42'
STEEL, STEEL_EDGE, STEEL_DARK = '#dfe6ef', '#8a97a8', '#4b5563'
ROBE, ROBE_DARK, ROBE_LIGHT = '#16181d', '#050608', '#2a2e38'
VOID, EYE_SOCKET, EYE_GLOW, EYE = '#020203', '#2a0505', '#ff2a1a', '#ffd9b0'
BONE, BONE_DARK = '#ece3c6', '#8c8268'
SKULL, SKULL_DARK, MIST = '#a8efc9', '#1d4436', '#2f5a6e'
NIGHT, NIGHT_EDGE = '#1c2160', '#0d1033'


def _arc(cx, cy, radius, start, end, steps=24):
    """Points along a circle from `start` to `end` degrees (screen y points down)."""
    return [(cx + radius * math.cos(math.radians(start + (end - start) * i / steps)),
             cy + radius * math.sin(math.radians(start + (end - start) * i / steps)))
            for i in range(steps + 1)]


def _band(x1, y1, x2, y2, width):
    """A straight strip of the given width from (x1, y1) to (x2, y2)."""
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    return [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]


def _curve(start, control, end, width, shrink=0.0, taper=False, steps=28):
    """A strip along the quadratic curve start -> control -> end.

    Each side is the curve moved along its normal by half the width; with
    `taper` the width narrows to a point at `end`, which is how the blade is
    drawn, and without it the strip keeps its width, which is how the handle
    is drawn. `shrink` narrows it, for the layers drawn over an outline.
    """
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t ** 2 * end[0]
        y = (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t ** 2 * end[1]
        dx = 2 * (1 - t) * (control[0] - start[0]) + 2 * t * (end[0] - control[0])
        dy = 2 * (1 - t) * (control[1] - start[1]) + 2 * t * (end[1] - control[1])
        length = math.hypot(dx, dy) or 1.0
        half = max(0.0, width * ((1 - t) ** 0.75 if taper else 1.0) / 2 - shrink)
        left.append((x - dy / length * half, y + dx / length * half))
        right.append((x + dy / length * half, y - dx / length * half))
    return left + right[::-1]


# The scythe: a long, thin, gently bowed wooden handle held across his body from
# lower left to upper right, and a long narrow blade leaving its top end and
# angling down to the right.
SNATH = ((1.5, 55.0), (30.0, 24.0), (57.0, 7.0))
BLADE = ((56.5, 6.5), (63.5, 16.0), (59.5, 39.0))
# The floating skulls, as (x, y, size): behind him first, then in front.
SKULLS_BEHIND = ((7.0, 31.0, 2.3), (11.0, 21.0, 1.6), (47.0, 30.0, 2.0), (53.0, 41.0, 2.2))
SKULLS_FRONT = ((44.0, 49.0, 2.4), (9.0, 59.0, 2.0), (20.5, 61.0, 2.2), (33.0, 58.5, 1.8),
                (57.0, 54.0, 2.0))


def _skull(x, y, r, glow=True):
    """One small pale-green skull: cranium, jaw, two dark eye sockets, a faint glow."""
    parts = [('circle', (x, y + 0.3 * r, 1.7 * r), MIST)] if glow else []
    return parts + [
        ('circle', (x, y, r), SKULL),
        ('poly', [(x - 0.55 * r, y + 0.45 * r), (x + 0.55 * r, y + 0.45 * r),
                  (x + 0.42 * r, y + 1.15 * r), (x - 0.42 * r, y + 1.15 * r)], SKULL),
        ('circle', (x - 0.38 * r, y - 0.05 * r, 0.3 * r), SKULL_DARK),
        ('circle', (x + 0.38 * r, y - 0.05 * r, 0.3 * r), SKULL_DARK),
    ]


def _hand(x, y, size=2.4):
    """A skeletal hand closed round the handle: knuckles in a row, a dark outline."""
    return [('circle', (x, y, size + 0.7), BONE_DARK)] + [
        ('circle', (x - size * 0.55 + i * size * 0.37, y - size * 0.15, size * 0.42), BONE)
        for i in range(4)] + [('circle', (x, y + size * 0.35, size * 0.7), BONE)]


def shapes():
    """The drawing, back to front: ('poly', points, colour) and ('circle', (x, y, r), colour)."""
    root, control, tip = BLADE
    drawing = [('circle', (32.0, 32.0, 31.5), NIGHT_EDGE), ('circle', (32.0, 32.0, 30.0), NIGHT)]
    for x, y, r in SKULLS_BEHIND:
        drawing += _skull(x, y, r)
    drawing += [
        # The robe: a hood over a black robe that flows down into wisps.
        ('poly', [(26.0, 6.0), (33.5, 9.0), (36.5, 18.0), (39.0, 26.0), (40.5, 38.0),
                  (38.0, 47.0), (35.0, 44.0), (31.5, 55.0), (27.5, 46.5), (22.5, 53.0),
                  (20.5, 44.0), (15.0, 47.0), (16.0, 36.0), (14.5, 28.0), (17.5, 18.0),
                  (19.5, 9.5)], ROBE_DARK),
        ('poly', [(26.0, 7.6), (32.4, 10.2), (35.2, 18.5), (37.6, 26.4), (39.0, 37.5),
                  (37.2, 44.0), (35.0, 41.5), (31.4, 51.0), (27.6, 43.5), (22.8, 49.5),
                  (21.2, 41.5), (16.8, 43.5), (17.6, 36.0), (16.2, 28.2), (18.9, 18.5),
                  (20.6, 10.6)], ROBE),
        ('poly', [(26.0, 7.6), (30.0, 9.4), (25.5, 24.0), (21.0, 40.0), (18.6, 38.0), (21.5, 24.0)],
         ROBE_LIGHT),
        # Deep in the hood, a skull with burning red eyes.
        ('poly', [(26.0, 10.0), (31.0, 12.5), (32.0, 19.0), (29.5, 24.5), (22.5, 24.5),
                  (20.0, 19.0), (21.0, 12.5)], VOID),
        ('circle', (26.0, 16.0, 4.6), BONE),
        ('poly', [(22.6, 18.0), (29.4, 18.0), (28.4, 22.4), (23.6, 22.4)], BONE),
        ('circle', (24.2, 15.8, 1.55), EYE_SOCKET),
        ('circle', (27.8, 15.8, 1.55), EYE_SOCKET),
        ('circle', (24.2, 15.8, 1.0), EYE_GLOW),
        ('circle', (27.8, 15.8, 1.0), EYE_GLOW),
        ('circle', (24.0, 15.6, 0.4), EYE),
        ('circle', (27.6, 15.6, 0.4), EYE),
        ('poly', [(26.0, 17.6), (26.9, 19.3), (25.1, 19.3)], EYE_SOCKET),
        ('poly', [(24.0, 20.6), (28.0, 20.6), (28.0, 21.2), (24.0, 21.2)], BONE_DARK),
        # Sleeves reaching out to where the hands hold the handle.
        ('poly', _band(18.0, 27.0, 13.5, 41.0, 6.0), ROBE_DARK),
        ('poly', _band(18.2, 27.4, 13.8, 40.4, 4.2), ROBE),
        ('poly', _band(33.5, 25.0, 39.5, 23.5, 5.4), ROBE_DARK),
        ('poly', _band(33.8, 25.0, 39.0, 23.6, 3.6), ROBE),
        # The scythe across him, in front of the robe.
        ('poly', _curve(*SNATH, 3.6), WOOD_DARK),
        ('poly', _curve(*SNATH, 3.6, shrink=0.8), WOOD),
        ('poly', _curve((2.0, 54.0), (30.0, 23.0), (56.5, 6.4), 0.7), WOOD_LIGHT),
        ('poly', _curve(root, control, tip, 5.0, taper=True), STEEL_DARK),
        ('poly', _curve(root, control, tip, 5.0, shrink=0.7, taper=True), STEEL),
        ('poly', _curve((root[0] + 0.6, root[1] + 1.5), (control[0] - 0.5, control[1] + 1.0),
                        (tip[0] - 0.3, tip[1] - 1.0), 1.4, taper=True), STEEL_EDGE),
    ]
    drawing += _hand(13.2, 42.4) + _hand(40.0, 22.6)
    for x, y, r in SKULLS_FRONT:
        drawing += _skull(x, y, r)
    return drawing


def draw(canvas, x, y, size, tag='mascot'):
    """Draw the mascot on a Tk canvas with its top-left corner at (x, y)."""
    scale = size / 64.0
    for kind, data, colour in shapes():
        if kind == 'poly':
            flat = [value for px, py in data for value in (x + px * scale, y + py * scale)]
            canvas.create_polygon(flat, fill=colour, outline='', tags=tag)
        else:
            cx, cy, r = data
            canvas.create_oval(x + (cx - r) * scale, y + (cy - r) * scale,
                               x + (cx + r) * scale, y + (cy + r) * scale,
                               fill=colour, outline='', tags=tag)


def _rgb(colour):
    return tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))


def _inside(points, px, py):
    """Even-odd rule: is (px, py) inside the polygon?"""
    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def pixels(size, samples=4):
    """Rasterise to `size` x `size` RGBA rows, supersampled `samples`^2 per pixel."""
    drawing = []
    for kind, data, colour in shapes():
        if kind == 'poly':
            xs, ys = [p[0] for p in data], [p[1] for p in data]
            box = (min(xs), min(ys), max(xs), max(ys))
        else:
            cx, cy, r = data
            box = (cx - r, cy - r, cx + r, cy + r)
        drawing.append((kind, data, _rgb(colour), box))
    scale = 64.0 / size
    rows = []
    for row in range(size):
        line = bytearray()
        for column in range(size):
            red = green = blue = alpha = 0.0
            for sy in range(samples):
                for sx in range(samples):
                    px = (column + (sx + 0.5) / samples) * scale
                    py = (row + (sy + 0.5) / samples) * scale
                    hit = None
                    for kind, data, colour, (x0, y0, x1, y1) in drawing:
                        if not (x0 <= px <= x1 and y0 <= py <= y1):
                            continue
                        if kind == 'poly':
                            if _inside(data, px, py):
                                hit = colour
                        elif (px - data[0]) ** 2 + (py - data[1]) ** 2 <= data[2] ** 2:
                            hit = colour
                    if hit:
                        red, green, blue, alpha = red + hit[0], green + hit[1], blue + hit[2], alpha + 1
            count = samples * samples
            if alpha:
                line += bytes((round(red / alpha), round(green / alpha), round(blue / alpha),
                               round(255 * alpha / count)))
            else:
                line += b'\0\0\0\0'
        rows.append(bytes(line))
    return rows


def png(size=256):
    """The mascot as PNG bytes, RGBA, transparent background."""
    raw = b''.join(b'\0' + row for row in pixels(size))

    def chunk(kind, body):
        return (struct.pack('>I', len(body)) + kind + body
                + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff))
    header = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def ico(sizes=ICON_SIZES):
    """A Windows .ico holding one PNG image per size."""
    images = [png(size) for size in sizes]
    head = struct.pack('<HHH', 0, 1, len(images))
    offset = len(head) + 16 * len(images)
    entries, body = b'', b''
    for size, image in zip(sizes, images):
        side = 0 if size >= 256 else size
        entries += struct.pack('<BBBBHHII', side, side, 0, 0, 1, 32, len(image), offset + len(body))
        body += image
    return head + entries + body


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__.strip().splitlines()[-2].strip())
        return 2
    out = argv[0]
    data = ico() if out.lower().endswith('.ico') else png(int(argv[1]) if len(argv) > 1 else 256)
    with open(out, 'wb') as handle:
        handle.write(data)
    print('wrote', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
