import numpy as np

grey_value = 93

def find_pixel(filename: str) -> float:
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
        distances.append(pixels_at_grey[j] - pixels_at_grey[j -1])
    return float(np.mean(np.array(distances)))

def interpolate(x1: int, x2: int, y1: float, y2: float) -> float:
    rc = (x2 - x1)/(y2 - y1)
    return rc * (grey_value - y1) + x1

print(find_pixel(r"C:\Users\name\Downloads\Group 6 Element 1 (hor).csv"))