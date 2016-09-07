
import sys; sys.path.append('..')
import openmc
import vera_to_openmc



def test_baffle(baffle_cells, baffill, asmbly_lat, bounds):
	'''Test the get_openmc_baffle() function for geometric integrity.
	
	Inputs:
		baffle_cells:	list of instances of openmc.Cell describing the baffle make-up 
		asmbly_lat:		instance of openmc.RectLattice describing the core layout
		bounds:			tuple of instances of openmc.Surface that fall within asmbly_lat,
						but outside the baffle.
	
	Output:
		core_universe:	instance of openmc.Universe containing the baffle and the core lattice
	'''
	
	(min_x, max_x, min_y, max_y, min_z, max_z) = bounds
	
	core_universe = openmc.Universe()
	box = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	
	the_baffle = openmc.Cell(101, name = "the baffle")
	the_baffle.region = baffle_cells[0].region
	for c in baffle_cells[1:len(baffle_cells)]:
		the_baffle.region = the_baffle.region | c.region
	#the_baffle.region = the_baffle.region & (+min_z & -max_z)
	the_baffle.fill = baffill
	
	print(the_baffle)
	
	not_the_baffle = openmc.Cell(102, name = "not the baffle")
	not_the_baffle.region = ~the_baffle.region & box
	not_the_baffle.fill = asmbly_lat
	
	core_universe.add_cells((the_baffle, not_the_baffle))
	
	return core_universe
	
	
def set_settings(pitch):
	# OpenMC simulation parameters
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
	#pitch = 10
	bounds = (-pitch/2.0,)*3 + (pitch/2.0,)*3
	uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:], only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()
	
	
	

def set_cubic_boundaries(pitch, n, bounds=('reflective',)*6):
	'''Inputs:
		pitch:		float; pitch between fuel pins 
		n:			int; number of fuel pins in an assembly (usually 1 or 17)
		bounds:		tuple/list of strings with len=6, containing the respective
					boundary types for min/max x, y, and z (default: all reflective)
	
	Outputs:
		a tuple of the openmc X/Y/ZPlanes for the min/max x, y, and z boundaries
	'''
	
	min_x = openmc.XPlane(x0=-n*pitch/2.0, boundary_type=bounds[0])
	max_x = openmc.XPlane(x0=+n*pitch/2.0, boundary_type=bounds[1])
	min_y = openmc.YPlane(y0=-n*pitch/2.0, boundary_type=bounds[2])
	max_y = openmc.YPlane(y0=+n*pitch/2.0, boundary_type=bounds[3])
	min_z = openmc.ZPlane(z0=-n*pitch/2.0, boundary_type=bounds[4])
	max_z = openmc.ZPlane(z0=+n*pitch/2.0, boundary_type=bounds[5])
	
	return (min_x, max_x, min_y, max_y, min_z, max_z)



def create_openmc_materials():
	
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
	
	return materials
	

def create_9x9_lattice(materials, pitch):
	(mod, fuel, clad)  = materials
	
	# Make the pin surfaces
	ring0 = openmc.ZCylinder(R = 0.5)
	ring1 = openmc.ZCylinder(R = 0.75)
	#baf_in = openmc.ZCylinder(R = 5.0)
	#baf_out = openmc.ZCylinder(R = baf_in.coefficients['R'] + 1.0)
	#vessel = openmc.ZCylinder(R = 10)
	
	
	# Make the pin cells
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

	
	# Make the pin universes
	fpin = openmc.Universe(1)
	fpin.add_cells((cell0, cell1, cell2))
	
	puremodcell = openmc.Cell()
	puremodcell.fill = mod
	
	mpin = openmc.Universe(2)
	mpin.add_cell(puremodcell)


	
	lat = [[mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, fpin, fpin, fpin, mpin, mpin, mpin],
           [mpin, mpin, fpin, fpin, fpin, fpin, fpin, mpin, mpin],
           [mpin, mpin, fpin, fpin, mpin, fpin, fpin, mpin, mpin],
           [mpin, mpin, fpin, fpin, fpin, fpin, fpin, mpin, mpin],
           [mpin, mpin, mpin, fpin, fpin, fpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin],
           [mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin, mpin]]
	
	
	lattice = openmc.RectLattice(32)
	lattice.universes = lat
	lattice.pitch = (pitch, pitch)
	lattice.lower_left = [-pitch * float(len(lat)) / 2.0] * 2

	return lattice




def plot_everything(apitch, n, width=1250, height=1250):
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [n*pitch - .01, n*pitch - .01]
	plot.pixels = [width, height]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()
	
	
	
	
	
if __name__ == "__main__":
	case = vera_to_openmc.MC_Case("../p7.xml.gold")
	mats = create_openmc_materials()
	pitch = 2.0; n = 9
	apitch = case.core.pitch
	asmbly_lat = create_9x9_lattice(mats, pitch)
	edges = set_cubic_boundaries(pitch, n+4)
	(min_x, max_x, min_y, max_y, min_z, max_z) = edges
	box = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	baffle_verse = test_baffle(case.get_openmc_baffle(case.core), mats[-1], asmbly_lat, edges)
	
	
	# Create Geometry and set root Universe
	root_cell = openmc.Cell(name='root cell')
	root_cell.region = box
	root_cell.fill = baffle_verse
	root_universe = openmc.Universe(universe_id=0, name='root universe')
	root_universe.add_cell(root_cell)
	geometry = openmc.Geometry()
	geometry.root_universe = root_universe
	# Export to "geometry.xml"
	geometry.export_to_xml()
	
	plot_everything(apitch, n+3)
	set_settings(apitch)
	
	
	
	
	