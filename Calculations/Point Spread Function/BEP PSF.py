import inspect
import numpy as np
import matplotlib.pyplot as pyplot
from scipy.optimize import curve_fit
from scipy.signal import find_peaks, peak_widths
import microscPSF.microscPSF as msPSF
print(f'packages are imported')

# Microscope parameters.
m_params = {"M" : 200/18,                   # magnification
            "NA" : 0.3,                 # numerical aperture
            "ng0" : 1.52,               # coverslip RI design value
            "ng" : 1.52,                # coverslip RI experimental value
            "ni0" : 1,                  # immersion medium RI design value    medium between coverslip and objective
            "ni" : 1,                   # immersion medium RI experimental value
            "ns" : 1.33,                # specimen refractive index (RI)    water
            "ti0" : 10000,              # microns, working distance (immersion medium thickness) design value     just the working distance
            "tg" : 170,                 # microns, coverslip thickness experimental value
            "tg0" : 170,                # microns, coverslip thickness design value
            "zd0" : 200 * 1.0e+3,       # microscope tube length (in microns)
            "pixel_camera" : 2.4}       #pixel size of the camera  


# You can find more information about what these are in this file:
# print(inspect.getfile(msPSF))

# We'll use this for drawing PSFs.
#
# Note that we display the sqrt of the PSF.
#
def psfSlicePics(psf, sxy, sz, zvals, pixel_size = m_params["pixel_camera"]/m_params["M"]):
    ex = pixel_size * 0.5 * psf.shape[1]

    fig = pyplot.figure(figsize = (12,4))
    ax1 = fig.add_subplot(1,3,1)
    ax1.imshow(np.sqrt(psf[sz,:,:]),
               interpolation = 'none', 
               extent = [-ex, ex, -ex, ex],
               cmap = "gray")
    ax1.set_title("PSF XY slice")
    ax1.set_xlabel(r'x, $\mu m$')
    ax1.set_ylabel(r'y, $\mu m$')

    ax2 = fig.add_subplot(1,3,2)
    ax2.imshow(np.sqrt(psf[:,:,sxy]),
               interpolation = 'none',
               extent = [-ex, ex, zvals.max(), zvals.min()],
               cmap = "gray")
    ax2.set_title("PSF YZ slice")
    ax2.set_xlabel(r'y, $\mu m$')
    ax2.set_ylabel(r'z, $\mu m$')

    # ax3 = fig.add_subplot(1,3,3)
    # ax3.imshow(np.sqrt(psf[:,sxy,:]), 
    #            interpolation = 'none',
    #            extent = [-ex, ex, zvals.max(), zvals.min()],
    #            cmap = "gray")
    # ax3.set_title("PSF XZ slice")
    # ax3.set_xlabel(r'x, $\mu m$')
    # ax3.set_ylabel(r'z, $\mu m$')

    pyplot.show()

# Radial PSF
mp = m_params
pixel_size = m_params["pixel_camera"]/m_params["M"]
rv = np.arange(0.0, 10.01, pixel_size)
zv = np.arange(-40, 40.01, pixel_size)
x_steps = len(rv)
z_steps = len(zv)
psf_zr = msPSF.gLZRFocalScan(mp, rv, zv, 
                             pz = 0.1,       # Particle 0.1um above the surface.
                             wvl = 0.7,      # Detection wavelength.
                             zd = mp["zd0"]) # Detector exactly at the tube length of the microscope.

fig, ax = pyplot.subplots()

ax.imshow(np.sqrt(psf_zr),
          extent=(rv.min(), rv.max(), zv.max(), zv.min()),
          cmap = 'gray')
ax.set_xlabel(r'r, $\mu m$')
ax.set_ylabel(r'z, $\mu m$')

pyplot.show()

# XYZ PSF
psf_xyz = msPSF.gLXYZFocalScan(mp, pixel_size, x_steps, zv, pz = 0.0)    #data for graphs
# print(psf_xyz)

psfSlicePics(psf_xyz, x_steps//2, z_steps//2, zv)

#data for normal distribution
data_XY = psf_xyz[z_steps//2,:,:]
length_data = len(data_XY)
midplane = int(length_data/2)
x_range_min = -5
x_range_max = 5.01
stepsize = (x_range_max - x_range_min)/len(data_XY[midplane])
x_range = np.arange(x_range_min, x_range_max, stepsize)

#Curve fit
def Gauss(x, A, B, mu):
    return A * np.exp(-B * (x-mu)**2)

parameters, _ = curve_fit(Gauss, x_range, data_XY[midplane])
fit_A, fit_B, fit_mu = parameters
fit_y = Gauss(x_range, fit_A, fit_B, fit_mu)

#Calculating the FWHM
index_peak = find_peaks(fit_y, height=0.5)   #index and height of the peak
Width_info = peak_widths(fit_y, [index_peak[0][0]], rel_height = 0.5)   #width and the heigth at which is measured
FWHM_array = (Width_info[3] - Width_info[2]) * stepsize
FWHM = FWHM_array[0]

#plotting the graph
pyplot.plot(x_range, data_XY[midplane])
pyplot.plot(x_range, fit_y)
pyplot.xlabel(f'x, micrometer')
pyplot.xticks(np.arange(-5, 6, 1))
pyplot.show

print(f'FWHM = {FWHM} micrometer')
