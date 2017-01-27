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



