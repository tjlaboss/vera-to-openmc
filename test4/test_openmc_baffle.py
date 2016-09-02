import openmc


ring0 = openmc.ZCylinder(R = 0.5)
ring1 = openmc.ZCylinder(R = 0.75)

baf_in = openmc.ZCylinder(R = 5.0)
baf_out = openmc.ZCylinder(R = baf_in.coefficients['R'] + 1.0)

vessel = openmc.ZCylinder(R = 10)

# Essential materials
mod = openmc.Material(name="mod")
mod.add_nuclide("h-1", 1)

fuel = openmc.Material(name="u31")
fuel.add_nuclide("u-238", (100-3.1)/100.0, 'wo')
fuel.add_nuclide("u-235", (3.1)/100.0, 'wo')


clad = openmc.Material(name="iron")
clad.add_nuclide("fe-56", 1, 'wo')


materials = openmc.Materials((mod, fuel, clad))
materials.default_xs = "71c"
materials.export_to_xml()

# Universe for the lattice
cell0 = openmc.Cell()
cell0.region = -ring0
cell0.fill = fuel
cell1 = openmc.Cell()
cell1.region = -ring1 & +ring0
cell1.fill = clad
cell2 = openmc.Cell()
cell2.region = +ring1
cell2.fill = mod

fpin = openmc.Universe(1)
fpin.add_cells((cell0, cell1, cell2))

puremodcell = openmc.Cell()
#puremodcell.region = +ring1 & -ring1
puremodcell.fill = mod

mpin = openmc.Universe(2)
mpin.add_cell(puremodcell)


lat = [[mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
       [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
	   [mpin, mpin, mpin, fpin, fpin, fpin, mpin, mpin, mpin],
	   [mpin, mpin, fpin, fpin, fpin, fpin, fpin, mpin, mpin],
	   [mpin, mpin, fpin, fpin, fpin, fpin, fpin, mpin, mpin],
	   [mpin, mpin, mpin, fpin, fpin, fpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin]]

lattice = openmc.RectLattice(3)
lattice.universes = lat
lattice.pitch = (2.0, 2.0)
lattice.lower_left = [-2.0 * float(len(lat)) / 2.0] * 2


# make the root universe
a = 16
left = openmc.XPlane(x0 = -a)
right= openmc.XPlane(x0 = +a)
top  = openmc.YPlane(y0 = +a)
bot  = openmc.YPlane(y0 = -a)
above= openmc.ZPlane(z0 = +a)
below= openmc.ZPlane(z0 = -a)
for s in (left, right, top, bot, above, below):
    s.boundary_type = "vacuum"


inside_baffle = openmc.Cell()
inside_baffle.region = +baf_in & -baf_out
inside_baffle.fill = clad

outside_baffle = openmc.Cell()
outside_baffle.region = ~inside_baffle.region & \
	(+left & -right & +bot & -top)
outside_baffle.fill = lattice

root_universe = openmc.Universe(0)
root_universe.add_cells((inside_baffle, outside_baffle))
geometry = openmc.Geometry()
geometry.root_universe = root_universe
geometry.export_to_xml()


# OpenMC simulation parameters
if True:
	min_batches = 20
	max_batches = 200
	inactive = 5
	particles = 2500
	
	# Instantiate a Settings object
	settings_file = openmc.Settings()
	settings_file.batches = min_batches
	settings_file.inactive = inactive
	settings_file.particles = particles
	settings_file.output = {'tallies': False}
	settings_file.trigger_active = True
	settings_file.trigger_max_batches = max_batches
	# Create an initial uniform spatial source distribution over fissionable zones
	pitch = 6
	bounds = (-pitch/2.0,)*3 + (pitch/2.0,)*3
	uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:], only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()
	
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [a - .01, a - .01]
	plot.pixels = [1000, 1000]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()


