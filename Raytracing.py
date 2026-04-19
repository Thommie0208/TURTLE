from raytracing import *

# path = ImagingPath()
# path.append(Space(d=50))
# path.append(Lens(f=50, diameter=25))
# path.append(Space(d=120))
# path.append(Lens(f=30))
# path.append(Space(d=100))
# path.display()

### Beetje kloten ###
# path = ImagingPath()
# path.append(Space(d=4))
# path.append(Lens(f=4, diameter=8, label='ObjectiveLens'))
# path.append(Space(d=184))
# path.append(Lens(f=180, diameter=50, label='TubeLens'))
# path.append(Space(d=180))
# path.display(ObjectRays(diameter=1, halfAngle=0.5))

### CurvedMirror ###
# path = ImagingPath()
# path.append(Space(d=50))
# path.append(Lens(f=50, label = 'Lens'))
# path.append(Space(d=20))
# path.append(CurvedMirror(R=-200, diameter=300, label = 'Mirror'))           #CurvedMirror=lens,R+ = divergerend, R- = convergerend
# path.append(Space(d=200))
# path.display(ObjectRays(diameter = 1, halfAngle=0.5))

### Laser ###
# path = LaserPath()
# path.append(Space(d=50))
# path.append(Lens(f=100))
# path.append(Space(d=150))
# path.append(CurvedMirror(R=200, diameter=20))
# path.append(Space(d=200))
# beam = GaussianBeam(
#     w=3.0,                 # beam waist (mm)
#     wavelength=0.0006328   # golflengte (mm) → 632.8 nm (HeNe laser)
# )
# path.inputBeam = beam
# path.display()

### Matrices en manier om dingen te berekenen ###
# system = Space(d=20) * Lens(f=50) * Space(d=30)    #LET OP: matrixvermenigvuldiging, dus van rechts naar links
# ray = Ray(y=1, theta=0.05)                         #Lichtstraal
# result = system * ray
# print("Output ray:", result)

### Deze output geeft drie waarden: y, theta en z
### y is de hoogte van de ray tov van de optische as
### theta is de hoek van de ray
### z is de horizontale afstand, is in deze code 50, want Space(20) + Space(30) = 50