# PWR Assembly
# 
# Module for the OpenMC Python API. Once developed, it should
# contain everything needed to generate an openmc.Universe containing
# a model of a Westinghouse-style PWR assembly

import openmc
from functions import fill_lattice
from copy import copy
from math import sqrt

# Global constants for counters
SURFACE, CELL, MATERIAL, UNIVERSE = range(-1,-5,-1)
# Global variables for counters
openmc_surface_count	= openmc.AUTO_SURFACE_ID + 1
openmc_cell_count 		= openmc.AUTO_CELL_ID + 1
openmc_material_count	= openmc.AUTO_MATERIAL_ID + 1
openmc_universe_count	= openmc.AUTO_UNIVERSE_ID + 1


class Mixture(openmc.Material):
	'''Mixture of multiple OpenMC materials.
	Designed to be functionally identical to a regular openmc.Material,
	but defined differently.
	
	WARNING: Currently only works for weight fractions and densities in
	grams per cubic centimeter (g/cc and g/cm^3).
	
	
	Parameters
    ----------
	
	materials:		list of instances of openmc.Material to mix
    vfracs:			list of floats describing the volume fraction of each
    				Material listed above.  
    
    material_id:	int, optional
        Unique identifier for the material. If not specified, an identifier will
        automatically be assigned.
    name:			str, optional
        Name of the material. If not specified, the name will be the empty
        string.
       
    
    Attributes
    ----------
    id : int
        Unique identifier for the material
    density : float
        Density of the material (units defined separately)
    density_units : str
        Units used for `density`. Can be one of 'g/cm3', 'g/cc', 'kg/cm3',
        'atom/b-cm', 'atom/cm3', 'sum', or 'macro'.  The 'macro' unit only
        applies in the case of a multi-group calculation.
    elements : list of tuple
        List in which each item is a 3-tuple consisting of an
        :class:`openmc.Element` instance, the percent density, and the percent
        type ('ao' or 'wo').
    nuclides : list of tuple
        List in which each item is a 3-tuple consisting of an
        :class:`openmc.Nuclide` instance, the percent density, and the percent
        type ('ao' or 'wo').
	
	'''
	
	def __init__(self, materials, vfracs, material_id = None, frac_type = 'wo', name = ""):
		super(Mixture, self).__init__(material_id, name)
		
		mix_isos = []
		density = 0.0
	
		for i in range(len(materials)):
			density += materials[i].density * (vfracs[i] / sum(vfracs))
		for i in range(len(materials)):
			mat = materials[i]
			#mat.convert_ao_to_wo() --> Exists in VERA-to-OpenMC, but not here
			wtf = vfracs[i]*mat.density 	# weight fraction of entire material
			for iso in mat.get_all_nuclides().values():
				nuclide = iso[0]
				new_wt = wtf*iso[1] / density
				if iso in mix_isos:
					old_wt = mix_isos[iso][1]
					mix_isos.append((nuclide, new_wt + old_wt, frac_type))
				else:
					mix_isos.append((nuclide, new_wt, frac_type))
					
		self._nuclides = mix_isos
		self.set_density("g/cc", density)



class Nozzle(object):
	'''Nozzle defined as a smeared material of a certain height and mass
	
	Parameters:
		height:		float; z-coordinate of the top of this nozzle.
					The coordinate of the bottom is determined automatically.
		mass:		float; mass in grams of nozzle material
		nozzle_mat:	instance of openmc.Material; composition of the nozzle itself
		mod_mat:	instance of openmc.Material; composition of the moderator
		npins:		integer; number of pins in a row. Used to calculate Nozzle area
		pitch:		float; pitch in cm between pins.  Used to calculate Nozzle area
		[name:		string; optional name for the nozzle. Default is "nozzle-material".]
	
	Attributes:
		height:		[same as above]
		mass:		[same as above]
		material:	instance of openmc.Material; smearing of nozzle_mat and mod_mat
	'''
	
	def __init__(self, height, mass, nozzle_mat, mod_mat, npins, pitch, name = "nozzle-material"):
		self.height = height
		self.mass = mass
		self.name = name
		volume = (npins*pitch)**2 * height
		self.material = self.__mix(nozzle_mat, mod_mat, volume)
		
	def __mix(self, mat, mod, v):
		'''Mix materials in the way necessary to create the nozzle.
		
		WARNING: Currently only supports the same type of fraction (weight or atomic)
		
		Inputs:
			mat:	instance of openmc.Material describing the nozzle composition
			mod:	instance of openmc.Material describing the moderator
			v:		float; total volume in cm^3 of the nozzle region
		
		Output:
			mix:	instance of openmc.Material describing the smearing of 'mat' and 'mod'
		'''
		mat_vol = self.mass / mat.density
		mod_vol = v - mat_vol
		vfracs = [mat_vol / v, mat_vol / v]
		
		material = Mixture((mat, mod), vfracs, name = self.name)
		return material
		
	def __str__(self):
		return self.name





def counter(count):
		'''Get the next cell/surface/material/universe number, and update the counter.
		Input:
			count:		CELL, SURFACE, MATERIAL, or UNIVERSE
		Output:
			integer representing the next cell/surface/material/universe ID'''
		if count == SURFACE:
			global openmc_surface_count
			openmc_surface_count += 1
			return openmc_surface_count
		elif count == CELL:
			global openmc_cell_count
			openmc_cell_count += 1
			return openmc_cell_count
		elif count == MATERIAL:
			global openmc_cell_count
			openmc_material_count += 1
			return openmc_material_count
		elif count == UNIVERSE:
			global openmc_cell_count
			openmc_universe_count += 1
			return openmc_universe_count
		else:
			raise IndexError("Index " + str(count) + " is not SURFACE, CELL, MATERIAL, or UNIVERSE.")

"""
def duplicate(orig):
	'''Copy an OpenMC object, except for a new id 
	
	Input:
		orig: instance of openmc.(Surface, Cell, Material, or Universe)
	
	Output:
		dupl: same, but with a different instance.id 
	'''
	dup = copy(orig)
	if isinstance(orig, openmc.Surface):
		dup.id = openmc.AUTO_SURFACE_ID
		openmc.AUTO_SURFACE_ID += 1
	elif isinstance(orig, openmc.Cell):
		dup.id = openmc.AUTO_CELL_ID
		openmc.AUTO_CELL_ID += 1
	elif isinstance(orig, openmc.Material):
		dup.id = openmc.AUTO_MATERIAL_ID
		openmc.AUTO_MATERIAL_ID += 1
	elif isinstance(orig, openmc.Universe):
		dup.id = openmc.AUTO_UNIVERSE_ID
		openmc.AUTO_UNIVERSE_ID += 1
	else:
		name = orig.__class__.__name__
		raise TypeError(str(orig) + " is an instance of " + name + 
					"; expected Surface, Cell, Material, or Universe")
	return dup
"""
def duplicate(orig):
	'''Copy an OpenMC object, except for a new id 
	
	Input:
		orig: instance of openmc.(Surface, Cell, Material, or Universe)
	
	Output:
		dupl: same, but with a different instance.id 
	'''
	dup = copy(orig)
	if isinstance(orig, openmc.Surface):
		dup.id = counter(SURFACE)
	elif isinstance(orig, openmc.Cell):
		dup.id = counter(CELL)
	elif isinstance(orig, openmc.Material):
		dup.id = counter(MATERIAL)
	elif isinstance(orig, openmc.Universe):
		dup.id = counter(UNIVERSE)
	else:
		name = orig.__class__.__name__
		raise TypeError(str(orig) + " is an instance of " + name + 
					"; expected Surface, Cell, Material, or Universe")
	return dup


class SpacerGrid(object):
	'''Object to hold properties of an assembly's spacer grids
	
	Parameters:
		key: 		string; unique name of this spacer grid
		height:		float; height (cm) of the spacer around the pins
		mass:		float; mass in g of the entire spacer grid's material
		material:	instance of class openmc.Material
		pitch:		float; pin pitch (cm) 
		npins:		number of pins across an assembly
	Attributes:
		(key, height, mass, material - as above)
		thickness:	float; thickness (cm) of the grid around each pin, 
					or half the total thickness between pins
		'''
	
	def __init__(self, key, height, mass, material, pitch, npins):
		self.key = key	
		self.height = height	
		self.mass = mass		
		self.material = material
		self.thickness = self.calculate_thickness(pitch, npins)
	
	def calculate_thickness(self, pitch, npins):
		'''Calculate the thickness of the spacer surrounding each pincell.
		Inputs:
			pitch:		float; pin pitch (cm)
			npins:		int; number of pins across Assembly (npinsxnpins)
		'''
		
		''' Method:
		
		Volume = mass / density;		Combined Area = Volume / height
			Therefore, [ A = m/rho/h ],		and the area around a single pincell:
												a = m/rho/h / npins^2
			
			The area of the spacer material around one cell can also be found:
				a = p^2 - (p - 2*t)^2,		where 't' is the thickness and 'p' is the pitch
			->  a = p^2 - [p^2 - 4*t*p + 4*t^2]
			->  a = 4*t*p - 4*t^2
				
			Equate the two expressions for a:
				m/rho/h / npins^2 = 4*t*p - 4*t^2
			Then solve for 't' using the quadratic equation:
			
			              [             (          m/rho/h   ) ]
				t = 0.5 * [ p  +/- sqrt ( p^2 -   ---------- ) ]
				          [             (          npins^2   ) ]
        '''
		
		A = self.mass / self.materials[self.material].density / self.height
		t = 0.5*(pitch - sqrt(pitch**2 - A/npins**2))
		return t
		
	def __str__(self):
		name = self.key + ': ' + str(self.thickness) + " cm"
		return name


def add_grid_to(pincell, pitch, t, material):
	'''Given a pincell to be placed in a lattice, add
	the spacer grid to the individual cell.
	
	Inputs:
		pincell:	instance of openmc.Universe describing the pincell
					and its concentric rings of instances of openmc.Cell
		pitch:		float; pin pitch in cm
		t:			float; thickness in cm of one edge of the spacer between
					two pincells (HALF the total thickness)
		material:	instance of openmc.Material from which the spacer is made
	
	Output:
		new_cell:	instance of openmc.Universe describing the pincell
					surrounded by the spacer
	'''
	assert isinstance(pincell, openmc.Universe), str(pincell) + "must be an openmc.Universe (not a Cell)"
	assert isinstance(material, openmc.Material), str(material) + "is not an instance of openmc.Material" 
	
	orig_list = list(pincell.cells.values())
	
	# Create necessary planes
	p = pitch / 2.0
	top_out = openmc.YPlane(y0 =  p)
	top_in  = openmc.YPlane(y0 =  p - t)
	bot_in  = openmc.YPlane(y0 = -p + t)
	bot_out = openmc.YPlane(y0 = -p)
	left_out  = openmc.XPlane(x0 = -p)		# He feels left out
	left_in   = openmc.XPlane(x0 = -p + t)
	right_in  = openmc.XPlane(x0 =  p - t)
	right_out = openmc.XPlane(x0 =  p)
	
	# Get the outermost (mod) Cell of the pincell
	mod_cell = duplicate(orig_list[-1])
	
	# Make a cell encompassing the 4 sides of the spacer
	spacer = openmc.Cell(name = pincell.name + " spacer")
	spacer.region = (+left_out	& +top_in 	& -top_out	&	-right_out) | \
					(+right_in	& -right_out& +bot_in	& 	-top_in)	| \
					(+left_out	& -left_in	& +bot_in	&	-top_in)	| \
					(+bot_out 	& -bot_in	& +left_out	&	-right_out )  
					#& mod_cell.region	# top; bottom; right; left; #outside cylinder	 
	spacer.fill = material
	
	# Then fix the moderator cell to be within the bounds of the spacer
	mod_cell.region = mod_cell.region & \
					(+bot_in	& +left_in	& -top_in	& -right_in )
	
	new_cell = openmc.Universe(name = pincell.name + " gridded")
	# Add all of the original cells except the old mod cell
	for i in range(len(orig_list) - 1):
		new_cell.add_cell(orig_list[i])
	new_cell.add_cell(mod_cell) 	# the new mod cell
	new_cell.add_cell(spacer)
	
	return new_cell


class Assembly(object):
	'''An OpenMC Universe containing cells for the upper/lower nozzles,
	lattices (with and without spacer grids), and surrounding moderator.
	
	Parameters (all optional except "key"):
		key:			str; short, unique name of this Assembly as will appear in the core lattice.
		name:			str; more descriptive name of this Assembly, if desired
						[Default: same as key]
		universe_id:	int; unique integer identifier for its OpenMC universe
						[Default: None, and will be assigned automatically at instantiation of openmc.Universe]
		pitch:			float; pitch (cm) between pincells in the lattices
						[Default: 0.0]
		npins:			int; number of pins across the assembly
						[Default: 0]
		lattices:		list of instances of openmc.RectLattice, in the axial order they appear in the assembly
						(bottom -> top).
						[Default: empty list]
		lattice_elevs:	list of floats describing the elevations (cm) of each boundary in 'lattices',
						relative to the bottom core plate. The next lattice starts where the last leaves off.
						**Must contain exactly len(lattices)+1 entries**
						[Default: empty list] 
		spacers:		list of instances of SpacerGrid, in the axial order they appear in the assembly
						(bottom -> top). 
						[Default: empty list]
		spacer_mids:	list of floats describing the elevations (cm) of the midpoint of each spacer grid
						in 'spacers', relative to the bottom core plate. Gaps are expected.
						***Must contain exactly len(spacers) entries**
						[Default: empty list]
		lower_nozzle:	instance of Nozzle, starting at z=0 and terminating at min(lattice_elevs)
						[Default: None]
		upper_nozzle:	instance of Nozzle, starting at max(lattice_elevs) and terminating at z += Nozzle.height
						[Default: None]
		mod:			instance of openmc.Material describing  moderator surrounding the assembly.
						[Default: None] 
	
	Attributes:
		All the above, plus the following created at self.build():
		spacer_elevs:	list of the elevations of the tops/bottoms of all spacer grids
		all_elevs:		list of all axial elevations, created when (lattice_elevs + spacer_elevs)
						have been concatenated, sorted, and checked for duplicates
		openmc_surfs:	list of instances of openmc.Surface used in the construction of this assembly
		walls:			instance of openmc.Intersection; the 2D region within the assembly.
		openmc_cells:	list of all instances of openmc.Cell used in the construction of this assembly
	'''

	def __init__(self, 	key = "", 		name = "", 			universe_id = None,
						pitch = 0.0, 	npins = 0,
						lattices = [], 	lattice_elevs = [],	spacers = [], 	spacer_mids = [],
						lower_nozzle = None, 				upper_nozzle = None, 
						mod = None):
		
		return None
	
	
	def __prebuild(self):
		'''Check that all the required properties are there.
		If not, error out. Otherwise, do a few operations prior to build().'''
		
		if not self.name:
			self.name = self.key
		
		blank_allowable = ['universe_id', 'spacers', 'spacer_mids', 'upper_nozzle']
		if min(self.lattice_elevs) == 0:
			blank_allowable.append('lower_nozzle')
		
		
		# Check that all necessary parameters are present.
		err_str = "Error: the following parameters need to be set:\n"
		errs = 0
		for attr in self.dict:
			if not self.dict[attr]:
				if attr not in blank_allowable:
					errs += 1
					err_str += '\t- ' + attr + '\n'
		if errs:
			raise TypeError(err_str)
		
		# Check that the number of entries in the lists is correct
		assert (len(self.lattice_elevs) == len(self.lattices) +1), \
			"Error: number of entries in lattice_elevs must be len(lattices) + 1"
		assert (len(self.spacers) == len(self.spacer_elevs)), \
			"Error: number of entries in spacer_elevs must be len(spacers)"
		
		# Combine spacer_elevs and lattice_elevs into one list to rule them all
		if self.spacer_mids:
			spacer_elevs = []
			for i in range(len(self.spacers)):
				spacer = self.spacers[i]
				mid = self.spacer_mids[i]
				s_bot = mid - spacer.height / 2.0
				s_top = mid + spacer.height / 2.0
				spacer_elevs.append((s_bot, s_top))
			elevs = spacer_elevs + self.lattice_elevs
			elevs.sort()
			self.all_elevs = list(set(elevs))	# Remove the duplicates
		else:
			self.all_elevs = self.lattice_elevs
		
		# Finally, create the xy bounding planes
		half = self.pitch*self.npins
		min_x = self.__get_plane('x', -half, name = self.name + ' - min_x') 
		max_x = self.__get_plane('x', +half, name = self.name + ' - max_x') 
		min_y = self.__get_plane('y', -half, name = self.name + ' - min_y') 
		max_y = self.__get_plane('y', +half, name = self.name + ' - max_y') 
		
		self.openmc_surfaces = [min_x, max_x, min_y, max_y]
		self.walls = openmc.Region(+min_x & +min_y & -max_x & -max_y)
		self.openmc_cells = []
	
	
	def __get_plane(self, dim, val, boundary_type = "transmission", name = "", eps = 5):
		'''Return an instance of openmc.(X/Y/Z)Plane. Check if it exists, within
		a precision of 'eps'. If so, return it. Otherwise, create it.
		
		Inputs:
			dim:			str; 'x', 'y', or 'z'
			val:			float; value for x0, y0, or z0
			boundary_type:	"transmission", "vacuum", or "reflective".
							[Default: "transmission"]
			name:			str; creative name of surface
							[Default: empty string]
			eps:			int; number of decimal places after which two planes
							are considered to be the same.
							[Default: 5]
		'''
		
		dim = dim.lower()
		valid = ("x", "xplane", "y", "yplane", "z", "zplane")
		assert (dim in valid), "You must specify one of " + str(valid)
		
		if dim in ("x", "xplane"):
			for xplane in self.openmc_surfaces:
				if val == round(xplane.x0, eps):
					return xplane
			xplane =  openmc.XPlane(counter(SURFACE),
						boundary_type = boundary_type, x0 = val, name = name)
			self.openmc_surfaces.append(xplane)
			return xplane
		elif dim in ("y", "yplane"):
			for yplane in self.openmc_surfaces:
				if val == round(yplane.y0, eps):
					return yplane
			yplane =  openmc.YPlane(counter(SURFACE),
						boundary_type = boundary_type, y0 = val, name = name)
			self.openmc_surfaces.append(yplane)
			return yplane
		elif dim in ("z", "zplane"):
			for zplane in self.openmc_surfaces:
				if val == round(zplane.z0, eps):
					return zplane
			zplane =  openmc.ZPlane(counter(SURFACE),
						boundary_type = boundary_type, z0 = val, name = name)
			self.openmc_surfaces.append(zplane)
			return zplane
		
	
	
	def test_prebuild(self):
		'''Temporary method--to be removed once this class is complete'''
		self.__prebuild()
	
	
	def build(self):
		'''Construct the assembly from the ground up.
		
		Output:
			instance of openmc.Universe'''
		
		self.__prebuild()
		
		# Start at the bottom
		surf0 = openmc.ZPlane(counter(SURFACE), z0 = 0)
		last_s = surf0
		self.openmc_surfaces.append(surf0)
		
		if self.lower_nozzle:
			lnoz = openmc.Cell(counter(CELL), "lower nozzle")
			nozzle_top = self.__get_plane('z', self.lower_nozzle.height)
			lnoz.region = (self.walls & +last_s & -nozzle_top)
			lnoz.fill = self.lower_nozzle.material
			last_s = nozzle_top
		
		for z in self.all_elevs:
			s = self.__get_plane('z', z)
			
		
		
		return None
		




# Test
if __name__ == '__main__':
	
	
	
	# Define a global test moderator
	mod = openmc.Material(1, "mod")
	mod.set_density("g/cc", 1.0)
	mod.add_nuclide("h-1", 2.0/3, 'ao')
	mod.add_nuclide("o-16", 1.0/3, 'ao')
	
	# Define a simple test material
	iron = openmc.Material(2, "iron")
	iron.set_density("g/cc", 7.8)
	iron.add_element("Fe", 1, 'ao', expand=True)
	
	mix1 = Mixture([mod, iron], [0.5,0.5], 33, 'watery iron')
	assert isinstance(mix1, openmc.Material)	
	noz1 = Nozzle(10, 6250, iron, mod, 1, 10)

	# Test a pincell
	cyl0 = openmc.ZCylinder(10, R = 0.300) 
	cyl1 = openmc.ZCylinder(11, R = 0.333)
	cyl2 = openmc.ZCylinder(12, R = 0.350)
	ring0 = openmc.Cell(100, fill = iron, region = -cyl0)
	ring1 = openmc.Cell(101, fill = mod, region = (-cyl1 & +cyl0) )
	ring2 = openmc.Cell(102, fill = mix1, region = (-cyl2 & +cyl1) )
	outer = openmc.Cell(199, fill = mod, region = +cyl2)
	uni = openmc.Universe(cells = (ring0, ring1, ring2, outer), name = "test pincell")
	print(uni)
	gridded = add_grid_to(uni, 1.0, 0.10, iron)
	print(gridded)
	#print(duplicate(uni))

