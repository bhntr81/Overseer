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
ROBE, ROBE_DARK, ROBE_LIGHT = '#2f3442', '#11141b', '#434a5c'
VOID, EYE, EYE_GLOW = '#05070a', '#d9ffe9', '#2bff8a'
BONE, BONE_DARK = '#e9e4d4', '#8f8a78'
SKULL, SKULL_DARK, MIST, HAZE = '#5dff9f', '#0b3d22', '#bff7d6', '#e3fbec'


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


# The scythe he holds. The handle (the snath) is long, wooden and gently bowed,
# standing at his right; the blade leaves its top and sweeps left over his hood,
# hooking down to its point.
SNATH = ((51.0, 63.0), (55.0, 34.0), (47.0, 7.0))
BLADE = ((47.0, 8.0), (25.0, -3.0), (11.0, 19.0))
# Where the little skulls float, as (x, y, size).
SKULLS = ((6.5, 37.0, 3.0), (10.0, 54.0, 2.6), (59.0, 18.0, 2.6), (59.5, 47.0, 3.0), (26.0, 61.5, 2.4))


def _skull(x, y, r):
    """One small green skull in its own glow: cranium, jaw, two dark eyes."""
    return [
        ('circle', (x, y + 0.3 * r, 1.9 * r), MIST),
        ('circle', (x, y, r), SKULL),
        ('poly', [(x - 0.55 * r, y + 0.45 * r), (x + 0.55 * r, y + 0.45 * r),
                  (x + 0.45 * r, y + 1.15 * r), (x - 0.45 * r, y + 1.15 * r)], SKULL),
        ('circle', (x - 0.38 * r, y - 0.05 * r, 0.3 * r), SKULL_DARK),
        ('circle', (x + 0.38 * r, y - 0.05 * r, 0.3 * r), SKULL_DARK),
    ]


def shapes():
    """The drawing, back to front: ('poly', points, colour) and ('circle', (x, y, r), colour)."""
    root, control, tip = BLADE
    drawing = [
        # The spectral haze he stands in.
        ('circle', (30.0, 36.0, 22.0), HAZE),
        # The scythe's handle, behind him.
        ('poly', _curve(*SNATH, 5.0), WOOD_DARK),
        ('poly', _curve(*SNATH, 5.0, shrink=0.9), WOOD),
        ('poly', _curve((53.0, 60.0), (56.4, 34.5), (48.8, 9.5), 0.9), WOOD_LIGHT),
        # The robe: a hood that widens into a body and trails off in wisps.
        ('poly', [(30.0, 8.0), (38.5, 12.0), (42.0, 22.0), (44.0, 36.0), (46.5, 50.0),
                  (42.0, 55.0), (39.5, 50.5), (36.5, 60.0), (32.5, 52.0), (28.0, 62.0),
                  (24.5, 52.5), (20.0, 58.5), (17.5, 50.0), (13.5, 52.5), (15.5, 38.0),
                  (18.0, 22.0), (21.5, 12.0)], ROBE_DARK),
        ('poly', [(30.0, 9.6), (37.4, 13.2), (40.6, 22.4), (42.4, 36.0), (44.4, 49.0),
                  (42.0, 52.0), (39.3, 47.5), (36.4, 56.5), (32.5, 49.5), (28.0, 58.5),
                  (24.8, 50.0), (20.2, 55.5), (18.0, 48.0), (15.6, 49.5), (17.2, 38.0),
                  (19.4, 22.4), (22.6, 13.2)], ROBE),
        ('poly', [(30.0, 9.6), (35.0, 12.0), (29.0, 30.0), (24.0, 48.0), (21.0, 46.0),
                  (24.5, 30.0)], ROBE_LIGHT),
        # The face: a dark void under the hood with two green eyes.
        ('poly', [(30.0, 14.0), (35.0, 17.0), (36.0, 23.0), (33.0, 28.5), (27.0, 28.5),
                  (24.0, 23.0), (25.0, 17.0)], VOID),
        ('circle', (27.6, 21.5, 1.7), EYE_GLOW),
        ('circle', (32.4, 21.5, 1.7), EYE_GLOW),
        ('circle', (27.6, 21.5, 0.9), EYE),
        ('circle', (32.4, 21.5, 0.9), EYE),
        # His sleeve reaching to the handle, and the bony hand gripping it.
        ('poly', _band(38.0, 33.0, 50.5, 31.0, 6.4), ROBE_DARK),
        ('poly', _band(38.5, 33.0, 50.0, 31.1, 4.4), ROBE),
        ('circle', (52.5, 31.0, 2.6), BONE_DARK),
        ('circle', (52.5, 31.0, 1.9), BONE),
        # The blade, over his hood.
        ('poly', _curve(root, control, tip, 11.5, taper=True), STEEL_DARK),
        ('poly', _curve(root, control, tip, 11.5, shrink=1.0, taper=True), STEEL),
        ('poly', _curve((root[0] - 1.0, root[1] + 2.6), (control[0] + 1.5, control[1] + 5.5),
                        (tip[0] + 1.0, tip[1] - 0.5), 2.6, taper=True), STEEL_EDGE),
        ('circle', (47.0, 7.5, 2.2), STEEL_DARK),
    ]
    for x, y, r in SKULLS:
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
