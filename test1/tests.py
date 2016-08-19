# tests.py
#
# Use the functions below to test various features of the vera converter

import sys; sys.path.append('..')
import openmc
import vera_to_openmc


def test_pincell(case_file = "../1c.xml.gold", aname="assy"):
	'''Create and run a simple pincell'''
	pincell_case = vera_to_openmc.MC_Case(case_file)
	
	
	assembly = pincell_case.assemblies[aname]
	veracell1 = assembly.cells['PIN1']
	openmc_cell1 = pincell_case.get_openmc_pincell(veracell1)
	
	
	
	plot_assembly(assembly.pitch, 1)
	'''# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [01.5, 01.5]
	plot.pixels = [1250, 1250]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()'''
	
	bounds = set_cubic_boundaries(assembly.pitch, 1, ("reflective",)*6)

	return pincell_case, openmc_cell1, assembly.pitch, 1, bounds


def test_assembly(case_file = "../p7.xml.gold", aname='2'):
	'''Create and run a more complicated assembly'''
	
	ascase = vera_to_openmc.MC_Case(case_file)
	as2 = ascase.assemblies[aname]
	#print(ascase.assemblies.keys())
	
	openmc_as2_layers = ascase.get_openmc_assemblies(as2) 
	some_asmbly = openmc_as2_layers[0]	# 2 is the one with fuel
	
	plot_assembly(as2.pitch, as2.npins)
	bounds = set_cubic_boundaries(as2.npins, as2.pitch)
	
	return ascase, some_asmbly, as2.pitch, as2.npins, bounds



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
	


def test_core(case_file = "../2o.xml.gold"):
	'''Create a full core geometry'''
	core_case = vera_to_openmc.MC_Case(case_file)
	c = core_case.core
	n = None; pitch = None
	
	if c.size == 1:
		# Single assembly case
		aname = c.asmbly.square_map()[0][0].lower()
		asmbly = core_case.assemblies[aname]
		n = asmbly.npins; pitch = asmbly.pitch; 
		plot_assembly(pitch, n)
		fillcore = core_case.get_openmc_assemblies(asmbly)[0]
		bounds = (c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["top"], c.bc["top"])
		boundaries = set_cubic_boundaries(pitch, n, bounds)
		
		
	elif c.radii:
		radius = openmc.ZCylinder(R = max(case.core.vessel_radii), boundary_type = 'vacuum')
		min_z = openmc.ZPlane(z0 = 0, boundary_type="vacuum")
		max_z = openmc.ZPlane(z0 = case.core.height, boundary_type="vacuum")
		plot_assembly(c.pitch, 2)
		
		boundaries = (radius, min_z, max_z)
	
	else:
		raise(IOError)
		
	#PLOT
		
	return core_case, fillcore, pitch, n, boundaries
	



if __name__ == "__main__":
	#case, fillcell, pitch, n, bounds = test_pincell("../1c.xml.gold", "assy1")
	#case, fillcell, pitch, n, bounds = test_assembly("../p7.xml.gold")
	case, fillcell, pitch, n, bounds = test_assembly("../2a_dep.xml.gold", "assy")
	#case, fillcell, pitch, n, bounds = test_core()
	
	materials = openmc.Materials(case.openmc_materials.values())
	materials.default_xs = '71c'
	materials.export_to_xml()
	
	# Create root Cell
	root_cell = openmc.Cell(name='root cell')
	root_cell.fill = fillcell
	
	# Handle boundary conditions
	if len(bounds) == 3:
		radius, min_z, max_z = bounds
		root_cell.region = -radius & +min_z & -max_z
	elif len(bounds) == 6:
		min_x, max_x, min_y, max_y, min_z, max_z = bounds
		# Create boundary planes to surround the geometry
		root_cell.region = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	
	
	# Create Geometry and set root Universe
	root_universe = openmc.Universe(universe_id=0, name='root universe')
	root_universe.add_cell(root_cell)
	geometry = openmc.Geometry()
	geometry.root_universe = root_universe
	# Export to "geometry.xml"
	geometry.export_to_xml()
	
	
	

	
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
	# Create an initial unifo rm spatial source distribution over fissionable zones
	pitch = 10
	bounds = [-pitch/2.0, -pitch/2.0, -pitch/2.0, pitch/2.0, pitch/2.0, pitch/2.0]
	uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:], only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()
	
	
	
	###DEBUG###
	
	
	#print(case.openmc_surfaces)
	#print(case.openmc_cells)
	print(fillcell)
	# '''

	