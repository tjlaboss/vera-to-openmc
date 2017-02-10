# tests.py
#
# Use the functions below to test various features of the vera converter

import sys; sys.path.append('..')
import openmc
import vera_to_openmc



def test_pincell(case_file = "../gold/1c.xml.gold", aname="", pname = ""):
	"""Create and run a simple pincell.
	
	True pincell cases (those starting with a '1') only have 1 assembly consisting of 1 pin cell.
	In that case, just take the first (and only) entry in case.assemblies and assembly.cells.
	
	This function may also be used to run individual pin cells that are parts of larger cases.
	In this event, the user must specify the assembly name 'aname' in which the pincell lies,
	and the pincell name 'pname' referring to the cell itself.
	
	Inputs:
		case_file:		string of the location on the filesystem of the XML.GOLD input
		aname:			string; unique key of the Assembly in which the cell lies.
		pname:			string; unique key of the Cell in the Assembly 
	"""
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
	
	
	
	plot_lattice(assembly1.pitch, 1, col_spec = pincell_case.col_spec)
	"""# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = 'materials-xy'
	plot.origin = [0, 0, 0]
	plot.width = [01.5, 01.5]
	plot.pixels = [1250, 1250]
	plot.color = 'mat'
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()"""
	
	bounds = set_cubic_boundaries(assembly1.pitch, ("reflective",)*6)

	return pincell_case, openmc_cell1, assembly1.pitch, 1, bounds, [0.0, 1.0]

def test_lattice(case_file = "../gold/p7.xml.gold", aname=''):
	"""Create and run a more complicated lattice
	
	Plain lattice cases (those starting with a '2') are composed of a 2D lattice extended 1 cm
	in the Z axis. In this case, just take the first (and only) entry in case.assemblies.
	
	This function may also be used to run individual pin cells that are parts of larger cases.
	In this event, the user must specify the lattice/assembly name 'aname'.
	
	!! TODO !! 
	Edit this method to actually be able to run arbitrary assemblies from full-core cases. 
	
	Inputs:
		case_file:		string of the location on the filesystem of the XML.GOLD input
		aname:			string; unique key of the Assembly to run.
	"""
	
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
			insert_key = coremap.square_map[0][0]
			if insert_key != "-":		# indicates no insertion in VERA
				if insert_key in ascase.inserts:
					insertion = ascase.inserts[insert_key]
				elif insert_key in ascase.detectors:
					insertion = ascase.detectors[insert_key]
				elif insert_key in ascase.controls:
					insertion = ascase.controls[insert_key]
				else:
					print(ascase.inserts)
					raise KeyError("Unknown key:", insert_key)
				as2.add_insert(insertion)
		
	openmc_as2_layers = ascase.get_openmc_lattices(as2) 
	some_asmbly = openmc_as2_layers[0]
	
	'''
	Spacer test; doesn't work
	import pwr
	print(ascase.openmc_materials.keys())
	spacergrid = pwr.SpacerGrid("key", 3.81, 875, ascase.get_openmc_material("ss"), 1.26, 17)
	some_asmbly = pwr.assembly.add_grid_to(some_asmbly, 1.26, 17, spacergrid)
	'''
	
	plot_lattice(apitch, 1, col_spec = ascase.col_spec)
	bounds = set_cubic_boundaries(apitch)
	
	return ascase, some_asmbly, apitch, as2.pitch, as2.npins, bounds, [0.0, 1.0]


def test_assembly(case_file = "../gold/3a.xml.gold", aname='assy'):
	"""Create and run a single 3D assembly case
	
	
	TODO: Allow the user to test any assembly from full-core cases as well. 
	
	Inputs:
		case_file: 		string of the location on the filesystem of the XML.GOLD input
		aname:			string; unique key of the Assembly to run.
	"""
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
			#print(coremap)
			insert_key = coremap[0][0]
			if insert_key != "-":		# indicates no insertion in VERA
				if insert_key in ascase.inserts:
					insertion = ascase.inserts[insert_key]
				elif insert_key in ascase.detectors:
					insertion = ascase.detectors[insert_key]
				elif insert_key in ascase.controls:
					insertion = ascase.controls[insert_key]
				else:
					print(ascase.inserts)
					raise KeyError("Unknown key:", insert_key)
				as3.add_insert(insertion)
		
	pwr_asmbly = ascase.get_openmc_assembly(as3)
	asmbly_universe = pwr_asmbly.universe
	# The last cell of the universe should contain the moderator.
	# We need to get the key to this before adding any more cells.
	mod_key = list(asmbly_universe.cells.keys())[-1]

	lplate = ascase.core.bot_refl
	uplate = ascase.core.top_refl
	if lplate:
		# Add the lower core plate
		zbot = pwr_asmbly.bottom.z0 - lplate.thick
		bot_surf = openmc.ZPlane(ascase.counter.add_surface(), z0 = zbot, name = "Bottom")
		bot_plate_cell = openmc.Cell(ascase.counter.add_cell(), "Lower Core Plate")
		bot_plate_cell.fill = ascase.get_openmc_material(lplate.material)
		bot_plate_cell.region = (pwr_asmbly.wall_region & +bot_surf & -pwr_asmbly.bottom)
		asmbly_universe.add_cell(bot_plate_cell)
	else:
		print("Warning: No lower core plate found.")
		zbot = pwr_asmbly.bottom.z0
		bot_surf = pwr_asmbly.bottom
	if uplate:
		# Add the upper core plate
		ztop = pwr_asmbly.top.z0 + uplate.thick
		top_surf = openmc.ZPlane(ascase.counter.add_surface(), z0 = ztop, name = "Top")
		top_plate_cell = openmc.Cell(ascase.counter.add_cell(), "Upper Core Plate")
		top_plate_cell.fill = ascase.get_openmc_material(uplate.material)
		top_plate_cell.region = (pwr_asmbly.wall_region & +pwr_asmbly.top & -top_surf)
		asmbly_universe.add_cell(top_plate_cell)
	else:
		print("Warning: No upper core plate found.")
		ztop = pwr_asmbly.top.z0
		top_surf = pwr_asmbly.top
	
	asmbly_universe.cells[mod_key].region = (~pwr_asmbly.wall_region | -bot_surf | +top_surf)

	zrange_total = [zbot, ztop]			# zrange for boundary conditions
	[z0, z1] = pwr_asmbly.z_active		# zrange for fission source
	plot_assembly(apitch, as3.npins, z = (z1 - z0)/2.0, col_spec = ascase.col_spec)
	bounds = set_cubic_boundaries(apitch, ("reflective",)*4 + ("vacuum",)*2, zrange_total)
	
	return ascase, asmbly_universe, apitch, as3.pitch, as3.npins, bounds, [z0, z1]


def test_core_lattice(case_file = "../gold/p7.xml.gold"):
	"""Inputs:
		case_file	
	"""
	
	case = vera_to_openmc.MC_Case(case_file)
	lat = case.get_openmc_core_lattice()
	apitch = case.core.pitch
	r = apitch*case.core.size
	
	plot_lattice(apitch, case.core.size, z = 75, col_spec = case.col_spec)
	zrange_total = [20, 380]
	bounds = set_cubic_boundaries(r, ("reflective",)*4 + ("vacuum",)*2, zrange_total)
	
	return case, lat, r, apitch, case.core.size, bounds, zrange_total


def test_core(case_file = "../gold/p7.xml.gold"):
	"""Create a full core geometry
	
	"""
	core_case = vera_to_openmc.MC_Case(case_file)
	c = core_case.core
	apitch = c.pitch
	r = max(c.vessel_radii)
	
	'''
	if c.size == 1:
		# Single assembly case--probably should be rewritten
		aname = c.asmbly.square_map()[0][0].lower()
		asmbly = core_case.assemblies[aname]
		n = asmbly.npins; pitch = asmbly.pitch; 
		plot_lattice(pitch, n)
		fillcore = core_case.get_openmc_assemblies(asmbly)[0]
		bounds = (c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["top"], c.bc["top"])
		boundaries = set_cubic_boundaries(pitch, n, bounds)
	'''
		
	reactor_universe, boundaries = core_case.build_reactor()
	pwr_asmbly = list(core_case.openmc_assemblies.values())[0]
	zrange = pwr_asmbly.z_active  # zrange for fission source
	ppitch = pwr_asmbly.pitch
	
	#PLOT
	#heights = [127, 188]
	#xynames = ["grid", "fuel"]
	plot_core(r)
		
	#case, fillcell, apitch, ppitch, n, bounds, zrange
	return core_case, reactor_universe, apitch, ppitch, c.size, boundaries, zrange


def set_cubic_boundaries(pitch, bounds = ('reflective',) * 6, zrange = [0.0, 1.0]):
	"""Inputs:
		pitch:		float; pitch between fuel pins
		n:			int; number of fuel pins in an assembly (usually 1 or 17)
		bounds:		tuple/list of strings with len=6, containing the respective
					boundary types for min/max x, y, and z (default: all reflective)
		zrange: 	list of floats with len=2 describing the minimum and maximum z values
					of the geometry
	Outputs:
		a tuple of the openmc X/Y/ZPlanes for the min/max x, y, and z boundaries
	"""
	
	min_x = openmc.XPlane(x0 = -pitch / 2.0, boundary_type = bounds[0], name = "Bound - min x")
	max_x = openmc.XPlane(x0 = +pitch / 2.0, boundary_type = bounds[1], name = "Bound - max x")
	min_y = openmc.YPlane(y0 = -pitch / 2.0, boundary_type = bounds[2], name = "Bound - min y")
	max_y = openmc.YPlane(y0 = +pitch / 2.0, boundary_type = bounds[3], name = "Bound - max y")
	min_z = openmc.ZPlane(z0 = zrange[0], boundary_type = bounds[4], name = "Bound - min z")
	max_z = openmc.ZPlane(z0 = zrange[1], boundary_type = bounds[5], name = "Bound - max z")
	
	return min_x, max_x, min_y, max_y, min_z, max_z


def plot_lattice(pitch, npins = 1, z = 0, width=1250, height=1250, col_spec = {}):
	# Plot properties for this test
	plot = openmc.Plot(plot_id = 1)
	plot.filename = 'Plot-materials-xy'
	plot.origin = [0, 0, z]
	plot.width = [npins * pitch - .01, ] * 2
	plot.pixels = [width, height]
	plot.color = 'mat'
	plot.col_spec = col_spec
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot])
	plot_file.export_to_xml()


def plot_assembly(pitch, npins = 1, z = 188.0, width = 1250, height = 1250, col_spec = {}):
	# Fuel-xy (no grid)
	plot1 = openmc.Plot(plot_id = 1)
	plot1.filename = 'Plot-fuel-xy'
	plot1.origin = [0, 0, z]
	plot1.basis = "xy"
	plot1.width = [pitch - .01, pitch - .01]
	plot1.pixels = [width, height]
	plot1.color = 'mat'
	plot1.col_spec = col_spec
	
	# Gridded fuel:MID
	plot2 = openmc.Plot(plot_id = 2)
	plot2.filename = 'Plot-mid-grid-xy'
	plot2.origin = [0, 0, 127]
	plot2.basis = "xy"
	plot2.width = [pitch - .01, pitch - .01]
	plot2.pixels = [width, height]
	plot2.color = 'mat'
	plot2.col_spec = col_spec
	
	# Gridded fuel:END
	plot3 = openmc.Plot(plot_id = 3)
	plot3.filename = 'Plot-end-grid-xy'
	plot3.origin = [0, 0, 388]
	plot3.basis = "xy"
	plot3.width = [pitch - .01, pitch - .01]
	plot3.pixels = [width, height]
	plot3.color = 'mat'
	plot3.col_spec = col_spec
	
	# YZ
	plot4 = openmc.Plot(plot_id = 4)
	plot4.filename = 'Plot-yz'
	plot4.origin = [0, 0, 200]
	plot4.width = [pitch - .01, 410]
	plot4.pixels = [width, height]
	plot4.basis = "yz"
	plot4.color = 'mat'
	plot4.col_spec = col_spec
	
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots([plot1, plot2, plot3, plot4])
	plot_file.export_to_xml()


def test_core(case_file = "../gold/p7.xml.gold"):
	"""Create a full core geometry

	"""
	core_case = vera_to_openmc.MC_Case(case_file)
	c = core_case.core
	apitch = c.pitch
	r = max(c.vessel_radii)
	
	'''
	if c.size == 1:
		# Single assembly case--probably should be rewritten
		aname = c.asmbly.square_map()[0][0].lower()
		asmbly = core_case.assemblies[aname]
		n = asmbly.npins; pitch = asmbly.pitch;
		plot_lattice(pitch, n)
		fillcore = core_case.get_openmc_assemblies(asmbly)[0]
		bounds = (c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["rad"], c.bc["top"], c.bc["top"])
		boundaries = set_cubic_boundaries(pitch, n, bounds)
	'''
	
	reactor_universe, boundaries = core_case.build_reactor()
	pwr_asmbly = list(core_case.openmc_assemblies.values())[0]
	zrange = pwr_asmbly.z_active  # zrange for fission source
	ppitch = pwr_asmbly.pitch
	
	# PLOT
	# heights = [127, 188]
	# xynames = ["grid", "fuel"]
	plot_core(r, col_spec = core_case.col_spec)
	
	return core_case, reactor_universe, apitch, ppitch, c.size, boundaries, zrange


def plot_core(radius, width = 2500, height = 2500, col_spec = {},
              zs = [127.0, ], xynames = ["grid", ],
              xs = [0, ], yznames = ["center"],
              ys = [], xznames = [],
              ):
	plot_list = []
	for k in range(len(zs)):
		z = zs[k]
		plot = openmc.Plot(plot_id = k + 1)
		plot.basis = "xy"
		plot.filename = "Plot-" + xynames[k] + "-xy"
		plot.origin = (0, 0, z)
		plot.width = (2 * radius - .01,) * 2
		plot.pixels = [width, height]
		plot.color = "mat"
		plot.col_spec = col_spec
		plot_list.append(plot)
	for i in range(len(xs)):
		x = xs[i]
		plot = openmc.Plot(plot_id = k + i + 2)
		plot.basis = "yz"
		plot.filename = "Plot-" + yznames[i] + "-yz"
		plot.origin = (x, 0, 200)  # FIXME: detect right z height
		plot.width = (2 * radius - .01,) * 2
		plot.pixels = [width, height]
		plot.color = "mat"
		plot.col_spec = col_spec
		plot_list.append(plot)
	
	# Instantiate a Plots collection and export to "plots.xml"
	plot_file = openmc.Plots(plot_list)
	plot_file.export_to_xml()


def set_settings(npins, pitch, bounds, zrange, min_batches, max_batches, inactive, particles):
	"""Create the OpenMC settings and export to XML.
	
	Inputs:
		npins:		int; number of pins across an assembly. Use 1 for a pin cell,
					and the lattice size for an assembly (usually 17).
		pitch:		float; distance in cm between two PIN CELLS (not assemblies).
					Used for detecting fissionable zones.
		bounds:		iterable (tuple, list, etc.) of the X, Y, and Z bounding Planes:
					 (min_x, max_x, min_y, max_y, min_z, max_z)
		zrange:		list of floats describing the minimum and maximum z location
					of fissionable material
	"""
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
	#case, fillcell, apitch, ppitch, n, bounds, zrange = test_lattice("../gold/2f.xml.gold")
	case, fillcell, apitch, ppitch, n, bounds, zrange = test_assembly("../gold/3a.xml.gold")
	#case, fillcell, apitch, ppitch, n, bounds, zrange = test_core_lattice("../gold/p7.xml.gold")
	#case, fillcell, apitch, ppitch, n, bounds, zrange = test_core("../gold/p7.xml.gold")
	
	print("\nGenerating XML")
	
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

	
