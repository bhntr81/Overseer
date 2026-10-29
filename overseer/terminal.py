"""A visible-screen model for a client that runs in this terminal, not a pane.

The monitor reads a pane through tmux: the visible text and the cursor. In
single-program mode there is no tmux, so this module keeps the same view by
interpreting the bytes the client writes to its pseudo-terminal.

It renders only what fits in the grid, exactly as the user sees it: the
alternate screen when the client uses one, scrolling, erasing and cursor
addressing. It answers no terminal query. The client's queries reach the real
terminal, which answers them, and the driver relays that reply back.

This is not a complete terminal: colours, mouse reporting and keypad modes are
ignored, and DSR/DA replies are left to the real terminal. Everything the
monitor needs -- visible text, cursor row and column -- is kept.
"""

import re
import unicodedata


PRINTABLE = re.compile(r"[^\x00-\x1f\x7f]+")
CSI = re.compile(r"\x1b\[([0-?]*)([ -/]*)([@-~])")
OSC = "\x1b]"
STRING_INTRODUCERS = ("\x1bP", "\x1b^", "\x1b_", "\x1bX")
TERMINATOR_BEL = "\x07"
TERMINATOR_ST = "\x1b\\"
MAX_PENDING = 8192


def width(character):
    """Return the number of cells a character occupies."""
    if unicodedata.combining(character):
        return 0
    if unicodedata.category(character) in {"Mn", "Me", "Cf"}:
        return 0
    if unicodedata.east_asian_width(character) in {"W", "F"}:
        return 2
    return 1


class Buffer:
    """The cells of one screen: a wide character occupies two cells."""

    def __init__(self, columns, rows):
        self.columns = columns
        self.rows = rows
        self.cells = [self._blank() for _ in range(rows)]

    def _blank(self):
        return [" "] * self.columns

    def resize(self, columns, rows):
        cells = []
        for index in range(rows):
            if index < self.rows:
                line = self.cells[index][:columns]
                line.extend([" "] * (columns - len(line)))
            else:
                line = [" "] * columns
            cells.append(line)
        self.columns = columns
        self.rows = rows
        self.cells = cells

    def line(self, row):
        """Return one row as the user sees it, with trailing blanks removed."""
        return "".join(cell for cell in self.cells[row] if cell != "").rstrip(" ")

    def text(self):
        return "\n".join(self.line(row) for row in range(self.rows))


class Screen:
    """A small VT100/xterm screen: text, cursor, scrolling and erasing."""

    def __init__(self, columns=80, rows=24):
        self.columns = max(1, int(columns))
        self.rows = max(1, int(rows))
        self.main = Buffer(self.columns, self.rows)
        self.alternate = Buffer(self.columns, self.rows)
        self.buffer = self.main
        self.x = 0
        self.y = 0
        self.wrap_pending = False
        self.saved = (0, 0, False)
        self.scroll_top = 0
        self.scroll_bottom = self.rows - 1
        self.origin = False
        self.autowrap = True
        self.tabs = set(range(8, self.columns, 8))
        self._pending = ""

    # -- reading ---------------------------------------------------------

    def text(self):
        return self.buffer.text()

    def cursor_line(self):
        return self.buffer.line(self.y)

    @property
    def cursor_x(self):
        return self.x

    @property
    def cursor_y(self):
        return self.y

    # -- feeding ---------------------------------------------------------

    def feed(self, text):
        """Consume terminal output. An incomplete escape is kept for next time."""
        if self._pending:
            text = self._pending + text
            self._pending = ""
        index = 0
        length = len(text)
        while index < length:
            character = text[index]
            if character == "\x1b":
                end = self._escape(text, index)
                if end is None:
                    remainder = text[index:]
                    self._pending = remainder[-MAX_PENDING:]
                    return
                index = end
            elif character < " " or character == "\x7f":
                self._control(character)
                index += 1
            else:
                run = PRINTABLE.match(text, index)
                for item in run.group():
                    self._write(item)
                index = run.end()

    # -- parser ----------------------------------------------------------

    def _escape(self, text, index):
        if index + 1 >= len(text):
            return None
        following = text[index + 1]
        if following == "[":
            match = CSI.match(text, index)
            if match is None:
                # A broken or unfinished sequence: wait while it is short.
                if len(text) - index > 64:
                    return index + 2
                return None
            self._csi(match.group(1), match.group(2), match.group(3))
            return match.end()
        if text.startswith(OSC, index) or text.startswith(STRING_INTRODUCERS, index):
            return self._skip_string(text, index)
        if following in "()*+-./#":
            if index + 2 >= len(text):
                return None
            return index + 3
        handler = {
            "7": self._save_cursor,
            "8": self._restore_cursor,
            "D": self._index,
            "E": self._next_line,
            "M": self._reverse_index,
            "c": self._reset,
        }.get(following)
        if handler is not None:
            handler()
        return index + 2

    def _skip_string(self, text, index):
        bel = text.find(TERMINATOR_BEL, index + 2)
        st = text.find(TERMINATOR_ST, index + 2)
        ends = [position for position in (bel, st) if position != -1]
        if not ends:
            if len(text) - index > MAX_PENDING:
                return index + 2
            return None
        end = min(ends)
        if end == st:
            return end + 2
        return end + 1

    def _control(self, character):
        if character in "\n\x0b\x0c":
            self._linefeed()
        elif character == "\r":
            self.x = 0
            self.wrap_pending = False
        elif character == "\b":
            self.x = max(0, self.x - 1)
            self.wrap_pending = False
        elif character == "\t":
            self._tab()
        elif character == "\x0e" or character == "\x0f":
            return
        # BEL and every other control character changes no cell.

    def _csi(self, raw, intermediate, final):
        private = ""
        if raw[:1] in {"?", "<", "=", ">"}:
            private = raw[0]
            raw = raw[1:]
        numbers = []
        for part in re.split(r"[;:]", raw):
            numbers.append(int(part) if part.isdigit() else 0)
        first = numbers[0] if numbers else 0
        count = first or 1
        if final == "A":
            self._move_row(-count)
        elif final == "B":
            self._move_row(count)
        elif final == "C":
            self.x = min(self.columns - 1, self.x + count)
            self.wrap_pending = False
        elif final == "D":
            self.x = max(0, self.x - count)
            self.wrap_pending = False
        elif final == "E":
            self._move_row(count)
            self.x = 0
        elif final == "F":
            self._move_row(-count)
            self.x = 0
        elif final == "G":
            self.x = min(self.columns - 1, max(0, count - 1))
            self.wrap_pending = False
        elif final in {"H", "f"}:
            row = (numbers[0] if len(numbers) > 0 else 0) or 1
            column = (numbers[1] if len(numbers) > 1 else 0) or 1
            self._move_to(row, column)
        elif final == "d":
            self._move_to(first or 1, self.x + 1)
        elif final == "J":
            self._erase_display(first)
        elif final == "K":
            self._erase_line(first)
        elif final == "L":
            self._insert_lines(count)
        elif final == "M":
            self._delete_lines(count)
        elif final == "P":
            self._delete_characters(count)
        elif final == "@":
            self._insert_characters(count)
        elif final == "S":
            self._scroll_up(count)
        elif final == "T":
            self._scroll_down(count)
        elif final == "X":
            self._erase_characters(count)
        elif final in {"h", "l"}:
            self._mode(private, numbers, final == "h")
        elif final == "r":
            top = (numbers[0] if len(numbers) > 0 else 0) or 1
            bottom = (numbers[1] if len(numbers) > 1 else 0) or self.rows
            self._set_scroll_region(top, bottom)
        elif final == "s":
            self._save_cursor()
        elif final == "u":
            self._restore_cursor()
        # SGR, reports, tab stops and cursor style change no visible cell.

    # -- cursor ----------------------------------------------------------

    def _move_row(self, delta):
        low, high = (self.scroll_top, self.scroll_bottom) if self.origin else (0, self.rows - 1)
        self.y = min(high, max(low, self.y + delta))
        self.wrap_pending = False

    def _move_to(self, row, column):
        if self.origin:
            self.y = min(self.scroll_bottom, self.scroll_top + row - 1)
        else:
            self.y = min(self.rows - 1, max(0, row - 1))
        self.x = min(self.columns - 1, max(0, column - 1))
        self.wrap_pending = False

    def _save_cursor(self):
        self.saved = (self.x, self.y, self.wrap_pending)

    def _restore_cursor(self):
        self.x, self.y, self.wrap_pending = self.saved

    def _reset(self):
        self.main = Buffer(self.columns, self.rows)
        self.alternate = Buffer(self.columns, self.rows)
        self.buffer = self.main
        self.x = self.y = 0
        self.wrap_pending = False
        self.saved = (0, 0, False)
        self.scroll_top = 0
        self.scroll_bottom = self.rows - 1
        self.origin = False
        self.autowrap = True
        self._pending = ""

    # -- writing ---------------------------------------------------------

    def _write(self, character):
        size = width(character)
        if size == 0:
            self._combine(character)
            return
        if self.wrap_pending:
            if self.autowrap:
                self._linefeed()
                self.x = 0
            self.wrap_pending = False
        if size == 2 and self.x >= self.columns - 1:
            if self.autowrap:
                self._linefeed()
                self.x = 0
            else:
                self.x = self.columns - 1
        row = self.buffer.cells[self.y]
        row[self.x] = character
        if size == 2:
            row[self.x + 1] = ""
        if self.x + size >= self.columns:
            self.x = self.columns - 1
            self.wrap_pending = True
        else:
            self.x += size

    def _combine(self, character):
        if self.x == 0:
            return
        row = self.buffer.cells[self.y]
        column = self.x - 1
        if row[column] == "":
            column -= 1
        if column >= 0:
            row[column] += character

    def _tab(self):
        for column in range(self.x + 1, self.columns):
            if column in self.tabs:
                self.x = column
                return
        self.x = self.columns - 1

    # -- vertical movement ----------------------------------------------

    def _linefeed(self):
        if self.y == self.scroll_bottom:
            self._scroll_up(1)
        elif self.y < self.rows - 1:
            self.y += 1
        self.wrap_pending = False

    def _index(self):
        self._linefeed()

    def _next_line(self):
        self._linefeed()
        self.x = 0

    def _reverse_index(self):
        if self.y == self.scroll_top:
            self._scroll_down(1)
        elif self.y > 0:
            self.y -= 1
        self.wrap_pending = False

    def _scroll_up(self, count):
        top, bottom = self.scroll_top, self.scroll_bottom
        for _ in range(max(1, min(count, bottom - top + 1))):
            del self.buffer.cells[top]
            self.buffer.cells.insert(bottom, [" "] * self.columns)

    def _scroll_down(self, count):
        top, bottom = self.scroll_top, self.scroll_bottom
        for _ in range(max(1, min(count, bottom - top + 1))):
            del self.buffer.cells[bottom]
            self.buffer.cells.insert(top, [" "] * self.columns)

    def _set_scroll_region(self, top, bottom):
        top = min(max(1, top), self.rows)
        bottom = min(max(1, bottom), self.rows)
        if top >= bottom:
            top, bottom = 1, self.rows
        self.scroll_top, self.scroll_bottom = top - 1, bottom - 1
        self._move_to(1, 1)

    # -- erasing and editing --------------------------------------------

    def _erase_display(self, mode):
        if mode == 0:
            self._erase_line(0)
            for index in range(self.y + 1, self.rows):
                self.buffer.cells[index] = [" "] * self.columns
        elif mode == 1:
            for index in range(0, self.y + 1):
                self.buffer.cells[index] = [" "] * self.columns
            self._erase_line(1)
        else:
            for index in range(self.rows):
                self.buffer.cells[index] = [" "] * self.columns
        self.wrap_pending = False

    def _erase_line(self, mode):
        row = self.buffer.cells[self.y]
        if mode == 0:
            start, end = self.x, self.columns
        elif mode == 1:
            start, end = 0, self.x + 1
        else:
            start, end = 0, self.columns
        for column in range(start, end):
            row[column] = " "
        self.wrap_pending = False

    def _erase_characters(self, count):
        row = self.buffer.cells[self.y]
        for column in range(self.x, min(self.columns, self.x + count)):
            row[column] = " "

    def _insert_characters(self, count):
        row = self.buffer.cells[self.y]
        count = min(count, self.columns - self.x)
        row[self.x:self.x] = [" "] * count
        del row[self.columns:]

    def _delete_characters(self, count):
        row = self.buffer.cells[self.y]
        count = min(count, self.columns - self.x)
        del row[self.x:self.x + count]
        row.extend([" "] * count)

    def _insert_lines(self, count):
        if not self.scroll_top <= self.y <= self.scroll_bottom:
            return
        for _ in range(min(count, self.scroll_bottom - self.y + 1)):
            del self.buffer.cells[self.scroll_bottom]
            self.buffer.cells.insert(self.y, [" "] * self.columns)
        self.x = 0
        self.wrap_pending = False

    def _delete_lines(self, count):
        if not self.scroll_top <= self.y <= self.scroll_bottom:
            return
        for _ in range(min(count, self.scroll_bottom - self.y + 1)):
            del self.buffer.cells[self.y]
            self.buffer.cells.insert(self.scroll_bottom, [" "] * self.columns)
        self.x = 0
        self.wrap_pending = False

    # -- modes -----------------------------------------------------------

    def _mode(self, private, numbers, enabled):
        if private != "?":
            return
        for number in numbers:
            if number == 6:
                self.origin = enabled
                self._move_to(1, 1)
            elif number == 7:
                self.autowrap = enabled
                if not enabled:
                    self.wrap_pending = False
            elif number in {47, 1047, 1049}:
                self._alternate(enabled, number == 1049)
            # 1, 12, 25, 1000-1006, 2004, 2026: no visible cell changes.

    def _alternate(self, enabled, clear):
        if enabled:
            if self.buffer is self.alternate:
                return
            self._save_cursor()
            self.buffer = self.alternate
            self.scroll_top, self.scroll_bottom = 0, self.rows - 1
            if clear:
                self.alternate = Buffer(self.columns, self.rows)
                self.buffer = self.alternate
            self.x = self.y = 0
            self.wrap_pending = False
        else:
            if self.buffer is self.main:
                return
            self.buffer = self.main
            self.scroll_top, self.scroll_bottom = 0, self.rows - 1
            self._restore_cursor()

    # -- resizing --------------------------------------------------------

    def resize(self, columns, rows):
        columns, rows = max(1, int(columns)), max(1, int(rows))
        self.main.resize(columns, rows)
        self.alternate.resize(columns, rows)
        self.columns, self.rows = columns, rows
        self.tabs = set(range(8, self.columns, 8))
        self.scroll_top, self.scroll_bottom = 0, self.rows - 1
        self.x = min(self.x, self.columns - 1)
        self.y = min(self.y, self.rows - 1)
        self.wrap_pending = False
