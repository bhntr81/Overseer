"""The mascot: one drawing, rasterised to a valid PNG and a multi-size Windows icon."""
import struct
import unittest
import zlib

from overseer import mascot


class MascotTests(unittest.TestCase):
    def test_png_is_a_valid_rgba_image_of_the_asked_size(self):
        data = mascot.png(16)
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        width, height, depth, colour = struct.unpack('>IIBB', data[16:26])
        self.assertEqual((width, height, depth, colour), (16, 16, 8, 6))
        start = data.index(b'IDAT') + 4
        length = struct.unpack('>I', data[start - 8:start - 4])[0]
        raw = zlib.decompress(data[start:start + length])
        self.assertEqual(len(raw), 16 * (1 + 16 * 4))

    def test_the_drawing_is_mostly_opaque_in_the_middle_and_clear_in_a_corner(self):
        rows = mascot.pixels(16, samples=2)
        self.assertEqual(rows[0][3], 0)
        self.assertEqual(rows[8][8 * 4 + 3], 255)

    def test_ico_holds_one_png_per_size(self):
        data = mascot.ico((16, 32))
        reserved, kind, count = struct.unpack('<HHH', data[:6])
        self.assertEqual((reserved, kind, count), (0, 1, 2))
        for index, size in enumerate((16, 32)):
            side, _, _, _, _, _, length, offset = struct.unpack('<BBBBHHII', data[6 + 16 * index:22 + 16 * index])
            self.assertEqual(side, size)
            self.assertEqual(data[offset:offset + 8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(offset + length <= len(data), True)

    def test_every_shape_is_inside_the_drawing_space(self):
        for kind, data, colour in mascot.shapes():
            self.assertRegex(colour, r'^#[0-9a-f]{6}$')
            points = data if kind == 'poly' else [(data[0], data[1])]
            for x, y in points:
                self.assertTrue(-3 <= x <= 67 and -3 <= y <= 67, (kind, x, y))


if __name__ == '__main__':
    unittest.main()
