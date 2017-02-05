# Functions
#
# Container for useful functions for the pwr module

import openmc
import copy


def duplicate(orig, counter):
	"""Copy an OpenMC object, except for a new id

	Input:
		orig: 		instance of openmc.(Surface, Cell, Material, Universe, or Tally)
		counter:	instance of Counter

	Output:
		dupl: 		same as 'orig', but with a different instance.id
	"""
	dup = copy.copy(orig)
	if isinstance(orig, openmc.Surface):
		dup.id = counter.add_surface()
	elif isinstance(orig, openmc.Cell):
		dup.id = counter.add_cell()
	elif isinstance(orig, openmc.Material):
		dup.id = counter.add_material()
	elif isinstance(orig, openmc.Universe):
		dup.id = counter.add_universe()
	elif isinstance(orig, openmc.Tally):
		dup.id = counter.add_tally()
	else:
		name = orig.__class__.__name__
		raise TypeError(str(orig) + " is an instance of " + name +
		                "; expected Surface, Cell, Material, or Universe")
	return dup



def get_surface(counter, surfdict, dim, coeff, name = "", rd = 5):
	"""Given a single-coefficient Surface class (such as ZPlane, or Cylinder centered at 0,0),
	look it up in the provided dictionary 'surfdict' if possible. If not, generate it anew,
	and add it to the dictionary.

	Warning: This assumes you want a surface with the "transmission" boundary condition.
	If you need a different bc, do not use this function.

	Inputs:
		:param counter:         instance of pwr.Counter
		:param surfdict:        dictionary of some type of instance of openmc.Surface, of the format
		                        {str(coeff):openmc.Surface}; e.g., {str(x0):openmc.XPlane)
		:param dim:             str; dimension or surface type. Case insensitive.
								Currently works for ("x"/"xplane", "y"/"yplane", "z"/"zplane", "r"/"cyl"/"zcylinder")
		:param coeff:           float; Value of the coefficent (such as x0 or R) for the surface type
		:param name:            str; name to be assigned if the surface doesn't already exist
		:param rd:              int; number of decimal places to round to. If the coefficient for a surface matches
								up to 'rd' decimal places, they are considered equal.
								[Default: 5]
	Output:
		:return openmc_surf:    instance of openmc.Surface
	"""
	coeff = round(coeff, rd)
	key = str(coeff)
	dim = dim.lower()
	if key in surfdict:
		return surfdict[key]
	else:
		# Generate it
		if dim in ("x", "xp", "xplane"):
			openmc_surf = openmc.XPlane(counter.add_surface(), x0 = coeff, name = name)
		elif dim in ("y", "yp", "yplane"):
			openmc_surf = openmc.YPlane(counter.add_surface(), y0 = coeff, name = name)
		elif dim in ("z", "zp", "zplane"):
			openmc_surf = openmc.ZPlane(counter.add_surface(), z0 = coeff, name = name)
		elif dim in ("r", "cyl", "cylinder", "zcylinder"):
			openmc_surf = openmc.ZCylinder(counter.add_surface(), R = coeff, name = name)
		else:
			errstr = "'dim' must be 'xplane', 'yplane', 'zplane', or 'zcylinder'"
			raise AssertionError(errstr)
		surfdict[key] = openmc_surf
		return openmc_surf


