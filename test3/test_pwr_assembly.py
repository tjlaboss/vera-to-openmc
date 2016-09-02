import sys; sys.path.append('..')
import openmc
import objects
import PWR_assembly


def plot_assembly(pitch, npins, width=1250, height=1250):
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [npins*pitch - .01, npins*pitch - .01]
	plot.pixels = [width, height]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()

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


def settings(pitch):
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
	bounds = (-pitch/2.0,)*3 + (pitch/2.0,)*3
	uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:], only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()


# Test
if __name__ == '__main__':
	
	# Define a global test moderator
	mod = openmc.Material(1, "mod")
	mod.set_density("g/cc", 1.0)
	mod.add_nuclide("h-1", 2.0/3, 'ao')
	mod.add_nuclide("o-16", 1.0/3, 'ao')
	
	# Define a simple test material
	iron = openmc.Material(2, "iron")
	iron.set_density("g/cc", 7.8)
	iron.add_element("Fe", 1, 'ao', expand=True)
	
	fuel = openmc.Material(3, "fuel")
	fuel.set_density("g/cc", 8.1)
	fuel.add_nuclide("u-233", 1, 'ao')
	
	mix1 = PWR_assembly.Mixture([mod, iron], [0.5,0.5], 33, 'watery iron')
	assert isinstance(mix1, openmc.Material)	
	noz1 = objects.Nozzle(10, 6250, iron, mod, 1, 10)

	# Test a pincell
	pitch = 1.0
	cyl0 = openmc.ZCylinder(10, R = 0.300) 
	cyl1 = openmc.ZCylinder(11, R = 0.333)
	cyl2 = openmc.ZCylinder(12, R = 0.350)
	ring0 = openmc.Cell(100, fill = iron, region = -cyl0)
	ring1 = openmc.Cell(101, fill = mix1, region = (-cyl1 & +cyl0) )
	ring2 = openmc.Cell(102, fill = fuel, region = (-cyl2 & +cyl1) )
	outer = openmc.Cell(199, fill = mod, region = +cyl2)
	uni = openmc.Universe(cells = (ring0, ring1, ring2, outer), name = "test pincell")
	print(uni)
	gridded = PWR_assembly.add_grid_to(uni, pitch, 0.10, iron)
	print(gridded)
	
	
	# Actual OpenMC test
	materials = openmc.Materials((iron, mod, mix1, fuel))
	materials.default_xs = '71c'
	materials.export_to_xml()
	
	root_cell = openmc.Cell(name='root cell')
	root_cell.fill = gridded
	(min_x, max_x, min_y, max_y, min_z, max_z) = set_cubic_boundaries(pitch, 1)
	root_cell.region = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	root_universe = openmc.Universe(universe_id=0, name='root universe')
	root_universe.add_cell(root_cell)
	geometry = openmc.Geometry()
	geometry.root_universe = root_universe
	# Export to "geometry.xml"
	geometry.export_to_xml()
	
	settings(pitch)
	plot_assembly(pitch, 1)
	
	
	
	