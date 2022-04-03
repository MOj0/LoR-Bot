import win32api
import win32con
from time import sleep


class MouseHandler:
    def __init__(self, smooth_factor=40, sleep_duration=0.01) -> None:
        self.smooth_factor = smooth_factor
        self.sleep_duration = sleep_duration

    def easeInOutQuad(self, t):
        return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2

    def move_mouse_smooth(self, x1, y1):
        x0, y0 = win32api.GetCursorPos()
        dx, dy = x1 - x0, y1 - y0

        for i in range(self.smooth_factor):
            t = self.easeInOutQuad(i / self.smooth_factor)
            win32api.SetCursorPos((int(x0 + dx * t), int(y0 + dy * t)))
            sleep(self.sleep_duration)

        return True

    def click(self, pos, y=None):
        if y is not None:
            x = pos
        else:
            (x, y) = pos

        x, y = int(x), int(y)
        if self.move_mouse_smooth(x, y):  # Wait for the move to finish
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def hold(self, pos, y=None):
        if y is not None:
            x = pos
        else:
            (x, y) = pos

        x, y = int(x), int(y)
        if self.move_mouse_smooth(x, y):  # Wait for the move to finish
            sleep(0.1)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)

    def release(self, pos, y=None):
        if y is not None:
            x = pos
        else:
            (x, y) = pos

        x, y = int(x), int(y)
        if self.move_mouse_smooth(x, y):  # Wait for the move to finish
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
