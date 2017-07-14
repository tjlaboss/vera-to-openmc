# Convert Common
#
# Functions common to all or most of the 'convert_[type].py' modules

import sys
import os
from xml.etree.ElementTree import ParseError
import openmc
import vera_to_openmc


def _arg_val(string):
	return sys.argv[sys.argv.index(string) + 1]


def set_cubic_boundaries(pitch, bounds=('reflective',)*6, zrange=(0.0, 1.0)):
	"""Set the source box around the fuel.
	
	Inputs:
		pitch:		float; pitch between fuel pins
		n:			int; number of fuel pins in an assembly (usually 1 or 17)
		bounds:		tuple/list of strings with len=6, containing the respective
					boundary types for min/max x, y, and z (default: all reflective)
		zrange: 	list of floats with len=2 describing the minimum and maximum z values
					of the geometry
	Outputs:
		a tuple of the openmc X/Y/ZPlanes for the min/max x, y, and z boundaries
	"""
	
	min_x = openmc.XPlane(x0=-pitch/2.0, boundary_type=bounds[0], name="Bound - min x")
	max_x = openmc.XPlane(x0=+pitch/2.0, boundary_type=bounds[1], name="Bound - max x")
	min_y = openmc.YPlane(y0=-pitch/2.0, boundary_type=bounds[2], name="Bound - min y")
	max_y = openmc.YPlane(y0=+pitch/2.0, boundary_type=bounds[3], name="Bound - max y")
	min_z = openmc.ZPlane(z0=zrange[0], boundary_type=bounds[4], name="Bound - min z")
	max_z = openmc.ZPlane(z0=zrange[1], boundary_type=bounds[5], name="Bound - max z")
	
	return min_x, max_x, min_y, max_y, min_z, max_z


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


# plot_file.export_to_xml()

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
	settings_file = openmc.Settings()
	settings_file.batches = min_batches
	settings_file.inactive = inactive
	settings_file.particles = particles
	settings_file.output = {'tallies': False}
	settings_file.trigger_active = True
	settings_file.trigger_max_batches = max_batches
	# Create an initial uniform spatial source distribution over fissionable zones
	lleft = (-npins*pitch/2.0,)*2 + (zrange[0],)
	uright = (+npins*pitch/2.0,)*2 + (zrange[1],)
	uniform_dist = openmc.stats.Box(lleft, uright, only_fissionable=True)  # @UndefinedVariable
	settings_file.source = openmc.source.Source(space=uniform_dist)
	settings_file.export_to_xml()


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


def get_args():
	"""Handle the command line arguments
	
	"""
	args = sys.argv
	
	# Remember, args[0] is this script itself!
	if len(args) >= 2:
		case_file = args[1]
	else:
		case_file = input("Enter the location of the VERA xml input: ")
	
	# Probably move these elsewhere?
	prob, case = get_case(case_file)
	particles, inactive, min_batches, max_batches = get_monte_carlo(case.mc, args)
	folder = get_export_location(case_file, args)
	
	return prob, case, particles, inactive, min_batches, max_batches, folder
	
	
if __name__ == "__main__":
	# test
	print(get_args())
