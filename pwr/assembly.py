# PWR Assembly
# 
# Module for the OpenMC Python API. Once developed, it should
# contain everything needed to generate an openmc.Universe containing
# a model of a Westinghouse-style PWR assembly

import openmc
import pwr.spacergrid
import pwr.functions



class Assembly(object):
	"""Constructor for an OpenMC Universe containing:
		cells for the upper/lower nozzles,
		lattices (with and without spacer grids),
		and the surrounding moderator.
	
	Parameters (all optional except "key"):
		key:				str; short, unique name of this Assembly as will appear in the core lattice.
		name:				str; more descriptive name of this Assembly, if desired
							[Default: same as key]
		universe_id:		int; unique integer identifier for its OpenMC universe
							[Default: None, and will be assigned automatically at instantiation of openmc.Universe]
		pitch:				float; pitch (cm) between pincells in the lattices
							[Default: 0.0]
		npins:				int; number of pins across the assembly
							[Default: 0]
		walls:				list of instances of openmc.Surface: [min_x, max_x, min_y, max_y] 
							Used to create the 2D region within the assembly.
							[Will be generated automatically if not provided.]
		xplanes:            dictionary of instances of openmc.XPlane, of the format {str(x0):xplane)
	                        [Default: empty dictionary]
		yplanes:            dictionary of instances of openmc.YPlane, of the format {str(y0):yplane)
	                        [Default: empty dictionary]
		zplanes:            dictionary of instances of openmc.ZPlane, of the format {str(z0):zplane)
	                        [Default: empty dictionary]
		lattices:			list of instances of openmc.RectLattice, in the axial order they appear in the assembly
							(bottom -> top).
							[Default: empty list]
		lattice_elevs:		list of floats describing the elevations (cm) of each boundary in 'lattices',
							relative to the bottom core plate. The next lattice starts where the last leaves off.
							**Must contain exactly len(lattices)+1 entries**
							[Default: empty list] 
		spacers:			list of instances of SpacerGrid, in the axial order they appear in the assembly
							(bottom -> top). 
							[Default: empty list]
		spacer_mids:		list of floats describing the elevations (cm) of the midpoint of each spacer grid
							in 'spacers', relative to the bottom core plate. Gaps are expected.
							***Must contain exactly len(spacers) entries**
							[Default: empty list]
		lower_nozzle:		instance of Nozzle, starting at z=0 and terminating at min(lattice_elevs)
							[Default: None]
		upper_nozzle:		instance of Nozzle, starting at max(lattice_elevs) and terminating at z += Nozzle.height
							[Default: None]
		z_active:			list with len=2 of the z-range of active fuel. If not specified, the minimum and maximum
							values of lattice_elevs will be automatically selected when you run build(). 
							[Default: empty list]  
		mod:				instance of openmc.Material describing  moderator surrounding the assembly.
							[Default: None] 
		counter:			instance of pwr.Counter used for keeping track of surface/cell/material/universe IDs.
							[Default: None] 
	
	Attributes:
		All the above, plus the following created at self.build():
		bottom:				instance of openmc.ZPlane marking the lowest surface in the Assembly
		top:				instance of openmc.ZPlane marking the highest surface in the Assembly
		spacer_elevs:		list of the elevations of the tops/bottoms of all spacer grids
		all_elevs:			list of all axial elevations, created when (lattice_elevs + spacer_elevs)
							have been concatenated, sorted, and checked for duplicates
		openmc_cells:		list of all instances of openmc.Cell used in the construction of this assembly
		gridded_pincells:	dictionary of pincells which have a gridded version, in the following format:
							{'orig. universe id': gridded instance of openmc.Universe}
		gridded_lattices:	dictionary of lattices  which have a gridded version, in the following format:
							{'orig. universe id': gridded instance of openmc.RectLattice}
		universe:			instance of openmc.Universe; the OpenMC representation of the fuel assembly
	"""

	def __init__(self, 	key = "", 		name = "", 			universe_id = None,
						pitch = 0.0, 	npins = 0,			walls = [],
                        xplanes = {},   yplanes = {},       zplanes = {},
						lattices = [], 	lattice_elevs = [],	spacers = [], 	spacer_mids = [],
						lower_nozzle = None, 				upper_nozzle = None, 
						z_active = [],	mod = None,			counter = None):
		self.key = key
		self.name = name
		self.universe_id = universe_id
		self.pitch = pitch;					self.npins = npins
		self.lattices = lattices;			self.lattice_elevs = lattice_elevs
		self.spacers = spacers;				self.spacer_mids = spacer_mids
		self.lower_nozzle = lower_nozzle;	self.upper_nozzle = upper_nozzle
		self.walls = walls;
		self.xplanes = xplanes;             self.yplanes = yplanes;         self.zplanes = zplanes
		self.z_active = z_active
		self.mod = mod
		self.counter = counter
	
	
	def __str__(self):
		return self.name
	
	
	def __get_surface(self, dim, coeff, name = "", rd = 5):
		"""Wrapper for pwr.get_surface()

			Inputs:
				:param dim:             str; dimension or surface type. Case insensitive.
				:param coeff:           float; Value of the coefficent (such as x0 or R) for the surface type
				:param name:            str; name to be assigned to the new surface (if one is generated)
										[Default: empty string]
				:param rd:              int; number of decimal places to round to. If the coefficient for a surface matches
										up to 'rd' decimal places, they are considered equal.
										[Default: 5]
			Output:
				:return openmc_surf:
		"""
		dim = dim.lower()
		if dim in ("x", "xp", "xplane"):
			surfdict = self.xplanes
		elif dim in ("y", "yp", "yplane"):
			surfdict = self.yplanes
		elif dim in ("z", "zp", "zplane"):
			surfdict = self.zplanes
		else:
			raise AssertionError(str(dim) + " is not an acceptable Surface type.")
		openmc_surf = pwr.functions.get_surface(self.counter, surfdict, dim, coeff, name, rd)
		return openmc_surf
	
	
	def __prebuild(self):
		"""Check that all the required properties are there.
		If not, error out. Otherwise, do a few operations prior to build()."""
		
		if not self.name:
			self.name = self.key
		blank_allowable = ['universe_id', 'spacers', 'spacer_mids', 'upper_nozzle', 'walls', 'z_active',
		                   'xplanes', 'yplanes', 'zplanes']
		if min(self.lattice_elevs) == 0:
			blank_allowable.append('lower_nozzle')
		
		# Check that all necessary parameters are present.
		err_str = "the following attributes need to be set:\n"
		errs = 0
		for attr in self.__dict__:
			if not self.__dict__[attr]:
				if attr not in blank_allowable:
					errs += 1
					err_str += '\t- ' + attr + '\n'
		if errs:
			raise AttributeError(err_str)
		
		# Check that the number of entries in the lists is correct
		assert (len(self.lattice_elevs) == len(self.lattices)+1), \
			"Error: number of entries in lattice_elevs must be len(lattices) + 1"
		assert (len(self.spacers) == len(self.spacer_mids)), \
			"Error: number of entries in spacer_elevs must be len(spacers)"
		
		#TODO: If griddict not in lattice.__dict__  --> add it
		
		self.openmc_cells = []
		
		# Determine the range of the active fuel
		if len(self.z_active) != 2:
			self.z_active = [min(self.lattice_elevs), max(self.lattice_elevs)]
		
		# Combine spacer_elevs and lattice_elevs into one list to rule them all
		if self.spacer_mids:
			self.spacer_elevs = []
			for i in range(len(self.spacers)):
				spacer = self.spacers[i]
				mid = self.spacer_mids[i]
				s_bot = mid - spacer.height / 2.0
				s_top = mid + spacer.height / 2.0
				self.spacer_elevs += (s_bot, s_top)
			elevs = self.spacer_elevs + self.lattice_elevs
			self.all_elevs = list(set(elevs))	# Remove the duplicates
			self.all_elevs.sort()
		else:
			self.all_elevs = self.lattice_elevs
		
		
		# Finally, create the xy bounding planes
		if self.walls:
			[min_x, max_x, min_y, max_y] = self.walls
		else:
			half = self.pitch*self.npins/2.0
			min_x = self.__get_surface('xplane', -half, name = self.name + ' - min_x')
			max_x = self.__get_surface('xplane', +half, name = self.name + ' - max_x')
			min_y = self.__get_surface('yplane', -half, name = self.name + ' - min_y')
			max_y = self.__get_surface('yplane', +half, name = self.name + ' - max_y')
			self.walls = [min_x, max_x, min_y, max_y]
		self.wall_region = openmc.Intersection(+min_x & +min_y & -max_x & -max_y)
	
	
	def build(self):
		"""Construct the assembly from the ground up.
		
		Output:
			instance of openmc.Universe"""
		
		self.__prebuild()
		
		# Start at the bottom
		self.bottom = self.__get_surface("zplane", 0, name = "bottom")
		last_s = self.bottom
		
		if self.lower_nozzle:
			lnoz = openmc.Cell(self.counter.add_cell(), "lower nozzle")
			nozzle_top = self.__get_surface('zplane', self.lower_nozzle.height)
			lnoz.region = (self.wall_region & +last_s & -nozzle_top)
			lnoz.fill = self.lower_nozzle.material
			self.openmc_cells.append(lnoz)
			last_s = nozzle_top
		
		
		for z in self.all_elevs[1:]:
			s = self.__get_surface('zplane', z)
			# See what lattice we are in
			for i in range(len(self.lattices)):
				if self.lattice_elevs[i] >= z > self.lattice_elevs[i-1]:
					break
			lat = self.lattices[i-1]
			# Check if there is a spacer grid
			if self.spacer_mids:
				for g in range(len(self.spacer_elevs)):
					if self.spacer_elevs[g] >= z > self.spacer_elevs[g-1]:
						break
				# Even numbers are bottoms, odds are top
				grid = None
				if g % 2 and z > min(self.spacer_elevs):
					# Then the last one was a bottom: a grid is present
					grid = self.spacers[int(g/2)]
				# OK--now we know what the current lattice is, and whether there's a grid here.
				if grid:
					if grid.key not in lat.griddict:
						# We need to add the spacer grid to this one, and then add it to the index
						lat.griddict[grid.key] = pwr.add_grid_to(lat, grid, self.counter,
						                                         self.xplanes, self.yplanes)
					lat = lat.griddict[grid.key]
				
			# Now, we have the current lattice, for the correct level, with or with a spacer
			# grid as appropriate. Time to make the layer.
			layer = openmc.Cell(self.counter.add_cell(), name = lat.name)
			layer.region = (self.wall_region & +last_s & -s)
			layer.fill = lat
			self.openmc_cells.append(layer)
			
			# And then prepare for the next loop around
			last_s = s
		
		# Now we've done all the lattice layers!
		# Add the top nozzle if necessary:
		if self.upper_nozzle:
			unoz = openmc.Cell(self.counter.add_cell(), "upper nozzle")
			nozzle_top = self.__get_surface('z', last_s.z0 + self.upper_nozzle.height)
			unoz.region = (self.wall_region & +last_s & -nozzle_top)
			unoz.fill = self.upper_nozzle.material
			self.openmc_cells.append(unoz)
			last_s = nozzle_top
		
		self.top = last_s
		
		# Finally, surround the whole assembly with moderator
		mod_cell = openmc.Cell(self.counter.add_cell(), name = self.name + " mod")
		mod_cell.region = (~self.wall_region | +self.top | -self.bottom)
		mod_cell.fill = self.mod
		self.openmc_cells.append(mod_cell)
		
		# And we're done!! Zip it all up in a universe.
		if self.universe_id:
			uid = self.universe_id
		else:
			uid = self.counter.add_universe()
		self.universe = openmc.Universe(uid, name = self.name)
		self.universe.add_cells(self.openmc_cells)
		
		return self.universe




# Test
if __name__ == '__main__':
	from pwr.mixture import Mixture
	import pwr.nozzle
	c = pwr.Counter()
	# Define a global test moderator
	mod = openmc.Material(c.add_material(), "mod")
	mod.set_density("g/cc", 1.0)
	mod.add_nuclide("h1", 2.0/3, 'ao')
	mod.add_nuclide("o16", 1.0/3, 'ao')
	
	# Define a simple test material
	iron = openmc.Material(c.add_material(), "iron")
	iron.set_density("g/cc", 7.8)
	iron.add_element("Fe", 1, 'ao')
	
	mix1 = Mixture([mod, iron], [0.5,0.5], c.add_material(), 'watery iron')
	assert isinstance(mix1, openmc.Material)	
	noz1 = pwr.nozzle.Nozzle(10, 6250, iron, mod, 1, 10, c)

	# Test a pincell
	cyl0 = openmc.ZCylinder(c.add_surface(), R = 0.300) 
	cyl1 = openmc.ZCylinder(c.add_surface(), R = 0.333)
	cyl2 = openmc.ZCylinder(c.add_surface(), R = 0.350)
	ring0 = openmc.Cell(c.add_cell(), fill = iron, region = -cyl0)
	ring1 = openmc.Cell(c.add_cell(), fill = mod, region = (-cyl1 & +cyl0) )
	ring2 = openmc.Cell(c.add_cell(), fill = mix1, region = (-cyl2 & +cyl1) )
	outer = openmc.Cell(c.add_cell(), fill = mod, region = +cyl2)
	uni = openmc.Universe(c.add_universe(), cells = (ring0, ring1, ring2, outer), name = "test pincell")
	print(uni)
	gridded = pwr.spacergrid.add_spacer_to(uni, 1.0, 0.10, iron, c, [])
	print(gridded)

