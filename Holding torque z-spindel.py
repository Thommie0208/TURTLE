import numpy as np

# Lead screw parameters
friction_coefficient = 0.4 #Static friction brass - steel
thread_angle = 30.0  # degrees
thread_diameter = 8.0  # mm

# Stage parameters
infill = 0.25  # 25% infill
pla_density = 1.25 * infill  # g/cm^3
stage_length = 85.0  # mm
stage_width = 50.0  # mm
stage_height = 100.0  # mm
motor_weight = 0.5 # kg
stage_weight = (stage_length * stage_width * stage_height * pla_density) / 1e6 # kg

rho = np.arctan(friction_coefficient)
phi = np.radians(thread_angle)

F_i = (stage_weight + 2 * motor_weight) * 9.81  # N
F_h = F_i * np.tan(rho + phi)  # N

required_torque = F_h * (thread_diameter / 2000)  # Nm

print(f"Downward force (F_i): {F_i:.2f} N")
print(f"Required torque to hold the stage: {required_torque:.3f} Nm\n"
      f"{required_torque:.3f} Nm = {required_torque / 9.81 * 100:.2f} kgcm")