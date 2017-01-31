# Vera to OpenMC
#
# Takes a VERA case and attempts to construct 
# the required files for an OpenMC input.

from copy import copy
from read_xml import Case
from functions import fill_lattice, clean
import objects
import openmc
import pwr
from pwr import SURFACE, CELL, MATERIAL, UNIVERSE, TALLY	# Global constants for counters


class MC_Case(Case):
	"""An extension of the Case class from read_xml,
	customized with some new attributes and methods to 
	generate objects for OpenMC."""
	def __init__(self, source_file):
		super(MC_Case, self).__init__(source_file)
		
		self.openmc_surfaces = []
		# The following dictionaries use key-value pairs of 'coefficient':openmc.Surface
		self.openmc_xplanes ={}         # {str(x0):openmc.XPlane)
		self.openmc_yplanes ={}         # {str(y0):openmc.YPlane)
		self.openmc_zplanes ={}         # {str(z0):openmc.ZPlane)
		self.openmc_cylinders ={}       # {str(R):openmc.Cylinder)
		
		self.openmc_materials = {}
		self.openmc_pincells = {}
		self.openmc_assemblies = {}
		
		# ID Counter
		# Starting at 99 makes all IDs triple digits
		self.counter = pwr.Counter(99, 99, 99, 99)
		
		
		# Create the essential moderator material
		'''The outside of each cell is automatically filled with the special material "mod", which refers to
		the moderator (or coolant). The composition of "mod" is calculated by the codes using the local T/H
		conditions and the soluble boron concentration, and cannot be specified by a user on a mat card.'''
		self.mod = self.get_openmc_material("mod")
		self.mod.add_s_alpha_beta("c_H_in_H2O")
		
		# Create an infinite cell/universe of moderator
		self.mod_cell = openmc.Cell(100, name = "Infinite Mod Cell", fill = self.mod)
		self.mod_verse = openmc.Universe(100, name = "Infinite Mod Universe", cells = (self.mod_cell,))
	
	def __counter(self, TYPE):
		"""Get the next cell/surface/material/universe number, and update the counter.
		Input:
			count:		CELL, SURFACE, MATERIAL, UNIVERSE, or TALLY
		Output:
			integer representing the next cell/surface/material/universe ID"""
		
		# Quick fix
		return self.counter.count(TYPE)
	
	
	def __get_surface(self, dim, coeff, rd = 5):
		"""Wrapper for pwr.get_surface()
		
		Inputs:
			:param dim:             str; dimension or surface type. Case insensitive.
			:param coeff:           float; Value of the coefficent (such as x0 or R) for the surface type
			:param rd:              int; number of decimal places to round to. If the coefficient for a surface matches
									up to 'rd' decimal places, they are considered equal.
									[Default: 5]
		Output:
			:return openmc_surf:
		"""
		dim = dim.lower()
		if dim in ("x", "xp", "xplane"):
			surfdict = self.openmc_xplanes
		elif dim in ("y", "yp", "yplane"):
			surfdict = self.openmc_xplanes
		elif dim in ("z", "zp", "zplane"):
			surfdict = self.openmc_xplanes
		elif dim in ("r", "cyl", "cylinder", "zcylinder"):
			surfdict = self.openmc_xplanes
		else:
			raise AssertionError(str(dim) + " is not an acceptable Surface type.")
		return pwr.add_surface(self.counter, surfdict, dim, coeff, rd)
		
	
		
	def __get_xyz_planes(self, x0s = (), y0s = (), z0s = (), rd = 5):
		"""
		Inputs:
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
		xlist = [None,]*nx
		ylist = [None,]*ny
		zlist = [None,]*ny
		
		for i in range(nx):
			xlist[i] = pwr.get_plane(self.openmc_surfaces, self.counter, 'x', x0s[i], eps = rd)
		for i in range(ny):
			ylist[i] = pwr.get_plane(self.openmc_surfaces, self.counter, 'y', y0s[i], eps = rd)
		for i in range(nz):
			zlist[i] = pwr.get_plane(self.openmc_surfaces, self.counter, 'z', z0s[i], eps = rd)
		
		return xlist, ylist, zlist
	
	
	
	def get_openmc_baffle(self):
		"""Calls pwr.get_openmc_baffle() with the
		properties of this case and core.
		
		Output:
			baffle_cell:        instance of openmc.Cell describing the baffle geometry.
		"""
		
		baf = self.core.baffle		# instance of objects.Baffle
		cmap = self.core.shape.square_map()
		apitch = self.core.pitch
		baffle_cell = pwr.get_openmc_baffle(baf, cmap, apitch, self.openmc_xplanes,
		                                    self.openmc_yplanes, self.counter)
		return baffle_cell
		
	
		
	def get_openmc_material(self, material, asname = "", inname = ""):
		"""Given a vera material (objects.Material) as extracted by self.__get_material(),
		return an instance of openmc.Material. If the OpenMC Material exists, look it
		up in the dictionary. Otherwise, create it anew.
		
		Inputs:
			material:			string; key of the material in self.materials
			asname:				string; name of the Assembly in which a pin cell is present.
								VERA pin cells may have different materials sharing the same name.
								[Default: empty string]
			inname:				string; name of the Insert which has been placed inside the cell, if any.
								[Default: empty string]
		
		Outputs:
			openmc_material:	instance of openmc.Material
		
		All of the material fractions sum to either +1.0 or -1.0. If positive fractions are used, they
		refer to weight fractions. If negative fractions are used, they refer to atomic	fractions.
		"""
		
		# Handle the permutations/combinations of suffixes.
		# This order should be preserved.
		all_suffixes = [asname + inname, asname, inname]
		for suffix in all_suffixes:
			if material + suffix in self.materials:
				material += suffix
				break
		
		if material in self.openmc_materials:
			# Look it up as normal
			openmc_material = self.openmc_materials[material]
		else:
			# Then the material doesn't exist yet in OpenMC form
			# Generate it and add it to the index 
			vera_mat = self.materials[material]
			openmc_material = openmc.Material(self.__counter(MATERIAL), material)
			openmc_material.set_density("g/cc", vera_mat.density)
			openmc_material.temperature = vera_mat.temperature
			for nuclide in sorted(vera_mat.isotopes):
				frac = vera_mat.isotopes[nuclide]
				if nuclide[-2:] == "00":
					# Natural abundance-expand except for Carbon
					ename = nuclide[:-2]
					if ename == "C":
						# Correct for OpenMC syntax
						openmc_material.add_nuclide("C0", frac, 'wo')
					else:
						# Element.expand() breaks an element into its constituent nuclides
						elem = openmc.Element(ename)
						for nuclist in elem.expand(frac, 'wo'):
							n, w = nuclist[0:2]
							openmc_material.add_nuclide(n, w, 'wo')
				else:
					openmc_material.add_nuclide(nuclide, frac, 'wo')
				# Shouldn't be needed: the parsed XML should already be in weight frac
				#if frac < 0:
				#	openmc_material.add_nuclide(nuclide, abs(frac), 'ao')			
					
			self.openmc_materials[material] = openmc_material
		
		return openmc_material
	
	

	
	def get_openmc_pincell(self, vera_cell):
		"""Converts a VERA cell to an OpenMC universe. If this pincell universe
		already exists, return it; otherwise, construct it anew, and add it
		to self.openmc_pincells.
		
		Inputs:
			vera_cell:			instance of objects.Cell from the vera deck
		
		Outputs:
			pincell_universe:	instance of openmc.Universe, containing:
				.cells:				list of instances of openmc.Cell, describing the
									geometry and composition of this pin cell's universe
				.universe_id:	integer; unique identifier of the Universe
				.name:			string; more descriptive name of the universe (pin cell)			
			"""
		
		# First, check if this cell has already been created
		if vera_cell.key in self.openmc_pincells:
			return self.openmc_pincells[vera_cell.key]
		else:
			openmc_cells = []
			# Before proceeding, define the OpenMC surfaces (Z cylinders)
			for ring in range(vera_cell.num_rings):
				r = vera_cell.radii[ring]
				name = vera_cell.name + "-ring" + str(ring)
				# Check if the outer bounding surface exists
				surf_id = None
				for s in self.openmc_surfaces:
					if s.type == "z-cylinder":
						if (s.r == r) and (s.x0 == 0) and (s.y0 == 0):
							# Then the cylinder is the same
							surf_id = s.id
							break # from the "for s in" loop
				if not surf_id:
					# Generate new surface and get its surf_id
					s = openmc.ZCylinder(self.counter.add_surface(), "transmission", 0, 0, r)
					# Add the new surfaces to the registry
					self.openmc_surfaces.append(s)
					
				# Otherwise, the surface s already exists
				# Proceed to define the cell inside that surface:
				new_cell = openmc.Cell(self.counter.add_cell(), name)
				
				if ring == 0:
					# Inner ring
					new_cell.region = -s
					last_s = s
				else:
					# Then this OpenMC cell is outside the previous (last_s), inside the current
					new_cell.region = -s & +last_s
					last_s = s
				
				# Fill the cell in with a material
				m = vera_cell.mats[ring]
				fill = self.get_openmc_material(m, vera_cell.asname, vera_cell.inname)
					
				# What I want to do instead is, somewhere else in the code, generate the corresponding
				# openmc material for each objects.Material instance. Then, just look it up in that dictionary.
				new_cell.fill = fill
				openmc_cells.append(new_cell)
			# end of "for ring" loop
			
			# Then add the moderator outside the pincell
			mod_cell = openmc.Cell(self.counter.add_cell(), vera_cell.name + "-Mod")
			mod_cell.fill = self.mod
			mod_cell.region = +last_s
			openmc_cells.append(mod_cell)
			
			# Create a new universe in which the pin cell exists 
			pincell_universe = openmc.Universe(self.counter.add_universe(), vera_cell.name + "-verse")
			pincell_universe.add_cells(openmc_cells)
			
			# Initialize a useful dictionary to keep track of versions of
			# this cell which have spacer grids added
			pincell_universe.griddict = {}
			
			self.openmc_pincells[vera_cell.key] = pincell_universe
			
			return pincell_universe
	
	
	
	def get_openmc_lattices(self, vera_asmbly):
		"""Creates the  assembly geometry and lattices of pin cells
		required to define an assembly in OpenMC.
		
		Inputs:
			vera_asmbly:		instance of objects.Assembly
		
		Outputs:
			openmc_asmblies:	list of instance of openmc.RectLattice
		"""
		pitch = vera_asmbly.pitch
		npins = vera_asmbly.npins
		# Look for optional parameters available from vera_asmbly.params
		# Possible params include:
		# axial_elevations, axial_labels, grid_elev, grid_map,
		# ppitch, title, num_pins, label
		openmc_lattices = []
		
		# Instantiate all the pin cells (openmc.Universes) that appear in the Assembly
		cell_verses = {}
		for vera_cell in vera_asmbly.cells.values():
			c = self.get_openmc_pincell(vera_cell)
			cell_verses[vera_cell.key] = c
		
		for latname in vera_asmbly.axial_labels:
			lattice = openmc.RectLattice(self.__counter(UNIVERSE), latname)
			lattice.pitch = (pitch, pitch)
			lattice.lower_left = [-pitch * float(npins) / 2.0] * 2
			# And populate with universes from cell_verses
			asmap = vera_asmbly.key_maps[latname]
			
			lattice.universes = fill_lattice(asmap, lambda c: cell_verses[c], npins)
			lattice.outer = self.mod_verse	# To account for the assembly gap
			# Initialize a dictionary of versions of this lattice which have spacer grids added
			lattice.griddict = {}
			openmc_lattices.append(lattice)
		
		return openmc_lattices
	
	
	
	
	def get_openmc_assembly(self, vera_asmbly):
		"""Creates an OpenMC fuel assembly, complete with lattices
		of fuel pins and spacer grids, that should be equivalent to what
		is constructed by VERA.
		
		Inputs:
			vera_asmbly:		instance of objects.Assembly
		
		Outputs:
			pwr_asmbly:			instance of pwr.Assembly containing the lattices, spacers, and such. 
								pwr_asmbly.universe is the instance of openmc.Universe modeling
								the fuel assembly.
		"""
		key = vera_asmbly.name
		if key in self.openmc_assemblies:
			return self.openmc_assemblies[key]
		else:
			
			ps = vera_asmbly.params
			pitch = vera_asmbly.pitch
			npins = vera_asmbly.npins
			
			# Initiate and describe the Assembly
			pwr_asmbly = pwr.Assembly(vera_asmbly.label, vera_asmbly.name, self.counter.add_universe(), pitch, npins)
			pwr_asmbly.lattices = self.get_openmc_lattices(vera_asmbly)
			pwr_asmbly.lattice_elevs = vera_asmbly.axial_elevations
			pwr_asmbly.mod = self.mod
			pwr_asmbly.counter = self.counter
			
			if vera_asmbly.spacergrids:
				if not vera_asmbly.pwr_spacers:
					# Translate from VERA to pwr 
					for gkey in vera_asmbly.spacergrids:
						g = vera_asmbly.spacergrids[gkey]
						mat = self.get_openmc_material(g.material)
						grid = pwr.SpacerGrid(gkey, g.height, g.mass, mat, pitch, npins)
						vera_asmbly.pwr_spacers[gkey] = grid
				# Otherwise, we should already have a dictionary of them.
				
				pwr_asmbly.spacers = clean(ps["grid_map"], lambda key: vera_asmbly.pwr_spacers[key] )
				pwr_asmbly.spacer_mids = clean(ps["grid_elev"], float)
			
			# Handle nozzles
			
			if "lower_nozzle_comp" in ps:
				if "lower" not in vera_asmbly.pwr_nozzles:
					nozzle_mat = self.get_openmc_material(ps["lower_nozzle_comp"])
					mass = float(ps["lower_nozzle_mass"])
					height = float(ps["lower_nozzle_height"])
					lnozmat = self.get_nozzle_mixture(height, mass, nozzle_mat, self.mod, npins, pitch, "lower-nozzle-mat")
					#lnoz = pwr.Nozzle(height, mass, nozzle_mat, self.mod, npins, pitch,
					#					counter = self.counter, name = "Lower Nozzle")
					#self.openmc_materials[lnozmat.name] = lnozmat
					lnoz = objects.Nozzle(height, lnozmat, "Lower Nozzle")
					vera_asmbly.pwr_nozzles["lower"] = lnoz
				else:
					lnoz = vera_asmbly.pwr_nozzles["lower"]
				pwr_asmbly.lower_nozzle = lnoz
			if "upper_nozzle_comp" in ps:
				if "upper" not in vera_asmbly.pwr_nozzles:
					nozzle_mat = self.get_openmc_material(ps["upper_nozzle_comp"])
					mass = float(ps["upper_nozzle_mass"])
					height = float(ps["upper_nozzle_height"])
					unozmat = self.get_nozzle_mixture(height, mass, nozzle_mat, self.mod, npins, pitch, "upper-nozzle-mat")
					#unoz = pwr.Nozzle(height, mass, nozzle_mat, self.mod, npins, pitch,
					#					counter = self.counter, name = "Upper Nozzle")
					#self.openmc_materials[unozmat.name] = unozmat
					unoz = objects.Nozzle(height, unozmat, "Upper Nozzle")
					vera_asmbly.pwr_nozzles["upper"] = unoz
				else:
					unoz = vera_asmbly.pwr_nozzles["upper"]
				pwr_asmbly.upper_nozzle = unoz
			
			'''	Worth noting about the nozzles:
		
				== Analysis of the BEAVRS Benchmark Using MPACT ==
			A major difference between the model and the benchmark specification is the treatment of 
			the axial reflector region. The benchmark specifies the upper and lower nozzle to be modeled 
			with a considerable amount of stainless steel. The authors discerned that 
			the benchmark is specifying up to 10 times the amount of steel that is in the nozzle and
			core plate region. Instead of using this amount of steel, a Westinghouse optimized fuel
			assembly (OFA) design found in Technical Report ML033530020 is used for the upper and
			lower reflector regions.
											--CASL-U-2015-0183-000	'''
			
			
			# Where the magic happens
			pwr_asmbly.build()
			self.openmc_assemblies[key] = pwr_asmbly
			
				
			return pwr_asmbly
	
	
	def get_nozzle_mixture(self, height, mass, nozzle_mat, mod_mat, npins, pitch, name = "nozzle-material"):
		"""Get the mixture for a nozzle. 
		
		Inputs:
		
		Output:
			new_mixture:		instance of pwr.Mixture
		"""
		if name in self.openmc_materials:
			return self.openmc_materials[name]
		else:
			v = (npins*pitch)**2 * height
			mat_vol = mass / nozzle_mat.density
			mod_vol = v - mat_vol
			vfracs = [mat_vol / v, mod_vol / v]
			new_mixture = pwr.Mixture((nozzle_mat, mod_mat), vfracs,
			                name = name, material_id = self.counter.add_material())
			self.openmc_materials[name] = new_mixture
			return new_mixture
		
	
	
	
	def get_openmc_reactor_vessel(self):
		"""Creates the pressure vessel representation in OpenMC
		
		Inputs:
			vera_core:		instance of objects.Core
		
		Outputs:
			openmc_vessel:	instance of openmc.Universe containing all the cells
							describing the reactor pressure vessel EXCEPT inside_cell
			inside_cell:	instance of openmc.Cell containing the innermost ring
							of the vessel, TO BE FILLED with assemblies
			inside_fill:	string; key of the openmc.Material to fill all spaces
							within inside_cell, outside of the assemblies
			outer_surfs:	instances of openmc.Surface (specifically, ZCylinder and ZPlane)
							describing the bounding	surfaces of the reactor vessel
		"""
		
		ps = self.core.params
		core_cells = []
		
		# Create the top and bottom planes of the core and core plate
		plate_bot = openmc.ZPlane(self.counter.add_surface(),
							z0 = -self.core.bot_refl.thick, boundary_type = self.core.bc["bot"])
		core_bot = openmc.ZPlane(self.counter.add_surface(), z0 = 0.0)
		core_top = openmc.ZPlane(self.counter.add_surface(), z0 = self.core.height)
		plate_top = openmc.ZPlane(self.counter.add_surface(),
							z0 = self.core.height + self.core.top_refl.thick, boundary_type = self.core.bc["top"])
		
		# Create the concentric cylinders of the vessel
		for ring in range(len(self.core.vessel_radii) - 1):
			r = self.core.vessel_radii[ring]
			m = self.core.vessel_mats[ring]
			
			s = openmc.ZCylinder(self.counter.add_surface(), R = r)
			
			cell_name = "Vessel_" + str(ring)
			new_cell = openmc.Cell(self.counter.add_cell(), cell_name)
			
			if ring == 0:
				# For the center ring,
				new_cell.region = -s & +core_bot & -core_top
				inside_cell = new_cell
				inside_fill = m
				last_s = s
				vessel_surf = s
			else:
				new_cell.region = -s & +last_s & +plate_bot & -plate_top
				new_cell.fill = self.get_openmc_material(m)
				last_s = s
				core_cells.append(new_cell)
		
		# And finally, the outermost ring
		s = openmc.ZCylinder(self.__counter(SURFACE), R = max(self.core.vessel_radii), boundary_type = self.core.bc["rad"])
		new_cell = openmc.Cell(self.__counter(CELL), "Vessel-Outer")
		new_cell.region = -s    & +plate_bot & -plate_top
		core_cells.append(new_cell)
		
		# Add the core plates
		top_plate_mat = self.get_openmc_material(self.core.bot_refl.material)
		self.openmc_materials[top_plate_mat.name] = top_plate_mat
		top_plate_cell = openmc.Cell(self.__counter(CELL), "Top core plate")
		top_plate_cell.region = -vessel_surf & + core_top & -plate_top
		top_plate_cell.fill = top_plate_mat
		core_cells.append(top_plate_cell)
		
		bot_plate_mat = self.get_openmc_material(self.core.bot_refl.material)
		self.openmc_materials[bot_plate_mat.name] = bot_plate_mat
		bot_plate_cell = openmc.Cell(self.__counter(CELL), "Bot core plate")
		bot_plate_cell.region = -vessel_surf & + core_bot & -plate_bot
		bot_plate_cell.fill = bot_plate_mat
		core_cells.append(bot_plate_cell)
		
		outer_surfs = (vessel_surf, plate_bot, plate_top)
		
		openmc_vessel = openmc.Universe(self.__counter(UNIVERSE), "Reactor Vessel")
		openmc_vessel.add_cells(core_cells)
		
		return openmc_vessel, inside_cell, inside_fill, outer_surfs
			
	
	def add_insert(self, base_lattice, insert):
		"""Insert a burnable poision, thimble plug, or other arbitrary object to a lattice.
		
		Inputs:
			base_lattice:		instance of openmc.RectLattice
			insert:				instance of objects.Insert with the same
								number of pins as base_lattice
		
		Outputs:
			new_lattice:		instance of openmc.RectLattice with some cells replaced
		"""
		n = insert.npins
		x = base_lattice.size[0]
		y = base_lattice.size[1]
		assert(n == x and n == y), \
			"'base_lattice' must be exactly " + str(n) + "x" + str(n) + " pins."
		
		
		
		
		return None
	
	
	
	
	
	
	
	
	def get_openmc_core_lattice(self, blank = "-"):
		"""Create the reactor core lattice.
		
		This is an extremely important function that hasn't really been written yet.
		What it needs to do is iterate through the shape map.
			If an assembly belongs in that location:
				check for inserts, controls, and detectors
				refer to the assembly map
				get_openmc_assembly(asmbly, inserts, controls, detectors)
					get_openmc_lattices() based on that
				we then have an instance of pwr.Assembly
				place that in the core map
			Else:
				fill with mod
		Then zip this lattice up in a universe and return it.
		Later, that will be placed inside the baffle, and the reactor vessel.
		
		Input:
			blank:			string which represents a location in a core map with no insertion.
							[Default: "-"]
		Output:
			openmc_core:	instance of openmc.RectLattice; the lattice contains [read: will contain]
							instances of pwr.Assembly
		"""
		shape, asmap = self.core.square_maps(space = "")
		n = len(shape)
		halfwidth = self.core.pitch * n / 2.0
		
		openmc_core = openmc.RectLattice(self.__counter(UNIVERSE), "Core Lattice")
		openmc_core.pitch = (self.core.pitch, self.core.pitch)
		openmc_core.lower_left = [-halfwidth * n / 2.0] * 2
		openmc_core.outer = self.mod_verse
		
		ins_map = self.core.insert_map.square_map()
		det_map = self.core.detector_map.square_map()
		crd_map = self.core.control_map.square_map()
		crd_bank_map = self.core.control_bank.square_map()
		
		lattice = [[None,]*n]*n
		
		print("Generating core (this may take a while)...")
		for j in range(n):
			new_row = [None,]*n
			for i in range(n):
				# Check if there is supposed to be an assembly in this position
				if shape[j][i]:
					askey = asmap[j][i].lower()
					vera_asmbly = self.assemblies[askey]
					
					ins_key = ins_map[j][i]
					det_key = det_map[j][i]
					crd_key = crd_map[j][i]
					crd_bank_key = crd_bank_map[j][i]
					
					if (ins_key or crd_key or det_key) != blank:
						vera_asmbly = copy(vera_asmbly)
						# Handle each type of insertion differently.
						if ins_key != blank:
							vera_ins = self.inserts[ins_key]
							vera_asmbly.add_insert(vera_ins)
							vera_asmbly.name += "+" + vera_ins.name
						if crd_key != blank:
							vera_crd = self.controls[crd_key]
							steps = self.state.rodbank[crd_bank_key]
							depth = steps*vera_crd.step_size
							vera_asmbly.add_insert(vera_crd, depth)
							vera_asmbly.name += "+" + vera_crd.name
						if det_key != blank:
							# Is it any different than a regular insert?
							vera_det = self.detectors[det_key]
							vera_asmbly.add_insert(vera_det)
							vera_asmbly.name += "+" + vera_det.name
					
					openmc_assembly = self.get_openmc_assembly(vera_asmbly)
					
					new_row[i] = openmc_assembly.universe
				else:
					# Then install the moderator universe instead
					#new_row[i] = 0 # REPLACE WITH: that universe
					new_row[i] = self.mod_verse
			lattice[j] = new_row
		
		
		openmc_core.universes = lattice
		
		return openmc_core
	
	
	
	

if __name__ == "__main__":
	# Instantiate a test case with a representative VERA XML.gold
	#filename = "gold/p7.xml.gold"
	#filename = "gold/2a_dep.xml.gold"
	filename = "gold/2e.xml.gold"
	test_case = MC_Case(filename)
	#print "Testing:",  test_case
	
	
	print("\nInspecting the children")
	for child in test_case.root:
		if child.tag == "ParameterList":
			print(child.attrib["name"])
			
	#print test_case.describe()
	all_pins = []
	for a in test_case.assemblies.values():
		for cm in a.cellmaps.values():
			continue
			# comment out 'continue' to look at the cell maps
			print(a, ':\t', cm)
			print(cm.str_map())
			print("-"*18)
		#print a.params
		for c in a.cells.values():
			new_pin = test_case.get_openmc_pincell(c)
			all_pins.append(new_pin)
			if new_pin.name == "Cell_1-verse":
				mypin = new_pin
	
	#print cm.square_map()
	

	test_asmblys = test_case.get_openmc_lattices(a)[0]
	#print(test_asmbly)
	
	core, icell, ifill, cyl = test_case.get_openmc_reactor_vessel()
	#print(test_case.core.square_maps("a", ''))
	print(test_case.core.str_maps("shape"))
	b = test_case.get_openmc_baffle()
	print(str(b))
	#print(core)
	
	test_case.get_openmc_spacergrids(a.spacergrids, clean(a.params["grid_map"]), clean(a.params["grid_elev"]), 17, a.pitch)
	
	last_cell = list(mypin.cells.values())[-1]
	print(last_cell)
	print()
	#print(last_cell.region.surface())
	
	
	core_lattice = test_case.get_openmc_core_lattice()
	
	
	
	
