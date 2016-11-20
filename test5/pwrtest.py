import sys
sys.path.append('..')

import pwr
import openmc


# Instantiate some Nuclides
h1 = openmc.Nuclide('H1')
b10 = openmc.Nuclide('B10')
o16 = openmc.Nuclide('O16')
u235 = openmc.Nuclide('U235')
u238 = openmc.Nuclide('U238')
zr90 = openmc.Nuclide('Zr90')
# 1.6 enriched fuel
fuel = openmc.Material(name='1.6% Fuel')
fuel.set_density('g/cm3', 10.31341)
fuel.add_nuclide(u235, 3.7503e-4)
fuel.add_nuclide(u238, 2.2625e-2)
fuel.add_nuclide(o16, 4.6007e-2)
# borated water
water = openmc.Material(name='Borated Water')
water.set_density('g/cm3', 0.740582)
water.add_nuclide(h1, 4.9457e-2)
water.add_nuclide(o16, 2.4732e-2)
water.add_nuclide(b10, 8.0042e-6)
# zircaloy
zircaloy = openmc.Material(name='Zircaloy')
zircaloy.set_density('g/cm3', 6.55)
zircaloy.add_nuclide(zr90, 7.2758e-3)
# Instantiate a Materials collection
materials_file = openmc.Materials((fuel, water, zircaloy))
materials_file.default_xs = '06c'
materials_file.export_to_xml()

# Create a Universe to encapsulate a fuel pin
pin_cell_universe = openmc.Universe(name='1.6% Fuel Pin')
# Create cylinders for the fuel and clad
fuel_outer_radius = openmc.ZCylinder(x0=0.0, y0=0.0, R=0.39218)
clad_outer_radius = openmc.ZCylinder(x0=0.0, y0=0.0, R=0.45720)
# Create boundary planes to surround the geometry
# Use both reflective and vacuum boundaries to make life interesting
#min_x = openmc.XPlane(x0=-10.71, boundary_type='reflective')
#max_x = openmc.XPlane(x0=+10.71, boundary_type='vacuum')
#min_y = openmc.YPlane(y0=-10.71, boundary_type='vacuum')
#max_y = openmc.YPlane(y0=+10.71, boundary_type='reflective')
min_z = openmc.ZPlane(z0=0, boundary_type='reflective')
max_z = openmc.ZPlane(z0=10, boundary_type='reflective')
# Create fuel Cell
fuel_cell = openmc.Cell(10, name='1.6% Fuel')
fuel_cell.fill = fuel
fuel_cell.region = -fuel_outer_radius
fuel_cell.temperature = 600.0
pin_cell_universe.add_cell(fuel_cell)
# Create a clad Cell
clad_cell = openmc.Cell(11, name='1.6% Clad')
clad_cell.fill = zircaloy
clad_cell.region = +fuel_outer_radius & -clad_outer_radius
clad_cell.temperature = 600.0
pin_cell_universe.add_cell(clad_cell)
# Create a moderator Cell
moderator_cell = openmc.Cell(12, name='1.6% Moderator')
moderator_cell.fill = water
moderator_cell.region = +clad_outer_radius
moderator_cell.temperature = 600.0
pin_cell_universe.add_cell(moderator_cell)
#Using the pin cell universe, we can construct a 17x17 rectangular lattice with a 1.26 cm pitch.
# Create fuel assembly Lattice
as1 = openmc.RectLattice(33, name='1.6% Fuel RectLattice')
as1.pitch = (1.26, 1.26)
as1.lower_left = [-1.26 * 17. / 2.0] * 2
as1.universes = [[pin_cell_universe] * 17] * 17
as1.outer = pin_cell_universe




mypwr = pwr.Assembly(key = "1", name = "pwr_assembly", pitch = 1.26, npins = 17)
mypwr.lattices = [as1, as1]
mypwr.lattice_elevs = [0, 5, 10]
mypwr.mod = water
pwrverse = mypwr.build()
for surf in mypwr.openmc_surfaces:
	surf.boundary_type = "reflective"
# = mypwr.walls

# Create root Cell
root_cell = openmc.Cell(name='root cell')
root_cell.fill = pwrverse
# Add boundary planes
root_cell.region = mypwr.wall_region & +min_z & -max_z
root_universe = openmc.Universe(universe_id=0, name='root universe')
root_universe.add_cell(root_cell)
# Create Geometry and set root Universe
geometry = openmc.Geometry()
geometry.root_universe = root_universe
# Export to "geometry.xml"
geometry.export_to_xml()


# Instantiate a Plot
plot = openmc.Plot(plot_id=1)
plot.filename = 'plot-materials-xy'
plot.origin = [0, 0, 0]
plot.width = [21.5, 21.5]
plot.pixels = [750, 750]
plot.color = 'mat'
plot.basis = 'xz'
plot_file = openmc.Plots([plot])
plot_file.export_to_xml()
## Instantiate a Settings object
# OpenMC simulation parameters
min_batches = 20
max_batches = 200
inactive = 5
particles = 2500
settings_file = openmc.Settings()
settings_file.batches = min_batches
settings_file.inactive = inactive
settings_file.particles = particles
settings_file.output = {'tallies': False}
settings_file.trigger_active = True
settings_file.trigger_max_batches = max_batches
# Create an initial uniform spatial source distribution over fissionable zones
bounds = [-6.71, -6.71, 1, 6.71, 6.71, 2]
uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:], only_fissionable=True)
settings_file.source = openmc.source.Source(space=uniform_dist)
# Export to "settings.xml"
settings_file.export_to_xml()








