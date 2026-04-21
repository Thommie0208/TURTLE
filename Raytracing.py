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

### objective ###
# obj = Objective(f=10, NA=0.8, focusToFocusLength=60, backAperture=18, workingDistance=2, magnification=40, fieldNumber=1.4, label="Objective")
# path = ImagingPath()
# path.label = "Path with generic objective"
# path.append(Space(d=180))
# path.append(obj)
# path.append(Space(d=10))
# path.displayWithObject(diameter=20, fanAngle=0.005)

### thorlabs lens ###
# path = ImagingPath()
# path.append(Space(d=50))
# path.append(thorlabs.AC127_050_A())
# path.append(Space(d=75))
# path.display()

### OpenFlexure ### vgm?????????????????
focal = 4 #mm
NumericalAperture = 0.65
n = 1.0003 #refractive index van air
WorkingDistance = 0.6 #mm

back_aperture = 2*focal*NumericalAperture/n

obj_OpenFlexure = Objective(f=focal, NA = NumericalAperture, focusToFocusLength = focal+WorkingDistance, backAperture = back_aperture, 
                            workingDistance = WorkingDistance, 
                            magnification=40, label='Objective')
path = ImagingPath()
path.label = "Path with generic objective"
path.append(Space(d=4))
path.append(obj_OpenFlexure)
path.append(Space(d=160))
path.append(thorlabs.AC127_050_A())
path.append(Space(d=150))
path.displayWithObject(diameter=20, fanAngle=0.005)