"""
Module defines functions and methods to analyse bead samples images to extract PSF information. Images can be 2D or 3D
(zstack) data. IN the latter case, a basic autofocus algorithm is used to find the plane of focus. Beads are assumed
to lie on a common plane of focus (this is true for beads of a cover slip samples, not true for beads in agarose gel).

All data is assumed to follow the index convention: (plane, row, column) or (row, column).
"""
import time
from itertools import count

import lmfit.models
import numpy as np

from tqdm.auto import tqdm


def autofocus(data, verbose=True):
    """
    Returns the index of the image plane where the FFT annulus integral is maximised. This should be the plane of focus.
    :param data: 3D dataset. Indices (plane, row, column)
    :param verbose: if True (default) displays progress bar.
    :return: index of plane of focus.
    """
    from OpticsLabMethods.image_metrics import fft_annulus
    metric = [0.0] * data.shape[0]

    z_range = range(data.shape[0])
    if verbose:
        tqdm(z_range, desc="Autofocus", total=data.shape[0])

    for i in z_range:
        metric[i] = fft_annulus(data[i])

    i = np.argmin(metric)

    return data[i], i


def segment_beads(image, threshold='Otsu', small_object_size=10, morphology_footprint=3, max_merge_distance=5):
    """
    Returns the label image and region properties of segmented regions. This function implements a 'blob detection'
    algorithm, the image is assumed to contain bright blobs (such as fluorescent beads).
    :param image: 2D image of fluorescent beads.
    :param threshold: int or str, value to be used for thresholding the background. If set to 'Otsu' (default), Otsu's
                    algorithm is used.
    :param small_object_size: int, segmented regions that have an area smaller that this value (in pixels) are removed.
                                This is used to remove small noisy regions that survive thresholding.
    :param morphology_footprint: int or 2D array. Footprint to be used for morphology operations. By default, a 3x3
                                square is used, however, different connectivity footprint can alter the results. See
                                skimage documentation for details.
    :param max_merge_distance: int, regions with centroids closer than this value will be merged.
    :return: label image (2D np.array) and region properties (list) of segmented regions.
    """
    from skimage.filters import threshold_otsu
    from skimage.morphology import remove_small_objects, remove_small_holes
    from scipy import ndimage as ndi
    from skimage.feature import peak_local_max
    from skimage.segmentation import watershed
    from skimage.measure import regionprops

    # sanitise inputs
    if image.ndim > 2:
        raise ValueError(f"Image should be 2D data, got {image.ndim}-D.")

    if threshold == "Otsu" or threshold == "otsu":
        threshold = threshold_otsu(image)

    threshold = int(threshold)

    if isinstance(morphology_footprint, int):
        morphology_footprint = np.ones((morphology_footprint, morphology_footprint))

    morphology_footprint = np.atleast_2d(morphology_footprint)

    # start processing
    binary = image >= threshold

    binary = remove_small_objects(binary, min_size=small_object_size)
    binary = remove_small_holes(binary, small_object_size)

    distance = ndi.distance_transform_edt(binary)

    # we use the 'distance transform' to find the pixel that are furthers from the background and used those as starting
    # 'sources' in the watershed segmentation.
    coords = peak_local_max(distance, footprint=morphology_footprint, labels=binary)

    # this defines the pixels that are used as 'sources of water' in the watershed algorithm
    mask = np.zeros(distance.shape, dtype=bool)
    mask[tuple(coords.T)] = True

    markers, _ = ndi.label(mask)

    # the 'distance' image is used as morphology map for the watershed, 'markers' are the sources of water and the mask
    # 'binary' ensure that we stop the segmentation where the background starts.
    labels = watershed(-distance, markers, mask=binary)

    # measure region properties using the segmented labels but the original image as intensity map.
    regions = regionprops(labels, intensity_image=image)

    # merge regions that have centroids closer than max_merge_distance
    coordinates = [reg.centroid for reg in regions]
    coordinates = np.array(coordinates, dtype=float)

    for i, reg in enumerate(regions):
        distances = np.array([max(abs(c - coordinates[i])) for c in coordinates])

        mask = (distances < max_merge_distance)
        indices = mask.nonzero()[0]

        # set the labels of the regions that are too close to be the same as the label of this region
        for j in indices:
            labels[labels == regions[j].label] = reg.label

    # execute again regionprops (with new label values)
    regions = regionprops(labels, intensity_image=image)

    return labels, regions


def find_beads_bbox(regions, safety_factor=0.75, size_threshold=15, same_size=False):
    """
    Computes the largest square box around each bead such that only that bead is contained in the square.
    :param regions: region properties, from skimage.measure.regionprops()
    :param safety_factor: float less than 1, reduces the size of the bounding box by this factor to ensure that the tail
                        of one bead does not 'bleed' into the bbox of another bead.
    :param size_threshold: int, bboxes that have a smaller edge length than this value (in pixels) will be excluded.
                        This allows to exclude beads that are very close to each other. Set to 0 to include all.
    :param same_size: if False (default), each bead will have a smaller or large bbox depending on the distances with
                    other beads. If True, the smallest of all boxes is used for all beads.
    :return: coordinates and box sizes for each region.
    """
    coordinates = [reg.centroid for reg in regions]
    coordinates = np.array(coordinates, dtype=float)

    # For each bead measure the distance to all other beads and find the closest.
    # Use this to define a box that contains a single bead.
    max_box_sizes = [0.0] * len(coordinates)
    for i, coord in enumerate(coordinates):
        distances = [max(abs(c - coord)) for c in coordinates]
        # the i-th position is always zero since it corresponds to this bead
        distances[i] = np.inf

        # reduce the box size by 'safety_factor' since beads will defocus and expand outside the plane of focus
        max_box_sizes[i] = 2 * np.min(distances) * safety_factor

    if size_threshold:
        mask = [size >= size_threshold for size in max_box_sizes]

        coordinates = [c for c, m in zip(coordinates, mask) if m]
        max_box_sizes = [s for s, m in zip(max_box_sizes, mask) if m]

    if same_size:
        size = np.min(max_box_sizes)

        max_box_sizes = [size] * len(max_box_sizes)

    return coordinates, max_box_sizes


def extract_psfs(data, coordinates, bboxes):
    """
    Extracts images of individual beads.
    :param data: image data. Either 2D or 3D.
    :param coordinates: list of beads centre coordinates
    :param bboxes: list of bounding boxes size for each bead. The smallest box will be used for all beads.
    :return: list of np.array.
    """
    if data.ndim not in [2, 3]:
        raise ValueError(f"Data should be 2D or 3D array, got {data.ndim}-D.")

    sub_images = []

    bboxes = [int(s) for s in bboxes]

    for i, (cy, cx), size in zip(count(), coordinates, bboxes):
        y0 = int(cy - size / 2)
        x0 = int(cx - size / 2)

        slc = slice(y0, y0 + size), slice(x0, x0 + size)

        if data.ndim == 3:
            img = data[:, *slc]
        else:
            img = data[*slc]

        sub_images.append(img)

    return sub_images


def average_psf(data, coordinates, bboxes):
    """
    Averages the image of multiple beads by overlapping data from each bead bounding box and summing them together.
    :param data: image data. Either 2D or 3D.
    :param coordinates: list of beads centre coordinates
    :param bboxes: list of bounding boxes size for each bead. The smallest box will be used for all beads.
    :return: np.array same dimensions as input. Averaged psf image.
    """
    if data.ndim not in [2, 3]:
        raise ValueError(f"Data should be 2D or 3D array, got {data.ndim}-D.")

    # ensure we use the smaller bounding box
    size = int(min(bboxes))
    bboxes = [size] * len(bboxes)

    sub_images = extract_psfs(data, coordinates, bboxes)

    avg_psf = sum(sub_images) // len(sub_images)

    return avg_psf


def analyse_psf(data, psf_size_guess=10, method='hybrid'):
    """
    Measures the PSF FWHM from a 2D or 3D image of a single bead.
    :param data: 2D or 3D np.array. Image of a single bead.
    :param psf_size_guess: size guess in pixel to be used as initial estimate of the psf.
    :param method: either '1D', 'Hybrid', or '3D'.
        If '1D' a 1D Gaussian fit along the x,y,z axes is used. This is quick and easy, but only works if there are no
        tilts in the PSF, as each axis is considered independently.
        IF '3D' a 3D Gaussian model is fitted on the whole zstack. Note data must be 3D.
        if 'Hybrid', a 2D Gaussian is used to fit the focal plane and estimate FWHM along x and y. A 1D Gaussian is used
        for the z direction (if data is 3D). Like the '1D' case, if the PSF presents tilting the result may be wrong.
    :return: lmfit parameter object.
    """
    if data.ndim not in [2, 3]:
        raise ValueError(f"Data should be 2D or 3D. Got {data.ndim}-D.")

    if data.ndim != 3 and method.lower() == '3d':
        raise ValueError(f"To fit a 3D model data must be 3D. Got {data.ndim}-D.")

    if method.lower() == '1d':
        return _analyse_psf_1d(data, psf_size_guess)
    elif method.lower() == 'hybrid':
        return _analyse_psf_hybrid(data, psf_size_guess)
    elif method.lower() == '3d':
        return _analyse_psf_3d(data, psf_size_guess)
    else:
        raise ValueError(f"Unknown method: {method}.")


def analyse_multi_psf(datasets, psf_size_guess=10, method='hybrid'):
    return [analyse_psf(data, psf_size_guess, method) for data in datasets]


# METHODS
def _analyse_psf_1d(data, psf_size_guess=10):
    raise NotImplementedError()


def _analyse_psf_hybrid(data, psf_size_guess=10):
    # Find approximate bead centre.
    # If data is 3D we extract the plane where the maximum is located and continue with 2D fit
    max_indices = np.unravel_index(np.argmax(data), data.shape)
    z0 = 0

    # 2D analysis of focus plane
    data_2d = data.copy()

    if data.ndim == 3:
        z0, max_indices = max_indices[0], max_indices[1:]
        data_2d = data[z0]

    x = np.arange(data.shape[-1])
    y = np.arange(data.shape[-2])
    Y, X = np.meshgrid(y, x, indexing='ij')

    model = lmfit.Model(_gaussian_2d, independent_vars=['x', 'y']) + lmfit.models.ConstantModel()
    params = model.make_params()

    params['amplitude'].set(value=data_2d.max() - data_2d.mean(), min=0)
    params['centerx'].set(value=max_indices[-1], min=0)
    params['centery'].set(value=max_indices[-2], min=0)
    params['sigmax'].set(value=psf_size_guess, min=0)
    params['sigmay'].set(value=psf_size_guess, min=0)
    params['c'].set(value=data_2d.mean(), min=0)

    res_2d = model.fit(data_2d.ravel(), x=X.ravel(), y=Y.ravel(), params=params)

    # if the data is 3D we also do a 1D fit along z
    if data.ndim == 3:
        x0 = round(res_2d.best_values["centerx"])
        y0 = round(res_2d.best_values["centery"])

        z = np.arange(data.shape[0])

        signal = data[:, y0, x0]

        model = lmfit.models.GaussianModel() + lmfit.models.ConstantModel()
        params = model.make_params()

        params['amplitude'].set(value=signal.max(), min=0)
        params['center'].set(value=z0, min=0)
        params['sigma'].set(value=psf_size_guess, min=0)
        params['c'].set(value=signal.mean(), min=0)

        res_z = model.fit(signal, x=z, params=params)

        # build the 3D model parameters and return those
        params3d = res_2d.params

        # rename z-parameters
        res_z.params['center'].name = 'centerz'
        params3d.add(res_z.params['center'])

        res_z.params['sigma'].name = 'sigmaz'
        params3d.add(res_z.params['sigma'])

        return params3d

    return res_2d.params


def _analyse_psf_3d(data, psf_size_guess=10):
    # Find approximate bead centre.
    # If data is 3D we extract the plane where the maximum is located and continue with 2D fit
    max_indices = np.unravel_index(np.argmax(data), data.shape)

    x = np.arange(data.shape[2])
    y = np.arange(data.shape[1])
    z = np.arange(data.shape[0])

    Z, Y, X = np.meshgrid(z, y, x, indexing='ij')

    model = lmfit.Model(_gaussian_3d, independent_vars=['x', 'y', 'z']) + lmfit.models.ConstantModel()
    params = model.make_params()

    params['amplitude'].set(value=data.max(), min=0)
    params['centerx'].set(value=max_indices[2], min=0)
    params['centery'].set(value=max_indices[1], min=0)
    params['centerz'].set(value=max_indices[0], min=0)
    params['sigmax'].set(value=psf_size_guess, min=0)
    params['sigmay'].set(value=psf_size_guess, min=0)
    params['sigmaz'].set(value=psf_size_guess, min=0)
    params['c'].set(value=data.mean(), min=0)

    res = model.fit(data.ravel(), x=X.ravel(), y=Y.ravel(), z=Z.ravel(), params=params)
    return res.params


def _gaussian(x, amplitude, centre, sigma):
    return amplitude * np.exp(-0.5 * (x-centre)**2/sigma**2)


def _gaussian_2d(x, y, amplitude, centerx, centery, sigmax, sigmay):
    return amplitude * _gaussian(x, 1.0, centerx, sigmax) * _gaussian(y, 1.0, centery, sigmay)


def _gaussian_3d(x, y, z, amplitude, centerx, centery, centerz, sigmax, sigmay, sigmaz):
    return (amplitude *
            _gaussian(x, 1.0, centerx, sigmax) *
            _gaussian(y, 1.0, centery, sigmay) *
            _gaussian(z, 1.0, centerz, sigmaz))


def plot_psf_slice(data, fit_params, slice_axes="xy"):
    import matplotlib.pyplot as plt

    if 'z' in slice_axes.lower() and data.ndim !=3:
        raise ValueError(f"Attempting to performa a {slice_axes} slice of 2D data. Use slice='xy' in this case.")

    # Prep model data
    x = np.arange(data.shape[-1])
    y = np.arange(data.shape[-2])

    if data.ndim == 2:
        Y, X = np.meshgrid(y, x, indexing='ij')

        model = lmfit.Model(_gaussian_2d, independent_vars=['x', 'y']) + lmfit.models.ConstantModel()
        fit = model.eval(fit_params, x=X, y=Y)

    else:
        z = np.arange(data.shape[0])

        Z, Y, X = np.meshgrid(z, y, x, indexing='ij')

        model = lmfit.Model(_gaussian_3d, independent_vars=['x', 'y', 'z']) + lmfit.models.ConstantModel()
        fit = model.eval(fit_params, x=X, y=Y, z=Z)

    # define ax labels and slicing indices based on the slice argument
    if slice_axes.lower() == 'xy' or slice_axes.lower() == 'yx':
        xlabel = 'x'
        ylabel = 'y'

        if data.ndim == 2:
            slc = [
                [slice(None), slice(None)],
                [int(fit_params["centery"].value), slice(None)],
                [slice(None), int(fit_params["centerx"].value)],
            ]
        else:
            slc = [
                [int(fit_params["centerz"].value), slice(None), slice(None)],
                [int(fit_params["centerz"].value), int(fit_params["centery"].value), slice(None)],
                [int(fit_params["centerz"].value), slice(None), int(fit_params["centerx"].value)],
            ]

        vertical_plot_y = x

    elif slice_axes.lower() == 'zx' or slice_axes.lower() == 'xz':
        xlabel = 'x'
        ylabel = 'z'

        slc = [
            [slice(None), int(fit_params["centery"].value), slice(None)],
            [int(fit_params["centerz"].value), int(fit_params["centery"].value), slice(None)],
            [slice(None), int(fit_params["centery"].value), int(fit_params["centerx"].value)],
        ]

        vertical_plot_y = z

    elif slice_axes.lower() == 'yz' or slice_axes.lower() == 'zy':
        xlabel = 'y'
        ylabel = 'z'

        slc = [
            [slice(None), slice(None), int(fit_params["centerx"].value)],
            [int(fit_params["centerz"].value), slice(None), int(fit_params["centerx"].value)],
            [slice(None), int(fit_params["centery"].value), int(fit_params["centerx"].value)],
        ]

        vertical_plot_y = z

    else:
        raise ValueError(f"Unknown slice axes {slice_axes}. Use 'xy', 'yz', or 'zx'.")

    # prepare gridspec plot
    fig = plt.figure(figsize=(10, 10))

    gs = fig.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
                          left=0.1, right=0.9, bottom=0.1, top=0.9,
                          wspace=0.05, hspace=0.05)
    # Create the Axes.
    ax = fig.add_subplot(gs[1, 0])
    ax_x = fig.add_subplot(gs[0, 0], sharex=ax)
    ax_y = fig.add_subplot(gs[1, 1], sharey=ax)

    ax_x.tick_params(axis="x", labelbottom=False)
    ax_y.tick_params(axis="y", labelleft=False)

    ax.set(xlabel=f"{xlabel} [px]", ylabel=f"{ylabel} [px]")
    ax_x.set(ylabel="Intensity [a.u.]")
    ax_y.set(xlabel="Intensity [a.u.]")

    # 2D central image
    ax.imshow(data[*slc[0]], cmap="Grays", aspect="auto")
    ax.contour(fit[*slc[0]])

    # Line across X (centre of psf)
    ax_x.plot(data[*slc[1]], ls='', marker='.')
    ax_x.plot(fit[*slc[1]], ls='-')

    # Line across Y (centre of psf)
    ax_y.plot(data[*slc[2]], vertical_plot_y, ls='', marker='.')
    ax_y.plot(fit[*slc[2]], vertical_plot_y, ls='-')

    return fig, [ax, ax_x, ax_y]




