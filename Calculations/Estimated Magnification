import numpy as np

#Beide zijn fabrikant gegevens en hier weet ik de onzekerheid niet van
W_line = 7.8     #micrometre - line width of the test slip
p_s = 3.45       #micrometre - pixel size (at the image sensor)

u_wline = 0.05
u_ps = 0.005

#Results
n_p_hor = np.array([18.9225, 18.9125, 18.8613, 19.0395, 19.0162, 19.0500, 19.1463, 19.0947, 18.9494, 19.2058, 19.0976, 19.0365, 18.9408, 18.8837, 18.8717])          #number of pixels to display the line at FWHM for horizontal measurements
n_p_vert = np.array([19.0265, 18.9421, 18.9605, 19.4417, 19.2746, 19.3210, 19.4286, 19.3285, 19.6476, 19.2893, 19.5818, 19.2512, 18.7413, 18.7191, 18.9111])            #number of pixels to display the line at FWHM for vertical measurements
u_pi = 0.5      #uncertainty of the measurements --> is the same as the uncertainty of the 

#Calculations
#n_p = np.hstack((n_p_hor, n_p_vert))
n_p = n_p_vert

n_p_mean = n_p.sum() / len(n_p)
u_np = u_pi * np.sqrt(2)
u_np_mean = u_np / np.sqrt(len(n_p))

M_est = p_s * n_p_mean / W_line

u_m_ps = (n_p_mean / W_line) * u_ps
u_m_wl = -1 * (p_s * n_p_mean / (W_line ** 2)) * u_wline
u_m_np = (p_s / W_line) * u_np_mean
u_m_est = np.sqrt(u_m_ps ** 2 + u_m_wl ** 2 + u_m_np ** 2)

print(f"The estimated magnification is {M_est:.2f} \u00B1 {u_m_est:.2f}")