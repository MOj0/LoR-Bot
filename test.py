import win32api
from time import sleep
from random import uniform

#TODO: Implement this in the Bot!

def easeInOutQuad(t):
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2


def move_line_s(x1, y1, n):
    x0, y0 = win32api.GetCursorPos()
    dx, dy = x1 - x0, y1 - y0

    for i in range(n):
        t = easeInOutQuad(i / n)
        win32api.SetCursorPos((int(x0 + dx * t), int(y0 + dy * t)))
        sleep(0.0001)

for _ in range(100):
    x, y = int(uniform(0, 1920)) ,int(uniform(-1080, 1080))
    move_line_s(x, y, 50)
