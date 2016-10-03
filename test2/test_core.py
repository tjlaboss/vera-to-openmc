# test_core.py
#
# Given a full-core VERA model, try to produce the corresponding OpenMC input.
# The goal of this test is to see what methods and classes are missing from vera_to_openmc.py.
# The overall structure of the final converter may not look like this.

import sys; sys.path.append('..')
import openmc
import vera_to_openmc
from functions import fill_lattice


def convert_to_openmc(file):
	case = vera_to_openmc.MC_Case(file)
	
	# Get the OpenMC model of the reactor pressure vessel
	rpv, core_cell, fill_mat, outer_vessel_surfs = case.get_openmc_reactor_vessel(case.core)
	
	
	
	# First order of business: fill the core with assemblies
	inner_core = openmc.RectLattice(name="Inside of Core")
	ap = case.core.pitch; n = case.core.size
	inner_core.pitch = (ap, ap)
	inner_core.lower_left = [-ap * float(n) / 2.0] * 2
	# Make an assembly-sized universe of moderator
	mod_verse = get_mod_universe(case, fill_mat)
	# Refer to the core maps and grab the proper assemblies.
	asmap = case.core.square_maps("assembly", space='')
	# TODO:
	# Right now, I'm inserting placeholder strings.
	# What I actually want to do is insert universes containing the
	# entire assemblies. 
	
	# Quick lambda function to pass to fill_lattice()
	f = lambda a: case.assemblies[a].name if a else "mod"
	#f = lambda a: case.get_openmc_assemblies(case.assemblies[a]) if a else mod_verse
	
	print(fill_lattice(asmap, f, n))
	#inner_core.universes = fill_lattice(asmap, f, n)
	
	
	'''
	To do that, we'll need to refer to the core maps and grab the proper assemblies.
	
	For every vera_assembly in the dictionary case.assemblies, run 
	case.get_openmc_assemblies(vera_assembly). It will return a vertical column, arranged
	something like (GAP,PLUG,LAT21,PLEN,PLUG,GAP). Somewhere in this, I want to add the
	grid spacers and nozzles. The fuel lattices, spacers, and nozzles will then all be
	placed in one universe. The name of the assembly in VERA shall serve as the key 
	in the dictionary in self.openmc_assemblies.
	
	Then, iterate through case.core.square_maps() and create an array of the Universes
	by position in the core, which is passed to an OpenMC RectLattice. Ideally, this will
	have the baffle around it. Outside the baffle is fill_mat (usually "mod").
	
	Finally, zip all of that up in a universe and fill core_cell with it.
	'''
	
	
	
	# Define a root cell with the reactor vessel
	root_cell = openmc.Cell(name='root cell')
	root_cell.fill = rpv
	rpv_cyl, zbot, ztop = outer_vessel_surfs
	root_cell.region = -rpv_cyl & +zbot & -ztop
	# Define a root universe
	root_universe = openmc.Universe(universe_id=0, name='root universe')
	root_universe.add_cell(root_cell)
	geometry = openmc.Geometry()
	geometry.root_universe = root_universe
	# Export to "geometry.xml"
	geometry.export_to_xml()
	
	
	
	materials = openmc.Materials(case.openmc_materials.values())
	materials.default_xs = '71c'
	materials.export_to_xml()
	
	
	
	
	
	
	
	'''root_cell.fill = fillcell
	
	# Handle boundary conditions
	if len(bounds) == 3:
		radius, min_z, max_z = bounds
		root_cell.region = -radius & +min_z & -max_z
	elif len(bounds) == 6:
		min_x, max_x, min_y, max_y, min_z, max_z = bounds
		# Create boundary planes to surround the geometry
		root_cell.region = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	
	
	
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
	
	
	#print(case.openmc_surfaces)
	#print(case.openmc_cells)
	print(fillcell)
	 '''

def get_mod_universe(case, fill):
	''''Create a blank (moderator) assembly'''
	hpitch = case.core.pitch * float(case.core.size) / 2.0
	min_x = openmc.XPlane(x0=-hpitch)
	max_x = openmc.XPlane(x0=+hpitch)
	min_y = openmc.YPlane(y0=-hpitch)
	max_y = openmc.YPlane(y0=+hpitch)
	
	mod_cell_universe = openmc.Universe(name='mod assembly universe')
	mod_cell = openmc.Cell(name='mod')
	mod_cell.fill = case.openmc_materials[fill]
	mod_cell.region = +min_x & -max_x & +min_y & -max_y
	mod_cell_universe.add_cell(mod_cell)
	
	return mod_cell_universe

if __name__ == "__main__":
	file = "../gold/p7.xml.gold"
	convert_to_openmc(file)
	
	
	