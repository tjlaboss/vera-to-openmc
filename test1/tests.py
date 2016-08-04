# tests.py
#
# Use the functions below to test various features of the vera converter

import sys; sys.path.append('..')
import openmc
import vera_to_openmc


def test_pincell(case_file):
	'''Create and run a simple pincell'''
	pincell_case = vera_to_openmc.MC_Case(case_file)
	
	
	assembly = pincell_case.assemblies["assy"]
	veracell1 = assembly.cells['1']
	openmc_cell1 = pincell_case.get_openmc_pincell(veracell1)
	
	
	
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [01.5, 01.5]
	plot.pixels = [1250, 1250]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()

	return pincell_case, openmc_cell1, assembly.pitch, 1


def test_assembly(case_file = "../p7.xml.gold"):
	'''Create and run a more complicated assembly'''
	
	ascase = vera_to_openmc.MC_Case(case_file)
	as2 = ascase.assemblies['2']
	#print(ascase.assemblies.keys())
	
	openmc_as2_layers = ascase.get_openmc_assemblies(as2) 
	gap_asmbly = openmc_as2_layers[2]	# 2 is the one with fuel
	#for row in gap_asmbly.universes:
	#	for u in row:
	#		#print(str(u.id) + ' ', end="")
	#		print(u.cells)
	#	print()
	#print(gap_asmbly.universes)
	#for a in gap_asmbly.cells:
	#	print (gap_asmbly.cells[a])
	#print(str(x) for x in as2.cells.values())
	
	
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [as2.npins*as2.pitch - .01, as2.npins*as2.pitch - .01]
	plot.pixels = [1250, 1250]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()
	
	return ascase, gap_asmbly, as2.pitch, as2.npins


if __name__ == "__main__":
	#case_file = "../2a_dep.xml.gold"
	#case, fillcell, pitch, n = test_pincell(case_file)

	case, fillcell, pitch, n = test_assembly("../p7.xml.gold")
	#print(fillcell)
	
	materials = openmc.Materials(case.openmc_materials.values())
	materials.default_xs = '71c'
	materials.export_to_xml()
	
	# Create root Cell
	root_cell = openmc.Cell(name='root cell')
	root_cell.fill = fillcell
	# Create boundary planes to surround the geometry
	min_x = openmc.XPlane(x0=-n*pitch/2.0, boundary_type='reflective')
	max_x = openmc.XPlane(x0=+n*pitch/2.0, boundary_type='vacuum')
	min_y = openmc.YPlane(y0=-n*pitch/2.0, boundary_type='vacuum')
	max_y = openmc.YPlane(y0=+n*pitch/2.0, boundary_type='reflective')
	min_z = openmc.ZPlane(z0=-n*pitch/2.0, boundary_type='reflective')
	max_z = openmc.ZPlane(z0=+n*pitch/2.0, boundary_type='reflective')
	# Add boundary planes
	root_cell.region = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	root_universe = openmc.Universe(universe_id=0, name='root universe')
	root_universe.add_cell(root_cell)
	# Create Geometry and set root Universe
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
	bounds = [-pitch-1, -pitch-1, -10, pitch-1, pitch-1, 10.]
	uniform_dist = openmc.stats.Box(bounds[:3], bounds[3:], only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()
	
	
	
	###DEBUG###
	
	
	print(case.openmc_surfaces)
	#print(case.openmc_cells)
	print(fillcell)
	

	