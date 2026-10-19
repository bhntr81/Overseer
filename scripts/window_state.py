"""Change only taskbar/pager visibility through the desktop's X11 protocol."""
import ctypes as c


def hide_from_switchers(window, hidden):
    lib = c.CDLL('libX11.so.6')
    lib.XOpenDisplay.argtypes = [c.c_char_p]
    lib.XOpenDisplay.restype = c.c_void_p
    lib.XDefaultRootWindow.argtypes = [c.c_void_p]
    lib.XDefaultRootWindow.restype = c.c_ulong
    lib.XInternAtom.argtypes = [c.c_void_p, c.c_char_p, c.c_int]
    lib.XInternAtom.restype = c.c_ulong
    lib.XSendEvent.argtypes = [c.c_void_p, c.c_ulong, c.c_int, c.c_long, c.c_void_p]
    lib.XFlush.argtypes = [c.c_void_p]
    lib.XCloseDisplay.argtypes = [c.c_void_p]
    class Message(c.Structure):
        _fields_ = [('type', c.c_int), ('serial', c.c_ulong), ('send_event', c.c_int),
                    ('display', c.c_void_p), ('window', c.c_ulong), ('message_type', c.c_ulong),
                    ('format', c.c_int), ('data', c.c_long * 5)]
    class Event(c.Union):
        _fields_ = [('message', Message), ('pad', c.c_long * 24)]
    display = lib.XOpenDisplay(None)
    if not display:
        raise RuntimeError('X11 display unavailable')
    try:
        event = Event()
        msg = event.message
        msg.type, msg.send_event, msg.display = 33, 1, display
        msg.window = int(window, 0)
        msg.message_type = lib.XInternAtom(display, b'_NET_WM_STATE', 0)
        msg.format = 32
        msg.data[:] = [int(hidden), lib.XInternAtom(display, b'_NET_WM_STATE_SKIP_TASKBAR', 0),
                       lib.XInternAtom(display, b'_NET_WM_STATE_SKIP_PAGER', 0), 1, 0]
        lib.XSendEvent(display, lib.XDefaultRootWindow(display), 0, (1 << 19) | (1 << 20), c.byref(event))
        lib.XFlush(display)
    finally:
        lib.XCloseDisplay(display)
