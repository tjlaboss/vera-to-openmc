# Convert Common
#
# Functions common to all or most of the 'convert_[type].py' modules

import sys
import os
from xml.etree.ElementTree import ParseError
import openmc
import openmc.stats
import vera_to_openmc
import pwr
import tallies

_OPTS = ("--particles", "--batches", "--max-batches", "--inactive",
         "--export", "--help", "-h", "--tallies", "--plots")

_HELP_STR = """
USAGE:
python convert.py [case_file] [--options]
-----------------------------------------------------------
Options:
    --help, -h              : display this help message and exit
    --export [/path/to/dir] : directory where to export the xml
    --tallies [true/false]  : whether to export the default tallies
    --plots [true/false]    : whether to export the default plots

Monte Carlo Parameters:
    --particles             : number of particles per batch
    --inactive              : number of inactive batches to run
    --batches               : number of total batches to run
                              unless tally triggers are active
    --max_batches           : maximum number of batches to run
                              if tally triggers are active
"""


def _arg_val(string):
	return sys.argv[sys.argv.index(string) + 1]


def plot_xy_lattice(pitch, z=0, width=1250, height=1250, plot_name='Plot-materials-xy'):
	# Plot properties for this test
	plot = openmc.Plot(plot_id=1)
	plot.filename = plot_name
	plot.origin = [0, 0, z]
	plot.width = [pitch - .01, pitch - .01]
	plot.pixels = [width, height]
	plot.color = 'mat'
	# Instantiate a Plots collection--don't export to "plots.xml" just yet
	plot_file = openmc.Plots([plot])
	return plot_file


def get_case(case_file):
	"""Outputs:
		case_number:    int in {1, 2, 3, 4, 5}; describes which kind of problem it is
		                (2D pincell, 2D lattice, 3D assembly, 3D mini-core, 3D full-core)
		case:           instance of vera_to_openmc.MC_Case
	"""
	# Process the Case and determine what kind it is (pincell, lattice, assembly, or fullcore)
	try:
		case = vera_to_openmc.MC_Case(case_file)
	except ParseError as e:
		raise ParseError("Could not parse {}; \
			is it a valid XML file?\n{}".format(case_file, e))
	except IOError as e:
		raise IOError("Could not open {}: {}".format(case_file, e))
	else:
		# Select an assembly
		if len(case.assemblies) > 1:
			# This is a full-core or mini-core.
			# Determine which from boundary conditions
			bc = case.core.bc["rad"]
			if bc == "vacuum":
				# This is a full-core
				return 5, case
			elif bc in ("reflecting", "reflective"):
				# This is a mini-core
				return 4, case
			else:
				errstr = """\
	"Unable to determine whether this is Problem 4 (mini-core)
	or Problem 5 (full-core) from the boundary conditions.
	Please check your BCs: case.core.bc["rad"] = {}""".format(bc)
				raise ParseError(errstr)
		else:
			# This is an assembly, lattice, or pincell
			# Examine the 1 assembly and see
			assembly0 = list(case.assemblies.values())[0]
			if len(assembly0.cellmaps) > 1:
				# This is a 3D assembly
				return 3, case
			else:
				# This is a lattice or pincell
				# Examine the 1 cellmap and see
				cellmap0 = list(assembly0.cellmaps.values())[0]
				if len(cellmap0) > 1:
					# This is a 2D lattice
					return 2, case
				else:
					# This is a 2D pincell
					return 1, case


def get_monte_carlo(mc, args):
	"""Get the Monte Carlo parameters from the command line.
	Anything not provided will be populated from the default
	values in the XML.
	
	Inputs:
		mc:             instance of objects.MonteCarlo to use
						for default values.
		args:           list of the command line arguments
	
	Outputs:
		particles:      int; the number of particles/batch
		inactive:       int; the number of inactive batches
		min_batches:    int; the number of batches to run
		max_batches:    int; the maximum number of batches to
						run if tally triggers are active.
	"""
	
	# Monte Carlo parameters
	# Get some from the command line, set them, and then double-check
	if "--particles" in args:
		particles = int(_arg_val("--particles"))
	else:
		particles = mc.particles
	if "--batches" in args:
		min_batches = int(_arg_val("--batches"))
	else:
		min_batches = mc.min_batches
		mc.max_batches = 10*min_batches
	if "--max-batches" in args:
		max_batches = int(_arg_val("--max-batches"))
	else:
		max_batches = mc.max_batches
	if "--inactive" in args:
		inactive = int(_arg_val("--inactive"))
	else:
		inactive = mc.inactive
	# Sanity check
	errs = 0
	errstr = "\n"
	if inactive >= min_batches:
		errs += 1
		errstr += "The number of inactive matches cannot \
be more than the number of batches.\n"
	if min_batches > max_batches:
		errs += 1
		errstr += "The maximum number of batches must be at least \
the minimum number of batches.\n"
	if errs:
		raise ValueError(errstr)
	
	return particles, inactive, min_batches, max_batches


def get_export_location(case_file, args):
	# Default export location
	if "--export" in args:
		folder = _arg_val("--export")
	else:
		folder = case_file.split('/')[-1].split('.')[0]
	if not os.path.exists(folder):
		# Let it fail here if it can't create
		os.makedirs(folder)
	elif os.listdir(folder):
		answer = None
		astr = "{} exists and is not empty; export anyway? [y/n] ".format(folder)
		while answer not in ("y", "n", "yes", "no"):
			answer = input(astr).lower()
		if answer[0] == "n":
			sys.exit("Process aborted.")
	return folder


def get_whether_to(keyword, args):
	if keyword in args:
		to_tally = str(_arg_val(keyword)).lower()
		if to_tally == "true":
			return True
		elif to_tally == "false":
			return False
		else:
			errstr = 'Arugment {} must be "true" or "false"'.format(keyword)
			raise ValueError(errstr)
	else:
		return True
		

def get_args():
	"""Handle the command line arguments
	
	"""
	args = sys.argv
	
	# Quit if the user requests the help message
	if ("-h" in args) or ("--help" in args):
		print(_HELP_STR)
		raise sys.exit()
	
	# Remember, args[0] is this script itself!
	if len(args) >= 2:
		case_file = args[1]
	else:
		case_file = input("Enter the location of the VERA xml input: ")
	
	# Check if there are erroneous options
	errs = 0
	errstr = "\nUnknown arguments:"
	for i in range(1, len(args)):
		arg = args[i]
		if arg not in _OPTS and arg != case_file:
			if args[i - 1] not in _OPTS:
				errs += 1
				errstr += '\n' + str(arg)
	if errs:
		raise ValueError(errstr)
	
	# Probably move these elsewhere?
	prob, case = get_case(case_file)
	particles, inactive, min_batches, max_batches = get_monte_carlo(case.mc, args)
	folder = get_export_location(case_file, args)
	to_tally = get_whether_to("--tally", args)
	to_plot = get_whether_to("--plot", args)
	
	if prob == 1:
		conv = Pincell_Conversion(case, particles, inactive, min_batches,
		                          max_batches, folder, False, to_plot)
		conv.export_to_xml()
	elif prob == 2:
		conv = Lattice_Conversion(case, particles, inactive, min_batches,
		                          max_batches, folder, to_tally, to_plot)
		conv.export_to_xml()
	elif prob == 3:
		conv = Assembly_Conversion(case, particles, inactive, min_batches,
		                           max_batches, folder, to_tally, to_plot)
		conv.export_to_xml()
	else:
		return prob, case, particles, inactive, min_batches, max_batches, folder


class Conversion(object):
	"""Conversion of
	
	"""
	def __init__(self, case, particles, inactive, min_batches, max_batches,
	             folder, to_tally=True, to_plot=False):
		self._case = case
		self._particles = particles
		self._inactive = inactive
		self._min_batches = min_batches
		self._max_batches = max_batches
		self.folder = folder
		self._pitch = self._get_pitch()
		
		self._assembly0 = list(self._case.assemblies.values())[0]
		
		self._geometry = openmc.Geometry()
		self._geometry.root_universe = self._get_root_universe()
	
		matlist = [value for (key, value) in sorted(case.openmc_materials.items())]
		self._materials = openmc.Materials(matlist)
		
		self._settings = openmc.Settings()
		self._settings.temperature = {"method": "interpolation", "multipole": True}
		self._settings.output = {'tallies': to_tally}
		self._settings.batches = min_batches
		self._settings.trigger_max_batches = max_batches
		self._settings.inactive = inactive
		self._settings.particles = particles
		self._settings.source = self._get_source_box()
		
		if to_tally:
			self._tallies = openmc.Tallies()
			self._set_case_tallies()
		else:
			self._tallies = None
		
		if to_plot:
			self._plots = openmc.Plots()
			self._set_case_plots()
		else:
			self._plots = None
	
	def _get_root_universe(self):
		pass
	
	def _get_source_box(self):
		pass
	
	def _get_pitch(self):
		pass
	
	def _set_case_tallies(self):
		pass
	
	def _set_case_plots(self):
		pass
	
	def get_cubic_boundaries(self, zrange, bounds = ("reflective",)*6):
		"""Get a cuboid region
		
		Paramters:
		----------
		zrange:     list/tuple of floats; [zbot, ztop]
		bounds:     list/tuple of strs describing the boundary conditions
					on each edge; [min_x, max_x, min_y, max_y, min_z, max_z]
					[Default: ("reflective",)*6 ]
		
		Returns:
		--------
		region:     intersection of the 6 edges
		"""
		p = self._pitch
		min_x = openmc.XPlane(x0=-p/2.0, boundary_type=bounds[0], name="Bound - min x")
		max_x = openmc.XPlane(x0=+p/2.0, boundary_type=bounds[1], name="Bound - max x")
		min_y = openmc.YPlane(y0=-p/2.0, boundary_type=bounds[2], name="Bound - min y")
		max_y = openmc.YPlane(y0=+p/2.0, boundary_type=bounds[3], name="Bound - max y")
		min_z = openmc.ZPlane(z0=zrange[0], boundary_type=bounds[4], name="Bound - min z")
		max_z = openmc.ZPlane(z0=zrange[1], boundary_type=bounds[5], name="Bound - max z")
		region = +min_x & -max_x & +min_y & -max_y & +min_z & -max_z
		return region
	
	def export_to_xml(self):
		self._materials.export_to_xml(self.folder + "/materials.xml")
		self._geometry.export_to_xml(self.folder + "/geometry.xml")
		self._settings.export_to_xml(self.folder + "/settings.xml")
		if self._tallies:
			self._tallies.export_to_xml(self.folder + "/tallies.xml")
		self._plots.export_to_xml(self.folder + "/plots.xml")


class InsertMixin(object):
	"""Class containing the add_insertions and add_spacergrids
	methods as used by single-assembly cases (for example,
	Probem 2: 2D lattice and Problem 3: 3D assembly)"""
	
	def __init__(self):
		self._case = None
		self._assembly0 = None
		pass
	
	def _add_insertions(self):
		# Add insertions as necessary
		insertion_maps = (self._case.core.insert_map,
		                  self._case.core.control_map,
		                  self._case.core.detector_map)
		for coremap in insertion_maps:
			if coremap:
				insert_key = coremap[0][0]
				if insert_key != "-":  # indicates no insertion in VERA
					if insert_key in self._case.inserts:
						insertion = self._case.inserts[insert_key]
					elif insert_key in self._case.detectors:
						insertion = self._case.detectors[insert_key]
					elif insert_key in self._case.controls:
						insertion = self._case.controls[insert_key]
					else:
						print(self._case.inserts)
						raise KeyError("Unknown key:", insert_key)
					self._assembly0.add_insert(insertion)
		
		# pwr_asmbly = self._case.get_openmc_assembly(self._assembly0)
		
		# The last cell of the universe should contain the moderator.
		# We need to get the key to this before adding any more cells.
		# mod_key = list(asmbly_universe.cells.keys())[-1]
		layers = self._case.get_openmc_lattices(self._assembly0)
		lattice = layers[0]
		return lattice
	
	def _add_spacergrids(self, lattice):
		sg = list(self._assembly0.spacergrids.values())[0]
		mat = self._case.get_openmc_material(sg.material, asname=self._assembly0.name)
		grid = pwr.SpacerGrid(sg.name, sg.height, sg.mass, mat,
		                      self._assembly0.pitch, self._assembly0.npins)
		lattice = pwr.add_grid_to(lattice, grid, self._case.counter,
		                          self._case.openmc_xplanes, self._case.openmc_yplanes)
		return lattice


class Pincell_Conversion(Conversion):
	def _get_pitch(self):
		return self._assembly0.pitch
	
	def _get_root_universe(self):
		"""Fill the root universe with the pincell universe"""
		root_universe = openmc.Universe(universe_id=0, name="root universe")
		pincell = list(self._assembly0.cells.values())[0]
		root_cell = openmc.Cell(cell_id=0, name="root cell")
		root_cell.fill = self._case.get_openmc_pincell(pincell)
		root_cell.region = self.get_cubic_boundaries(zrange=(0.0, 1.0))
		root_universe.add_cell(root_cell)
		return root_universe
		
	def _get_source_box(self):
		# Create an initial uniform spatial source distribution over fissionable zones
		p = self._pitch
		lleft = (-p/2.0, -p/2.0, 0.0)
		uright = (+p/2.0, +p/2.0, 1.0)
		uniform_dist = openmc.stats.Box(lleft, uright, only_fissionable=True)
		return openmc.source.Source(space=uniform_dist)
	
	def _set_case_plots(self):
		plot = openmc.Plot()
		plot.filename = 'Plot-materials-xy'
		plot.origin = [0, 0, 0.5]
		plot.width = [self._pitch - .01, ]*2
		plot.pixels = [600, 600]
		plot.color_by = 'material'
		plot.colors = self._case.col_spec
		self._plots.add_plot(plot)


class Lattice_Conversion(Conversion, InsertMixin):
	def _get_pitch(self):
		return self._case.core.pitch
	
	def _get_root_universe(self):
		"""Fill the root universe with the pincell universe"""
		root_universe = openmc.Universe(universe_id=0, name="root universe")
		lattice = self._add_insertions()
		if self._assembly0.spacergrids:
			lattice = self._add_spacergrids(lattice)
		root_cell = openmc.Cell(cell_id=0, name="root cell")
		root_cell.fill = lattice
		root_cell.region = self.get_cubic_boundaries(zrange=(0.0, 1.0))
		root_universe.add_cell(root_cell)
		return root_universe
	
	def _get_source_box(self):
		# Create an initial uniform spatial source distribution over fissionable zones
		p = self._pitch
		lleft = (-p/2.0, -p/2.0, 0.0)
		uright = (+p/2.0, +p/2.0, 1.0)
		uniform_dist = openmc.stats.Box(lleft, uright, only_fissionable=True)
		return openmc.source.Source(space=uniform_dist)

	def _set_case_tallies(self):
		lattice = self._case.get_openmc_lattices(self._assembly0)[0]
		tallies.get_lattice_tally(lattice, scores=["fission"], tallies_file=self._tallies)
		
	def _set_case_plots(self):
		plot = openmc.Plot()
		plot.filename = 'Plot-materials-xy'
		plot.origin = [0, 0, 0.5]
		plot.width = [self._pitch - .01, ]*2
		plot.pixels = [1200, 1200]
		plot.color_by = 'material'
		plot.colors = self._case.col_spec
		self._plots.add_plot(plot)


class Assembly_Conversion(Conversion, InsertMixin):
	def _get_pitch(self):
		return self._case.core.pitch
	
	def _get_root_universe(self):
		"""Fill the root universe with the pincell universe"""
		root_universe = openmc.Universe(universe_id=0, name="root universe")
		lattice = self._case.get_openmc_lattices(self._assembly0)[0]
		root_cell = openmc.Cell(cell_id=0, name="root cell")
		root_cell.fill = lattice
		zbot = self._assembly0.bottom.z0
		ztop = self._assembly0.top.z0
		root_cell.region = self.get_cubic_boundaries(zrange=(zbot, ztop))
		root_universe.add_cell(root_cell)
		return root_universe
	
	def _get_source_box(self):
		# Create an initial uniform spatial source distribution over fissionable zones
		p = self._pitch
		zrange = self._assembly0.z_active
		lleft = (-p/2.0, -p/2.0, zrange[0])
		uright = (+p/2.0, +p/2.0, zrange[1])
		uniform_dist = openmc.stats.Box(lleft, uright, only_fissionable=True)
		return openmc.source.Source(space=uniform_dist)
	
	def _set_case_tallies(self):
		assembly = list(self._case.assemblies.values())[0]
		lattice = self._case.get_openmc_lattices(assembly)[0]
		tallies.get_lattice_tally(lattice, scores=["fission"], tallies_file=self._tallies)
	
	def _set_case_plots(self):
		plot = openmc.Plot()
		plot.filename = 'Plot-materials-xy'
		plot.origin = [0, 0, 0.5]
		plot.width = [self._pitch - .01, ]*2
		plot.pixels = [1200, 1200]
		plot.color_by = 'material'
		plot.colors = self._case.col_spec
		self._plots.add_plot(plot)

if __name__ == "__main__":
	# test
	print(get_args())
	print("Exported successfully.")
