# Functions
#
# Container for useful functions for the pwr module

from pwr.settings import SURFACE, CELL, MATERIAL, UNIVERSE
import openmc
import copy


def duplicate(orig, counter):
	'''Copy an OpenMC object, except for a new id

	Input:
		orig: 		instance of openmc.(Surface, Cell, Material, or Universe)
		counter:	instance of Counter

	Output:
		dupl: 		same as 'orig', but with a different instance.id
	'''
	dup = copy.copy(orig)
	if isinstance(orig, openmc.Surface):
		dup.id = counter.count(SURFACE)
	elif isinstance(orig, openmc.Cell):
		dup.id = counter.count(CELL)
	elif isinstance(orig, openmc.Material):
		dup.id = counter.count(MATERIAL)
	elif isinstance(orig, openmc.Universe):
		dup.id = counter.count(UNIVERSE)
	else:
		name = orig.__class__.__name__
		raise TypeError(str(orig) + " is an instance of " + name +
		                "; expected Surface, Cell, Material, or Universe")
	return dup


def get_plane(surface_list, counter, dim, val, boundary_type = "transmission", name = "", eps = 5):
	'''Return an instance of openmc.(X/Y/Z)Plane. Check if it exists, within
	a precision of 'eps'. If so, return it. Otherwise, create it.

	Inputs:
		surface_list:	list of instances of openmc.Surface; the list to check for
						surfaces in. WILL BE MODIFIED.
		counter:		instance of Counter, to keep track of new surface numbers.
		dim:			str; 'x', 'y', or 'z'
		val:			float; value for x0, y0, or z0
		boundary_type:	"transmission", "vacuum", or "reflective".
						[Default: "transmission"]
		name:			str; creative name of surface
						[Default: empty string]
		eps:			int; number of decimal places after which two planes
						are considered to be the same.
						[Default: 5]	'''
	dim = dim.lower()
	valid = ("x", "xplane", "y", "yplane", "z", "zplane")
	assert (dim in valid), "You must specify one of " + str(valid)
	
	if dim in ("x", "xplane"):
		for xplane in surface_list:
			if isinstance(xplane, openmc.XPlane):
				if val == round(xplane.x0, eps):
					return xplane
		xplane = openmc.XPlane(counter.count(SURFACE),
		                       boundary_type = boundary_type, x0 = val, name = name)
		surface_list.append(xplane)
		return xplane
	elif dim in ("y", "yplane"):
		for yplane in surface_list:
			if isinstance(yplane, openmc.YPlane):
				if val == round(yplane.y0, eps):
					return yplane
		yplane = openmc.YPlane(counter.count(SURFACE),
		                       boundary_type = boundary_type, y0 = val, name = name)
		surface_list.append(yplane)
		return yplane
	elif dim in ("z", "zplane"):
		for zplane in surface_list:
			if isinstance(zplane, openmc.ZPlane):
				if val == round(zplane.z0, eps):
					return zplane
		zplane = openmc.ZPlane(counter.count(SURFACE),
		                       boundary_type = boundary_type, z0 = val, name = name)
		surface_list.append(zplane)
		return zplane


def get_xyz_planes(openmc_surfaces, count, x0s = (), y0s = (), z0s = (), rd = 5):
	"""
	Inputs:
		openmc_surfaces:
					list of existing instances of openmc.Surface (or openmc.Plane)
					 to compare against, to avoid duplicates.
		count:      instance of pwr.Counter
		x0s:		list or tuple of x0's to check for; default is empty tuple
		y0s:		same for y0's
		z0s:		same for z0's
		rd:			integer; number of digits to round to when comparing surface
					equality. Default is 5
	Outputs:
		xlist:		list of instances of openmc.XPlane, of length len(x0s)
		ylist:		ditto, for openmc.YPlane, y0s
		zlist:		ditto, for openmc.ZPlane, z0s
	"""
	nx = len(x0s)
	ny = len(y0s)
	nz = len(z0s)
	xlist = [None, ] * nx
	ylist = [None, ] * ny
	zlist = [None, ] * ny
	
	for i in range(nx):
		xlist[i] = get_plane(openmc_surfaces, count, 'x', x0s[i], eps = rd)
	for i in range(ny):
		ylist[i] = get_plane(openmc_surfaces, count, 'y', y0s[i], eps = rd)
	for i in range(nz):
		zlist[i] = get_plane(openmc_surfaces, count, 'z', z0s[i], eps = rd)
	
	return xlist, ylist, zlist


def get_surface(counter, surfdict, dim, coeff, rd = 5):
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
			openmc_surf = openmc.XPlane(counter.add_surface(), x0 = coeff)
		elif dim in ("y", "yp", "yplane"):
			openmc_surf = openmc.YPlane(counter.add_surface(), y0 = coeff)
		elif dim in ("z", "zp", "zplane"):
			openmc_surf = openmc.ZPlane(counter.add_surface(), z0 = coeff)
		elif dim in ("r", "cyl", "cylinder", "zcylinder"):
			openmc_surf = openmc.ZCylinder(counter.add_surface(), R = coeff)
		else:
			errstr = "'dim' must be 'xplane', 'yplane', 'zplane', or 'zcylinder'"
			raise AssertionError(errstr)
		surfdict[key] = openmc_surf
		return openmc_surf


