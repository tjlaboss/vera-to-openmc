# Convert Common
#
# Functions common to all or most of the 'convert_[type].py' modules

import sys
from xml.etree.ElementTree import ParseError
import openmc
import vera_to_openmc


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


def get_args():
	"""Handle the command line arguments
	
	Outputs:
		case_number:    int in {1, 2, 3, 4, 5}; describes which kind of problem it is
		                (2D pincell, 2D lattice, 3D assembly, 3D mini-core, 3D full-core)
		case:           instance of vera_to_openmc.MC_Case
	"""
	args = sys.argv
	errstr1 = "convert_pincell accepts at most 3 arguments at this time (case_file, aname, pname).\n"
	assert len(args) <= 4, errstr1
	case_file = ""
	pname = ""
	aname = ""
	
	# Remember, args[0] is this script itself!
	if len(args) >= 2:
		case_file = args[1]
	if not case_file:
		case_file = input("Enter the location of the VERA xml input: ")
	
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
	
if __name__ == "__main__":
	# test
	print(get_args())
