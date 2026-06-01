import os
import glob
import cv2
from stitch2d import StructuredMosaic
def stitch(path, tiles, output, extension):
    # change only this block
    folder = path

    tiles_x, tiles_y = tiles

    file_extension = extension

    snake_pattern = False

    overlap_x = 0.10
    overlap_y = 0.10

    output_name = output

    # CHECK IMAGES
    image_paths = sorted(glob.glob(os.path.join(folder, f"*.{file_extension}")))

    expected_number = tiles_x * tiles_y

    print(f"Found {len(image_paths)} images.")
    print(f"Expected {expected_number} images.")

    if len(image_paths) != expected_number:
        raise ValueError(
            f"Wrong number of images. Check tiles_x, tiles_y, folder, or file_extension. Expected amount: {expected_number}. Found number: {len(image_paths)}"
        )

    first_image = cv2.imread(image_paths[0])

    if first_image is None:
        raise ValueError("Could not read the first image.")

    height, width = first_image.shape[:2]

    print(f"Image size: {width} x {height}")

    # CALCULATE TILE SPACING FROM OVERLAP
    step_x = int(width * (1 - overlap_x))
    step_y = int(height * (1 - overlap_y))

    print(f"Step x: {step_x} pixels")
    print(f"Step y: {step_y} pixels")

    # CREATE MOSAIC
    pattern = "snake" if snake_pattern else "raster"

    mosaic = StructuredMosaic(
        folder,
        dim=tiles_x,
        origin="upper left",
        direction="horizontal",
        pattern=pattern
    )

    # BUILD MOSAIC FROM KNOWN OVERLAP
    # -------------------------------------------------------------------------
    # Stitch2D wants offsets in this order:
    # dy_row = vertical movement when going one row down
    # dx_row = horizontal movement when going one row down
    # dy_col = vertical movement when going one column right
    # dx_col = horizontal movement when going one column right
    offsets = (
        step_y,  # dy_row
        0,       # dx_row
        0,       # dy_col
        step_x   # dx_col
    )

    mosaic.build_out(from_placed=False, offsets=offsets)

    # SMOOTH SEAMS AND SAVE
    print("Smoothing seams...")
    mosaic.smooth_seams()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_name)

    print("Saving mosaic...")
    mosaic.save(output_path)

    print("Saved mosaic to:")
    print(output_path)
