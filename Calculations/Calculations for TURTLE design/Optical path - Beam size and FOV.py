import numpy as np
### General Information
# As the mirrors need to be put at an angle, one side will have a shortened projection, which we will call the width, 
# while the other direction remains unchanged, this will be the height. The optical area of camera's is not sqaure, but rectangular.
# The largest side of the optical area, will be called the height, and the smaller side the width.
# In order to get the biggest FOV, the height of the mirror and of the optical area should be alligned.

### Variables
#camera
pixles = np.array([3072, 2048])     #... - The resolution of the camera as in ... x ... (the order of input does not matter) (800 x 600)(1456 x 1088)(lab: 2056 x 1542, IDS: UI-3070CP Rev. 2)(UC2: 3072 x 2048, hikrobot: mv-cs060-10uc-pro)
pixle_size = 2.4                  #micrometer - The pixle size of the camera (4.8)(3.45)(lab: 3.45, IDS: UI-3070CP Rev. 2)(UC2: 2.4, hikrobot: mv-cs060-10uc-pro)

#lenses
M_obj = 10          #... - Magnification of the objective (4)(10)
NA_obj = 0.3       #... - Numerical aperature of the objective (0.13)(0.3)
WD_obj = 9         #mm - Working distance of the objective (17)(9)
f_tube_corr = 180   #mm - Focal length of the corresponding tube lens (the tube lens from the same company as the objective)
f_imaging = 200     #mm - Effective focal length of the imaging lens (most commonly an achromatic doublet or a tube lens)
d_imaging = 25      #mm - Diameter of the imaging lens (most commonly an achromatic doublet or a tube lens)
f_ach_l_shape = 150 #mm - Effective focal length of the lens used for focusing the expanded laser beam onto the objective back focal point
f_asp_l_shape = 10  #mm - Focal length of the lens used to focus the laser beam into the optical fiber

#filters
d_f = 22            #mm - clear aperature of the filter

#mirrors
h_m = 25            #mm - Height of the second mirror (eliptical)
w_m = 36            #mm - Width of the second mirror (eliptical)
h_mg = 1            #mm - Gasket height on the mirror
w_mg = 1            #mm - Gasket width on the mirror
h_dich = 36         #mm - Dichroic mirror height
w_dich = 25         #mm - Dichroic mirror width
t_dich = 3          #mm - Dichroic mirror thickness
refr_dich = 1.52    #... = Refractive index of the dichroic (1.52 for low-autofluorescence optical quality glass)
h_dg = 1            #mm - Gasket height on the dichroic
w_dg = 1            #mm - Gasket width on the dichroic

#distances between optical components
L_1 = 76        #mm - Distance between the objective and the midpoint of the first mirror
L_dich = 43     #mm - Distance between the midpoint of the first mirror and the midpoint of the dichroic mirror
L_2 = 90        #mm - Distance between the midpoint of the first mirror and the midpoint of the second mirror
L_f = 25        #mm - Distance between the midpoint of the second mirror and the emission filter
L_3 = 40        #mm - Distance between the midpoint of the second mirror and the imaging lens

#lasers
d_laser = 3.5     #mm - diameter of the laser beam emitted by the laser pointer (edmond: 1mm)(thorlabs: 3.5mm)
emis_wl = 510   #nm - Smallest flourescence emission wave length



# ----------------------------------------------------------------------------------------------------------------------------------



### Microscope characteristics
L_4 = f_imaging

f_obj = f_tube_corr / M_obj
M_true = f_imaging / f_obj
d_pup = 2 * NA_obj * f_obj

### Camera FOV
h_pixle = pixles[np.argmax(pixles)]
w_pixle = pixles[np.argmax(pixles) - 1]

h_sensor_cam = pixle_size * h_pixle * 10**(-3)  #in mm
w_sensor_cam = pixle_size * w_pixle * 10**(-3)  #in mm

h_FOV_cam = h_sensor_cam / M_true  #in mm
w_FOV_cam = w_sensor_cam / M_true  #in mm
diag_FOV_cam = np.sqrt(w_FOV_cam**2 + h_FOV_cam**2)

### Component limited FOV
# maximum height FOV (independent of the mirror angle)
h_max_phi_m1 = np.arctan((h_m - 2 * w_mg - d_pup) / (2 * L_1))
h_max_phi_dich = np.arctan((((h_dich - 2 * w_dg - 2 * h_dg)/ np.sqrt(2)) - d_pup) / (2 * (L_1 + L_dich))) ###GAAT NOG IETS FOUT, want origineel stond ie achter de 2 spiegel (np.arctan((((h_dich - 2 * w_dg - 2 * h_dg)/ np.sqrt(2)) - d_pup) / (2 * (L_1 + L_2 + L_dich))))
h_max_phi_m2 = np.arctan((h_m - 2 * w_mg - d_pup) / (2 * (L_1 + L_2)))
h_max_phi_filter = np.arctan((d_f  - d_pup) / (2 * (L_1 + L_2 + L_f)))
h_max_phi_lens = np.arctan((d_imaging - d_pup) / (2 * (L_1 + L_2 + L_3)))

h_max_phi = np.array([h_max_phi_m1, h_max_phi_m2, h_max_phi_dich, h_max_phi_filter, h_max_phi_lens])
h_phi_crit = np.min(h_max_phi)
h_FOV_crit = 2 * f_obj * np.tan(h_phi_crit)

# maximum width FOV (dependent on the mirror angle and at this point a mirror angle of 45 deg is assumed)
w_proj_m = (w_m - 2 * w_mg - 2 * h_mg) / np.sqrt(2)

w_max_phi_m1 = np.arctan((w_proj_m - d_pup) / (2 * L_1 + w_proj_m))
w_max_phi_dich = np.arctan((w_dich - 2* w_dg - d_pup) / (2 * (L_1 + L_dich)))       ###GAAT NOG IETS FOUT, want dit is deels van toen die achter de weede mirror stond.
w_max_phi_m2 = np.arctan((w_proj_m - d_pup) / (2* L_1 + 2 * L_2 + w_proj_m))
w_max_phi_filter = np.arctan((d_f - d_pup) / (2 * (L_1 + L_2 + L_f)))
w_max_phi_lens = np.arctan((d_imaging - d_pup) / (2 * (L_1 + L_2 + L_3)))

w_max_phi = np.array([w_max_phi_m1, w_max_phi_m2, w_max_phi_dich, w_max_phi_filter, w_max_phi_lens])
w_phi_crit = np.min(w_max_phi)
w_FOV_crit = 2 * f_obj * np.tan(w_phi_crit)     #mm

# determining the smallest diagonal
crit_res = np.array([w_FOV_crit, h_FOV_crit])
crit_diag = np.min(crit_res)

### Spare room calculation
h_needed_phi = np.arctan(h_FOV_cam / (2 * f_obj))
w_needed_phi = np.arctan(w_FOV_cam / (2 * f_obj))

h_d_dev_m1 = ((h_m - d_pup) / 2) - (L_1 * np.tan(h_needed_phi))
h_d_dev_m2 = ((h_m - d_pup) / 2) - ((L_1 + L_2) * np.tan(h_needed_phi))
h_d_dev_dich = ((w_dich - 2 * w_dg - 2 * h_dg - d_pup) / 2) - ((L_1 + L_2 + L_dich) * np.tan(h_needed_phi))
h_d_dev_filter = ((d_f - d_pup) / 2) - ((L_1 + L_2 + L_f) * np.tan(h_needed_phi))
h_d_dev_lens = ((d_imaging - d_pup) / 2) - ((f_imaging) * np.tan(h_needed_phi))
h_d_dev = np.array([h_d_dev_m1, h_d_dev_m2, h_d_dev_dich, h_d_dev_filter, h_d_dev_lens])

w_d_dev_m1 = ((w_proj_m - d_pup) / 2) - (((L_1 + (d_pup /2)) * np.tan(w_needed_phi)) / (1 - np.tan(w_needed_phi)))
w_d_dev_m2 = ((w_proj_m - d_pup) / 2) - (((L_1 + L_2 + (d_pup / 2)) * np.tan(w_needed_phi)) / (1 - np.tan(w_needed_phi)))
w_d_dev_dich = ((w_dich - 2 * w_dg - d_pup) / 2) - ((L_1 + L_2 + L_dich) * np.tan(w_needed_phi))
w_d_dev_filter = ((d_f - d_pup) / 2) - ((L_1 + L_2 + L_f) * np.tan(w_needed_phi))
w_d_dev_lens = ((d_imaging - d_pup) / 2) - ((f_imaging) * np.tan(w_needed_phi))
w_d_dev = np.array([w_d_dev_m1, w_d_dev_m2, w_d_dev_dich, w_d_dev_filter, w_d_dev_lens])

w_d_dev_m1_nc = ((w_proj_m - d_pup) / 2) - (((L_1 - (d_pup / 2)) * np.tan(w_needed_phi)) / (1 + np.tan(w_needed_phi)))
w_d_dev_m2_nc = ((w_proj_m - d_pup) / 2) - (((L_1 + L_2 - (d_pup / 2)) * np.tan(w_needed_phi)) / (1 + np.tan(w_needed_phi)))

### Resolution
res_obj = 0.61 * emis_wl * 10**(-3) / NA_obj
res_cam = pixle_size / M_true
Nyquist_cam = res_cam * 2.3

### Optical axis shift, due to refraction within the dichroic mirror
alpha = np.arcsin(np.sin(np.pi / 4) / refr_dich)
dev_alpha = (np.pi / 4) - alpha
axis_shift = t_dich * np.sin(dev_alpha)

### Maximum tube lens distance
d_imagefield = np.sqrt((h_sensor_cam**2) + (w_sensor_cam**2))
L_max = (d_imaging - d_pup) * f_imaging / d_imagefield

### Laser beam expansion

beam_width = w_FOV_crit / (f_obj / f_ach_l_shape)
f_needed = f_asp_l_shape * beam_width / d_laser

### Test prints
# print(h_max_phi * 180 / np.pi)
# print(w_max_phi * 180 / np.pi)
# print(crit_diag)
# print(h_d_dev)
# print(w_d_dev)
# print(w_d_dev_m1_nc)
# print(w_d_dev_m2_nc)
# print(L_max)
# print(beam_width)
# print(f_needed)



# ----------------------------------------------------------------------------------------------------------------------------------------



### Print statements
print(f"\nMicroscope magnification: {M_true:.2f}\n"
      f"Downwards focal axis length: {(L_3 + L_4):.1f} mm\n"
      f"Maximal distance between objective and imaging lens: {L_max:.2f} mm\n"
      f"Optical axis shift: {axis_shift:.2f} mm\n"
      f"Maximum allowable FOV: {w_FOV_crit:.3f} x {h_FOV_crit:.3f} (in mm x mm).\n" 
      f"Camera FOV: {w_FOV_cam:.3f} x {h_FOV_cam:.3f} (in mm x mm) with a diagonal of {diag_FOV_cam:.3f} mm.")

if diag_FOV_cam > crit_diag:
    if np.argmax(w_max_phi) == 1:
        print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
              'The first mirror is the limiting factor, due to its width and distance from the objective')
    elif np.argmax(w_max_phi) == 2:
        print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
              'The second mirror is the limiting factor, due to its width and distance from the objective')
    elif np.argmax(w_max_phi) == 3:
        print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
              'The dichroic mirror is the limiting factor, due to its width and distance from the objective')
    elif np.argmax(w_max_phi) == 4:
        print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
              'The filter is the limiting factor, due to its width and distance from the objective')
    else:
        print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
              'The imaging lens is the limiting factor, due to its width and distance from the objective')

if diag_FOV_cam < crit_diag:
    print('No information will be lost, as the FOV of the camera is smaller than the by the components allowed FOV\n')

print(f'Objective resolution: {res_obj:.2f} \n'
      f'Camera resolution (after Nyquist, 2.3x): {Nyquist_cam:.2f}')

if res_obj > Nyquist_cam:
    print('The image is sampled correctly.')
elif res_obj > res_cam:
    print('The image is technically sampled correctly, as it is sampled at a frequency of 2x or more, but not above the safety margin of 2.3x.')
else:
    print('The image is not sampled incorrectly.')

print('\nThe spare room on the optical components (in mm) is:\n'
      '               mirror 1     mirror 2     dichroic     filter     lens\n'
      f'top/bottom:     {h_d_dev_m1:.2f}         {h_d_dev_m2:.2f}          {h_d_dev_dich:.2f}        {h_d_dev_filter:.2f}      {h_d_dev_lens:.2f}\n'
      f'critical:       {w_d_dev_m1:.2f}         {w_d_dev_m2:.2f}           ^           ^         ^\n'
      f'non-critical:   {w_d_dev_m1_nc:.2f}         {w_d_dev_m2_nc:.2f}          {w_d_dev_dich:.2f}        {w_d_dev_filter:.2f}      {w_d_dev_lens:.2f}\n')

print(f'The minimal focal length needed for collimating the laser beam out of the optical fiber is: {f_needed:.2f} mm\n')


# if w_FOV_cam > w_FOV_crit:
#     if np.argmax(w_max_phi) == 1:
#         print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
#               'The first mirror is the limiting factor, due to its width and distance from the objective')
#     elif np.argmax(w_max_phi) == 2:
#         print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
#               'The second mirror is the limiting factor, due to its width and distance from the objective')
#     elif np.argmax(w_max_phi) == 3:
#         print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
#               'The dichroic mirror is the limiting factor, due to its width and distance from the objective')
#     elif np.argmax(w_max_phi) == 4:
#         print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
#               'The filter is the limiting factor, due to its width and distance from the objective')
#     else:
#         print('As the FOV width of the camera is bigger than the by the components allowed FOV width, information will be lost.\n' 
#               'The imaging lens is the limiting factor, due to its width and distance from the objective')
# if h_FOV_cam > h_FOV_crit:
#     if np.argmax(h_max_phi) == 1:
#         print('As the FOV height of the camera is bigger than the by the components allowed FOV height, information will be lost.\n' 
#               'The first mirror is the limiting factor, due to its height and distance from the objective')
#     elif np.argmax(h_max_phi) == 2:
#         print('As the FOV height of the camera is bigger than the by the components allowed FOV height, information will be lost.\n' 
#               'The second mirror is the limiting factor, due to its height and distance from the objective')
#     elif np.argmax(h_max_phi) == 3:
#         print('As the FOV height of the camera is bigger than the by the components allowed FOV height, information will be lost.\n' 
#               'The dichroic mirror is the limiting factor, due to its height and distance from the objective')
#     elif np.argmax(h_max_phi) == 4:
#         print('As the FOV height of the camera is bigger than the by the components allowed FOV height, information will be lost.\n' 
#               'The filter is the limiting factor, due to its height and distance from the objective')
#     else:
#         print('As the FOV height of the camera is bigger than the by the components allowed FOV height, information will be lost.\n' 
#               'The imaging lens is the limiting factor, due to its height and distance from the objective')