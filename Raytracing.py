from raytracing import *

# path = ImagingPath()
# path.append(Space(d=50))
# path.append(Lens(f=50, diameter=25))
# path.append(Space(d=120))
# path.append(Lens(f=30))
# path.append(Space(d=100))
# path.display()
    

path = ImagingPath()
path.append(Space(d=4))
path.append(Lens(f=4, diameter=8, label='ObjectiveLens'))
path.append(Space(d=184))
path.append(Lens(f=180, diameter=50, label='TubeLens'))
path.append(Space(d=180))
path.display(ObjectRays(diameter=1, halfAngle=0.5))