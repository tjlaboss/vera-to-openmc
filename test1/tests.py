# tests.py
#
# Use the functions below to test various features of the vera converter

import sys; sys.path.append('..')
import openmc
import vera_to_openmc



def test_pincell(case_file = "../gold/1c.xml.gold", aname="", pname = ""):
	'''Create and run a simple pincell.
	
	True pincell cases (those starting with a '1') only have 1 assembly consisting of 1 pin cell.
	In that case, just take the first (and only) entry in case.assemblies and assembly.cells.
	
	This function may also be used to run individual pin cells that are parts of larger cases.
	In this event, the user must specify the assembly name 'aname' in which the pincell lies,
	and the pincell name 'pname' referring to the cell itself.
	
	Inputs:
		case_file:		string of the location on the filesystem of the XML.GOLD input
		aname:			string; unique key of the Assembly in which the cell lies.
		pname:			string; unique key of the Cell in the Assembly 
	'''
	pincell_case = vera_to_openmc.MC_Case(case_file)
	
	assembly1 = list(pincell_case.assemblies.values())[0]
	veracell1 = list(assembly1.cells.values())[0]
	
	if aname and pname:
		try:
			assembly1 = pincell_case.assemblies[aname.lower()]
			veracell1 = assembly1.cells[pname.lower()]
		except KeyError as e:
			print("Key", e, "not found; autodetecting.")
			print("Using Assembly:", assembly1.name, "and Cell:", veracell1.name)
	
	openmc_cell1 = pincell_case.get_openmc_pincell(veracell1)
	
	
	
	plot_lattice(assembly1.pitch, 1)
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
	
	bounds = set_cubic_boundaries(assembly1.pitch, ("reflective",)*6)

	return pincell_case, openmc_cell1, assembly1.pitch, 1, bounds, [0.0, 1.0]


def test_lattice(case_file = "../gold/p7.xml.gold", aname=''):
	'''Create and run a more complicated lattice
	
	Plain lattice cases (those starting with a '2') are composed of a 2D lattice extended 1 cm
	in the Z axis. In this case, just take the first (and only) entry in case.assemblies.
	
	This function may also be used to run individual pin cells that are parts of larger cases.
	In this event, the user must specify the lattice/assembly name 'aname'.
	
	!! TODO !! 
	Edit this method to actually be able to run arbitrary assemblies from full-core cases. 
	
	Inputs:
		case_file:		string of the location on the filesystem of the XML.GOLD input
		aname:			string; unique key of the Assembly to run.
	'''
	
	ascase = vera_to_openmc.MC_Case(case_file)
	as2 = list(ascase.assemblies.values())[0]
	if aname:
		try:
			as2 = ascase.assemblies[aname.lower()]
		except KeyError as e:
			print("Key", e, "not found; autodetecting.")
			print("Using Assembly:", as2.name)
	
	apitch = ascase.core.pitch
	
	
	
	# Add insertions as necessary
	insertion_maps = (ascase.core.insert_map, ascase.core.control_map, ascase.core.detector_map) 
	for coremap in insertion_maps:
		if coremap:
			insert_key = coremap[0][0]
			if insert_key != "-":		# indicates no insertion in VERA
				insertion = ascase.inserts[insert_key]
				as2.add_insert(insertion)
		# TODO: For [CONTROL] case, handle stroke, maxsteps
		# Doesn't matter for assembly benchmarks, but does for full core
		
	openmc_as2_layers = ascase.get_openmc_lattices(as2) 
	some_asmbly = openmc_as2_layers[0]
	
	'''
	Spacer test; doesn't work
	import pwr
	print(ascase.openmc_materials.keys())
	spacergrid = pwr.SpacerGrid("key", 3.81, 875, ascase.get_openmc_material("ss"), 1.26, 17)
	some_asmbly = pwr.assembly.add_grid_to(some_asmbly, 1.26, 17, spacergrid)
	'''
	
	plot_lattice(apitch, as2.npins)
	bounds = set_cubic_boundaries(apitch)
	
	return ascase, some_asmbly, apitch, as2.pitch, as2.npins, bounds, [0.0, 1.0]



def test_assembly(case_file = "../gold/3a.xml.gold", aname='assy'):
	'''Create and run a single 3D assembly case
	
	
	TODO: Allow the user to test any assembly from full-core cases as well. 
	
	Inputs:
		case_file: 		string of the location on the filesystem of the XML.GOLD input
		aname:			string; unique key of the Assembly to run.
	'''
	ascase = vera_to_openmc.MC_Case(case_file)
	as3 = list(ascase.assemblies.values())[0]
	if aname:
		try:
			as3 = ascase.assemblies[aname.lower()]
		except KeyError as e:
			print("Key", e, "not found; autodetecting.")
			print("Using Assembly:", as3.name)
	
	apitch = ascase.core.pitch
	
	# Add insertions as necessary
	insertion_maps = (ascase.core.insert_map, ascase.core.control_map, ascase.core.detector_map) 
	for coremap in insertion_maps:
		if coremap:
			print(coremap)
			insert_key = coremap[0][0]
			if insert_key != "-":		# indicates no insertion in VERA
				insertion = ascase.inserts[insert_key]
				as3.add_insert(insertion)
		# TODO: For [CONTROL] case, handle stroke, maxsteps
		# Doesn't matter for assembly benchmarks, but does for full core
	
		
	some_asmbly = ascase.get_openmc_assembly(as3)
	
	# Find the top and bottom of the active region
	n = len(as3.axial_elevations)
	maxdiff = 0
	z0 = None; z1 = None
	for i in range(1, n):
		diff = as3.axial_elevations[i] - as3.axial_elevations[i-1]
		if diff > maxdiff:
			maxdiff = diff
			z0 = as3.axial_elevations[i-1]
			z1 = as3.axial_elevations[i]
	zrange_active = [z0, z1]
	# Set Z range for boundary conditions
	# FIXME: Correct this to account for core plates
	zrange_total = [0, ascase.core.height]
	
	plot_assembly(apitch, as3.npins, z = (z1 - z0)/2.0)
	bounds = set_cubic_boundaries(apitch, ("reflective",)*4 + ("vacuum",)*2, zrange_total)
	
	return ascase, some_asmbly, apitch, as3.pitch, as3.npins, bounds, zrange_active
	




def set_cubic_boundaries(pitch, bounds=('reflective',)*6, zrange = [0.0, 1.0]):
	'''Inputs:
		pitch:		float; pitch between fuel pins 
		n:			int; number of fuel pins in an assembly (usually 1 or 17)
		bounds:		tuple/list of strings with len=6, containing the respective
					boundary types for min/max x, y, and z (default: all reflective)
		zrange: 	list of floats with len=2 describing the minimum and maximum z values
					of the geometry
	Outputs:
		a tuple of the openmc X/Y/ZPlanes for the min/max x, y, and z boundaries
	'''
	
	min_x = openmc.XPlane(x0=-pitch/2.0, boundary_type=bounds[0], name = "Bound - min x")
	max_x = openmc.XPlane(x0=+pitch/2.0, boundary_type=bounds[1], name = "Bound - max x")
	min_y = openmc.YPlane(y0=-pitch/2.0, boundary_type=bounds[2], name = "Bound - min y")
	max_y = openmc.YPlane(y0=+pitch/2.0, boundary_type=bounds[3], name = "Bound - max y")
	min_z = openmc.ZPlane(z0=zrange[0],  boundary_type=bounds[4], name = "Bound - min z")
	max_z = openmc.ZPlane(z0=zrange[1],  boundary_type=bounds[5], name = "Bound - max z")
	
	return (min_x, max_x, min_y, max_y, min_z, max_z)

	
def plot_lattice(pitch, npins = 1, z = 0, width=1250, height=1250):
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'Plot-materials-xy'
	plot.origin = [0, 0, z]
	plot.width = [pitch - .01, pitch - .01]
	plot.pixels = [width, height]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()


def plot_assembly(pitch, npins = 1, z = 188, width = 1250, height = 1250):
	# Plot properties for this test
	plot1 = openmc.Plot(plot_id=1)
	plot1.filename = 'Plot-fuel-xy'
	plot1.origin = [0, 0, z]
	plot1.width = [pitch - .01, pitch - .01]
	plot1.pixels = [width, height]
	plot1.color = 'mat'
	
	#tmp
	plot2 = openmc.Plot(plot_id=2)
	plot2.filename = 'Plot-grid-xy'
	plot2.origin = [0, 0, 127]
	plot2.width = [pitch - .01, pitch - .01]
	plot2.pixels = [width, height]
	plot2.color = 'mat'
	
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot1, plot2])
	plot_file.export_to_xml()
	


def test_core(case_file = "../gold/2o.xml.gold"):
	'''Create a full core geometry
	
	THIS DOES NOT WORK AT THIS TIME.'''
	core_case = vera_to_openmc.MC_Case(case_file)
	c = core_case.core
	n = None; pitch = None
	
	if c.size == 1:
		# Single assembly case
		aname = c.asmbly.square_map()[0][0].lower()
		asmbly = core_case.assemblies[aname]
		n = asmbly.npins; pitch = asmbly.pitch; 
		plot_lattice(pitch, n)
		fillcore = core_case.get_openmc_assemblies(asmbly)[0]
		bounds = (c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["top"], c.bc["top"])
		boundaries = set_cubic_boundaries(pitch, n, bounds)
		
		
	elif c.radii:
		radius = openmc.ZCylinder(R = max(case.core.vessel_radii), boundary_type = 'vacuum')
		min_z = openmc.ZPlane(z0 = 0, boundary_type="vacuum")
		max_z = openmc.ZPlane(z0 = case.core.height, boundary_type="vacuum")
		plot_lattice(c.pitch, 2)
		
		boundaries = (radius, min_z, max_z)
	
	else:
		raise(IOError)
		
	#PLOT
		
	return core_case, fillcore, pitch, n, boundaries
	

def set_settings(npins, pitch, bounds, zrange, min_batches, max_batches, inactive, particles):
	'''Create the OpenMC settings and export to XML.
	
	Inputs:
		npins:		int; number of pins across an assembly. Use 1 for a pin cell,
					and the lattice size for an assembly (usually 17).
		pitch:		float; distance in cm between two PIN CELLS (not assemblies).
					Used for detecting fissionable zones.
		bounds:		iterable (tuple, list, etc.) of the X, Y, and Z bounding Planes:
					 (min_x, max_x, min_y, max_y, min_z, max_z)
		zrange:		list of floats describing the minimum and maximum z location
					of fissionable material
	'''
	# Instantiate a Settings object
	settings_file = openmc.Settings()
	settings_file.batches = min_batches
	settings_file.inactive = inactive
	settings_file.particles = particles
	settings_file.output = {'tallies': False}
	settings_file.trigger_active = True
	settings_file.trigger_max_batches = max_batches
	# Create an initial uniform spatial source distribution over fissionable zones
	lleft  = (-npins*pitch/2.0,)*2 + (zrange[0],)
	uright = (+npins*pitch/2.0,)*2 + (zrange[1],)
	uniform_dist = openmc.stats.Box(lleft, uright, only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()




if __name__ == "__main__":
	#case, fillcell, ppitch, n, bounds, zrange = test_pincell("../gold/1c.xml.gold")
	#case, fillcell, apitch, ppitch, n, bounds, zrange = test_lattice("../gold/2b.xml.gold")
	case, fillcell, apitch, ppitch, n, bounds, zrange = test_assembly("../gold/3b.xml.gold")
	#case, fillcell, pitch, n, bounds, zrange = test_core()
	
	matlist = [value for (key, value) in sorted(case.openmc_materials.items())]
	materials = openmc.Materials(matlist)
	materials.export_to_xml()
	
	# Create root Cell
	root_cell = openmc.Cell(name='root cell')
	root_cell.fill = fillcell
	
	# Handle boundary conditions
	if len(bounds) == 3:
		# Spherical
		radius, min_z, max_z = bounds
		root_cell.region = -radius & +min_z & -max_z
	elif len(bounds) == 6:
		# Cartesian
		min_x, max_x, min_y, max_y, min_z, max_z = bounds
		root_cell.region = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
	
	
	# Create Geometry and set root Universe
	root_universe = openmc.Universe(universe_id=0, name='root universe')
	root_universe.add_cell(root_cell)
	geometry = openmc.Geometry()
	geometry.root_universe = root_universe
	geometry.export_to_xml()
	
	
	

	
	# OpenMC simulation parameters
	'''min_batches = 275
	max_batches = min_batches*10
	inactive 	= 75
	particles 	= 200000'''
	min_batches = case.mc.min_batches
	max_batches = case.mc.min_batches
	inactive 	= case.mc.inactive
	particles 	= case.mc.particles
	set_settings(n, ppitch, bounds, zrange, min_batches, max_batches, inactive, particles)
	
	
	
	
	###DEBUG###
	
	print('\n', case)
	print(fillcell)

	
