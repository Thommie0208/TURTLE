import numpy as np
import os

base_dir = os.path.dirname(__file__)
grey_value = 86

def find_pixel(filename: str) -> str:
    higher_than_grey = True
    pixel_list: list[float] = [] #Pixel index is list index
    pixels_at_grey: list[float] = []
    distances: list[float] = []
    with open(filename) as f:
        for line in f:
            line = line.strip().split(',')
            match line:
                case x, y if x.isdigit():
                    pixel_list.append(float(y))
    for i in range(len(pixel_list)):
        if pixel_list[i] < grey_value and higher_than_grey:
            pixels_at_grey.append(interpolate((i - 1), i, pixel_list[i - 1], pixel_list[i]))
            higher_than_grey = False
        elif pixel_list[i] > grey_value and not higher_than_grey:
            pixels_at_grey.append(interpolate((i - 1), i, pixel_list[i - 1], pixel_list[i]))
            higher_than_grey = True
    for j in range(1, len(pixels_at_grey), 2):
        diff = pixels_at_grey[j] - pixels_at_grey[j -1]
        distances.append(diff)
        print(f"{diff:.4f}")
    return f"{(np.mean(np.array(distances))):.2f}"

def interpolate(x1: int, x2: int, y1: float, y2: float) -> float:
    rc = (x2 - x1)/(y2 - y1)
    return rc * (grey_value - y1) + x1

print(find_pixel(os.path.join(base_dir, f"USAF test map\\Sample 5\\Group 6 Element 1 (vert).csv"))) #Relies on a highly specific file structure where the USAF test map is in the same folder as this script