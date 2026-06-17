import numpy as np
import os

base_dir = os.path.dirname(__file__)

def readfile(filename: str) -> list[float]:
    pixel_list: list[float] = []
    with open(filename) as f:
        for line in f:
            line = line.strip().split(',')
            # print(line)
            match line:
                case x, y if x.isdigit():
                    pixel_list.append(float(y))
    return pixel_list

def find_min_max(pixels: list[float]) -> tuple[list[float], list[float]]:
    minimums: list[float] = []
    maximums: list[float] = []
    going_down = True
    start, end = find_starting_value(pixels), find_ending_value(pixels)
    # print(start, end)
    for i in range(start, end):
        if pixels[i] < pixels[i - 1] and not going_down:
            maximums.append(pixels[i - 1])
            going_down = True
        elif pixels[i] > pixels[i - 1] and going_down:
            minimums.append(pixels[i - 1])
            going_down = False
    return minimums, maximums

def find_starting_value(pixels: list[float]) -> int:
    for i in range(1, len(pixels)):
        # print(pixels[i])
        if pixels[i] < pixels[i - 1]:
            return i
    return -1

def find_ending_value(pixels: list[float]) -> int:
    for i in range(len(pixels) - 1, 0, -1):
        if pixels[i - 1] < pixels[i]:
            return i
    return -1

def find_ratio(minimums: list[float], maximums: list[float]) -> bool:
    valid_ratio = False
    # print(minimums, maximums)
    if len(maximums) < 2 or len(minimums) < 3:
        return False
    for i in range(len(minimums)):
        if i == 0:
            minimum, maximum = minimums[0], maximums[0]
        elif i == 1: 
            minimum, maximum = minimums[1], min(maximums[0], maximums[1])
        elif i == 2:
            minimum, maximum = minimums[2], maximums[1]
        else:
            pass
        # print(maximum, minimum)
        ratio = (maximum - minimum)/maximum
        # print(ratio)
        if ratio > criteria:
            valid_ratio = True
        else:
            pass
    return valid_ratio


criteria = 0.263
for sample in range(1, 6):
    group8_elem5_hor = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 8 Element 5 (hor).csv"))
    group8_elem5_vert = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 8 Element 5 (vert).csv"))
    group8_elem6_hor = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 8 Element 6 (hor).csv"))
    group8_elem6_vert = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 8 Element 6 (vert).csv"))
    group9_elem1_hor = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 9 Element 1 (hor).csv"))
    group9_elem1_vert = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 9 Element 1 (vert).csv"))
    group9_elem2_hor = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 9 Element 2 (hor).csv"))
    group9_elem2_vert = readfile(os.path.join(base_dir, f"USAF test map\\Sample {sample}\\Group 9 Element 2 (vert).csv"))

    groups = [group8_elem5_hor, group8_elem5_vert, group8_elem6_hor, group8_elem6_vert, group9_elem1_hor, group9_elem1_vert, group9_elem2_hor, group9_elem2_vert]
    for group in groups:
        mini, maxi = find_min_max(group)
        if find_ratio(mini, maxi):
            print(f"Sample {sample} is resolvable for group {groups.index(group)}")
        else:
            print(f"Sample {sample} is NOT resolvable for group {groups.index(group)}")
    print("")