"""The single-program screen model shows what the user's terminal shows."""
import unittest

from overseer.terminal import Screen


class ScreenTests(unittest.TestCase):
    def test_text_and_cursor_line(self):
        screen = Screen(20, 4)
        screen.feed("hello\r\n❯ ")
        self.assertEqual(screen.text().splitlines()[:2], ["hello", "❯"])
        self.assertEqual(screen.cursor_line(), "❯")
        self.assertEqual((screen.cursor_y, screen.cursor_x), (1, 2))

    def test_long_lines_wrap(self):
        screen = Screen(5, 3)
        screen.feed("abcdefg")
        self.assertEqual(screen.text().splitlines()[:2], ["abcde", "fg"])

    def test_scrolls_past_the_last_row(self):
        screen = Screen(10, 2)
        screen.feed("one\r\ntwo\r\nthree")
        self.assertEqual(screen.text(), "two\nthree")

    def test_erase_display_and_cursor_addressing(self):
        screen = Screen(10, 3)
        screen.feed("junk\x1b[2J\x1b[2;3Hx")
        self.assertEqual(screen.text(), "\n  x\n")

    def test_erase_to_end_of_line(self):
        screen = Screen(10, 1)
        screen.feed("abcdef\x1b[1;3H\x1b[K")
        self.assertEqual(screen.text(), "ab")

    def test_alternate_screen_is_shown_and_left(self):
        screen = Screen(10, 2)
        screen.feed("shell")
        screen.feed("\x1b[?1049hTUI")
        self.assertEqual(screen.text().splitlines()[0], "TUI")
        screen.feed("\x1b[?1049l")
        self.assertEqual(screen.text().splitlines()[0], "shell")

    def test_an_escape_split_across_reads_is_kept(self):
        screen = Screen(10, 2)
        screen.feed("a\x1b[")
        screen.feed("2Kb")
        self.assertEqual(screen.cursor_line(), " b")

    def test_colours_and_titles_are_not_text(self):
        screen = Screen(20, 1)
        screen.feed("\x1b]0;title\x07\x1b[1;32mgreen\x1b[0m")
        self.assertEqual(screen.text(), "green")

    def test_wide_characters_take_two_cells(self):
        screen = Screen(6, 1)
        screen.feed("日本x")
        self.assertEqual(screen.text(), "日本x")
        self.assertEqual(screen.cursor_x, 5)

    def test_resize_keeps_text_and_clamps_the_cursor(self):
        screen = Screen(10, 3)
        screen.feed("abc\r\n\r\nxyz")
        screen.resize(4, 2)
        self.assertEqual(screen.text(), "abc\n")
        self.assertLess(screen.cursor_y, 2)


if __name__ == "__main__":
    unittest.main()
