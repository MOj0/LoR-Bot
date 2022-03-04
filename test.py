import numpy as np
import cv2 as cv
from matplotlib import pyplot as plt
import masks

img = cv.imread('0.png', 0)  # 0 - grayscale
plt.subplot(121), plt.imshow(img, cmap='gray')
plt.title('Original Image'), plt.xticks([]), plt.yticks([])
edges = cv.Canny(img, 100, 100)
plt.subplot(122), plt.imshow(edges, cmap='gray')
plt.title('Edge Image'), plt.xticks([]), plt.yticks([])

for edge in edges:
    print(repr(edge))

# TODO: Use this technique in LOR_Bot.py
mask = masks.ZERO
num_mask_px = sum((val for line in mask for val in line))
num_match_px = sum(map(bool, (val for e, z in zip(edges, mask) for val in e[z])))
print(num_match_px, "/", num_mask_px)

plt.show()
