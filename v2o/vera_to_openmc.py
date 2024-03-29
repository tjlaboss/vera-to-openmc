# Vera to OpenMC
#
# Takes a VERA case and attempts to construct 
# the required files for an OpenMC input.

import numpy
import math
import openmc
import pwr
from copy import copy
from v2o.objects import Nozzle
from v2o.read_xml import Case
from v2o.functions import fill_lattice, clean


class MC_Case(Case):
	"""An extension of the Case class from read_xml,
	customized with some new attributes and methods to 
	generate objects for OpenMC."""
	
	def __init__(self, source_file):
		super(MC_Case, self).__init__(source_file)
		
		self.openmc_surfaces = []
		# The following dictionaries use key-value pairs of 'coefficient':openmc.Surface
		self.openmc_xplanes = {}  # {str(x0):openmc.XPlane)
		self.openmc_yplanes = {}  # {str(y0):openmc.YPlane)
		self.openmc_zplanes = {}  # {str(z0):openmc.ZPlane)
		self.openmc_cylinders = {}  # {str(R):openmc.Cylinder)
		
		self.openmc_materials = {}
		self.openmc_pincells = {}
		self.openmc_assemblies = {}
		
		# ID Counter
		# Starting at 99 makes all IDs triple digits
		self.counter = pwr.Counter(99, 99, 99, 99)
		
		# Define custom material color dictionary (populated by self.colors)
		self.col_spec = {}
		
		# Create the essential moderator material
		'''The outside of each cell is automatically filled with the special material "mod", which refers to
		the moderator (or coolant). The composition of "mod" is calculated by the codes using the local T/H
		conditions and the soluble boron concentration, and cannot be specified by a user on a mat card.'''
		self.mod = self.get_openmc_material("mod")
		self.mod.add_s_alpha_beta("c_H_in_H2O")
		
		# Create an infinite cell/universe of moderator
		self.mod_cell = openmc.Cell(self.counter.add_cell(), name = "Infinite Mod Cell", fill = self.mod)
		self.mod_verse = openmc.Universe(self.counter.add_universe(),
		                                 name = "Infinite Mod Universe", cells = (self.mod_cell,))
	
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
			surfdict = self.openmc_xplanes
		elif dim in ("y", "yp", "yplane"):
			surfdict = self.openmc_yplanes
		elif dim in ("z", "zp", "zplane"):
			surfdict = self.openmc_zplanes
		elif dim in ("r", "cyl", "cylinder", "zcylinder"):
			surfdict = self.openmc_cylinders
		else:
			raise AssertionError(str(dim) + " is not an acceptable Surface type.")
		openmc_surf = pwr.get_surface(self.counter, surfdict, dim, coeff, name, rd)
		return openmc_surf
	
	def get_axial_zones(self, d = 4):
		"""Return lists used for the axial power distribution tally.
		
		Inputs:
			d:      int; number of decimal places to consider
					a mesh spacing "equal"
					[Default: 4]
		
		Outputs:
			nzs:    list of ints; the number of z cuts in a mesh layer
			dzs:    list of floats; the size of a z cut (cm) in a mesh layer
			z0:     float; where the z cuts start (cm)
		"""
		z0 = self.axial_edits[0]
		n = len(self.axial_edits)
		dzs = []
		nzs = []
		z = z0
		dz0 = self.axial_edits[1] - self.axial_edits[0]
		dz_count = 0
		seq = [dz0]
		
		def avg_dz(dzvals, m):
			return round(sum(dzvals)/m, d)
		
		for i in range(n - 1):
			dz1 = self.axial_edits[i + 1] - z
			if math.isclose(dz1, dz0, abs_tol = 10**(1 - d)):
				dz_count += 1
				seq.append(dz1)
			else:
				if dz_count:
					nzs.append(dz_count)
					dzs.append(avg_dz(seq, dz_count))
				dz_count = 1
				seq = [dz1]
			z += dz1
			dz0 = dz1
		# Conclude the loop
		nzs.append(dz_count)
		dzs.append(avg_dz(seq, dz_count))
		return nzs, dzs, z0
	
	def get_openmc_baffle(self):
		"""Calls pwr.get_openmc_baffle() with the
		properties of this case and core.

		Output:
			baffle_cell:        instance of openmc.Cell describing the baffle geometry.
		"""
		
		mat = self.get_openmc_material(self.core.baffle.mat)
		t = self.core.baffle.thick
		gap = self.core.baffle.gap
		baf = pwr.Baffle(mat, t, gap)
		cmap = self.core.shape.square_map
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
			m_id = self.counter.add_material()
			openmc_material = openmc.Material(m_id, material)
			openmc_material.set_density("g/cc", vera_mat.density)
			openmc_material.temperature = vera_mat.temperature
			for nuclide in sorted(vera_mat.isotopes):
				frac = vera_mat.isotopes[nuclide]
				if nuclide[-2:] == "00":
					# Natural abundance-expand except for Carbon
					ename = nuclide[:-2]
					# Element.expand() breaks an element into its constituent nuclides
					openmc_material.add_element(openmc.Element(ename), frac, 'wo')
				else:
					openmc_material.add_nuclide(nuclide, frac, 'wo')
			if material in self.colors:
				self.col_spec[openmc_material] = self.colors[material]
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
				s = self.__get_surface("cylinder", r, name = name)
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
			lattice = openmc.RectLattice(self.counter.add_universe(), latname)
			lattice.pitch = (pitch, pitch)
			lattice.lower_left = [-pitch * float(npins) / 2.0] * 2
			# And populate with universes from cell_verses
			asmap = vera_asmbly.key_maps[latname]
			
			lattice.universes = fill_lattice(asmap, lambda c:cell_verses[c], npins)
			lattice.outer = self.mod_verse  # To account for the assembly gap
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
			pwr_asmbly.xplanes = self.openmc_xplanes
			pwr_asmbly.yplanes = self.openmc_yplanes
			pwr_asmbly.zplanes = self.openmc_zplanes
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
				
				pwr_asmbly.spacers = clean(ps["grid_map"], lambda key:vera_asmbly.pwr_spacers[key])
				pwr_asmbly.spacer_mids = clean(ps["grid_elev"], float)
			
			# Handle nozzles
			
			if "lower_nozzle_comp" in ps:
				if "lower" not in vera_asmbly.pwr_nozzles:
					nozzle_mat = self.get_openmc_material(ps["lower_nozzle_comp"])
					mass = float(ps["lower_nozzle_mass"])
					height = float(ps["lower_nozzle_height"])
					lnozmat = self.get_nozzle_mixture(height, mass, nozzle_mat, self.mod, npins, pitch,
					                                  "lower-nozzle-mat")
					lnoz = Nozzle(height, lnozmat, "Lower Nozzle")
					vera_asmbly.pwr_nozzles["lower"] = lnoz
				else:
					lnoz = vera_asmbly.pwr_nozzles["lower"]
				pwr_asmbly.lower_nozzle = lnoz
			if "upper_nozzle_comp" in ps:
				if "upper" not in vera_asmbly.pwr_nozzles:
					nozzle_mat = self.get_openmc_material(ps["upper_nozzle_comp"])
					mass = float(ps["upper_nozzle_mass"])
					height = float(ps["upper_nozzle_height"])
					unozmat = self.get_nozzle_mixture(height, mass, nozzle_mat, self.mod, npins, pitch,
					                                  "upper-nozzle-mat")
					unoz = Nozzle(height, unozmat, "Upper Nozzle")
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
			v = (npins * pitch) ** 2 * height
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
		# Intentionally does not use self.__get_surface() due to specific boundary conditions.
		plate_bot = openmc.ZPlane(surface_id=self.counter.add_surface(),
		                          z0=-self.core.bot_refl.thick, boundary_type=self.core.bc["bot"])
		core_bot = openmc.ZPlane(surface_id=self.counter.add_surface(), z0 = 0.0)
		core_top = openmc.ZPlane(surface_id=self.counter.add_surface(), z0 = self.core.height)
		plate_top = openmc.ZPlane(surface_id=self.counter.add_surface(),
		                          z0=self.core.height + self.core.top_refl.thick, boundary_type=self.core.bc["top"])
		zregion = +core_bot & -core_top
		
		# Create the concentric cylinders of the vessel
		for ring in range(len(self.core.vessel_radii) - 1):
			r = self.core.vessel_radii[ring]
			m = self.core.vessel_mats[ring]
			s = openmc.ZCylinder(surface_id=self.counter.add_surface(), r=r)
			cell_name = "Vessel_" + str(ring)
			new_cell = openmc.Cell(self.counter.add_cell(), cell_name)
			
			if ring == 0:
				# For the center ring,
				new_cell.region = -s & +core_bot & -core_top
				inside_cell = new_cell
				inside_fill = m
				vessel_surf = s
				last_s = s
			elif ring == 3:
				# Neutron pad
				pad_fill = self.get_openmc_material(m)
				region = -s & +last_s & +plate_bot & -plate_top
				pads = pwr.Neutron_Pads(region, pad_fill, self.mod, counter = self.counter)
				new_cells = pads.get_cells()
				core_cells += new_cells
				last_s = s
			else:
				new_cell.region = -s & +last_s & +plate_bot & -plate_top
				new_cell.fill = self.get_openmc_material(m)
				last_s = s
				core_cells.append(new_cell)
		
		# And finally, the outermost ring
		vessel_outer = openmc.ZCylinder(surface_id=self.counter.add_surface(),
		                                r=max(self.core.vessel_radii),
		                                boundary_type=self.core.bc["rad"])
		new_cell = openmc.Cell(self.counter.add_cell(), "Vessel-Outer")
		new_cell.region = -vessel_outer & +last_s & +plate_bot & -plate_top
		m = self.core.vessel_mats[-1]
		new_cell.fill = self.get_openmc_material(m)
		core_cells.append(new_cell)
		
		# Add the core plates
		top_plate_mat = self.get_openmc_material(self.core.bot_refl.material)
		self.openmc_materials[top_plate_mat.name] = top_plate_mat
		top_plate_cell = openmc.Cell(self.counter.add_cell(), "Top core plate")
		top_plate_cell.region = -vessel_surf & +core_top & -plate_top
		top_plate_cell.fill = top_plate_mat
		core_cells.append(top_plate_cell)
		
		bot_plate_mat = self.get_openmc_material(self.core.bot_refl.material)
		self.openmc_materials[bot_plate_mat.name] = bot_plate_mat
		bot_plate_cell = openmc.Cell(self.counter.add_cell(), "Bot core plate")
		bot_plate_cell.region = -vessel_surf & +plate_bot & -core_bot
		bot_plate_cell.fill = bot_plate_mat
		core_cells.append(bot_plate_cell)
		
		outer_surfs = (vessel_outer, plate_bot, plate_top)
		
		openmc_vessel = openmc.Universe(self.counter.add_universe(), "Reactor Vessel")
		openmc_vessel.add_cells(core_cells)
		
		return openmc_vessel, inside_cell, zregion, outer_surfs
	
	
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
		shape = self.core.shape.square_map
		asmap = self.core.asmbly.square_map
		ny, nx = shape.shape
		halfwidthx = self.core.pitch*nx/2.0
		halfwidthy = self.core.pitch*ny/2.0
		
		openmc_core = openmc.RectLattice(self.counter.add_universe(), "Core Lattice")
		openmc_core.pitch = (self.core.pitch, self.core.pitch)
		openmc_core.lower_left = [-halfwidthx, -halfwidthy]
		openmc_core.outer = self.mod_verse
		
		ins_map = self.core.insert_map.square_map
		det_map = self.core.detector_map.square_map
		crd_map = self.core.control_map.square_map
		crd_bank_map = self.core.control_bank.square_map
		
		lattice = numpy.empty((ny, nx), dtype=openmc.Universe)
		
		print("Generating core (this may take a while)...")
		for j in range(ny):
			for i in range(nx):
				print("\rConfiguring position: " + str(j) + "x" + str(i) + "...", end = "")  # debug
				# Check if there is supposed to be an assembly in this position
				if shape[j, i]:
					askey = asmap[j, i].lower()
					vera_asmbly = self.assemblies[askey]
					
					ins_key = ins_map[j, i]
					det_key = det_map[j, i]
					crd_key = crd_map[j, i]
					crd_bank_key = crd_bank_map[j, i]
					
					if not ((ins_key == blank) and (crd_key == blank) and (det_key == blank)):
						vera_asmbly = copy(vera_asmbly)
						# Handle each type of insertion differently.
						if ins_key != blank:
							vera_ins = self.inserts[ins_key]
							vera_asmbly.add_insert(vera_ins)
							vera_asmbly.name += "+" + vera_ins.name
						if crd_key != blank:
							vera_crd = self.controls[crd_key]
							steps = self.state.rodbank[crd_bank_key]
							depth = steps * vera_crd.step_size
							vera_asmbly.add_insert(vera_crd, depth)
							vera_asmbly.name += "+" + vera_crd.name
						if det_key != blank:
							# Is it any different than a regular insert?
							vera_det = self.detectors[det_key]
							vera_asmbly.add_insert(vera_det)
							vera_asmbly.name += "+" + vera_det.name
					
					openmc_assembly = self.get_openmc_assembly(vera_asmbly)
					
					lattice[j, i] = openmc_assembly.universe
				else:
					# No fuel assembly here: fill it with moderator
					lattice[j, i] = self.mod_verse
		
		openmc_core.universes = lattice
		print("\tDone.")
		return openmc_core
	
	def build_reactor(self):
		"""Tie all the core components and vessel together into one universe.

		Outputs:
			reactor:        instance of openmc.Universe
			outer_surfs:    tuple containing the following Surfaces, with the boundary
							conditions specified in the VERA deck:
			        			vessel_surf: openmc.ZCylinder bounding the outside edge of the reactor vessel
			        			plate_bot:   openmc.ZPlane bounding the bottom of the lower core plate
			        			plate_top:   openmc.ZPlane bounding the top of the upper core plate
		"""
		reactor, core_cell, zregion, outer_surfs = self.get_openmc_reactor_vessel()
		# Wrap the core cell around the baffle before vertically bounding the baffle
		baffle = self.get_openmc_baffle()
		core_cell.region &= ~baffle.region
		core_lattice = self.get_openmc_core_lattice()
		core_cell.fill = core_lattice
		reactor.add_cell(core_cell)
		# Now it is safe to put upper and lower bounds on the baffle
		baffle.region &= zregion
		reactor.add_cell(baffle)
		
		return reactor, outer_surfs


if __name__ == "__main__":
	# Instantiate a test case with a representative VERA XML.gold
	filename = "gold/p7.xml.gold"
	test_case = MC_Case(filename)
	print("Testing:", test_case)
	
	a = list(test_case.assemblies.values())[0]
	test_asmblys = test_case.get_openmc_lattices(a)[0]
	# print(test_asmbly)
	
	# core, icell, ifill, cyl = test_case.get_openmc_reactor_vessel()
	# print(test_case.core.square_maps("a", ''))
	# print(test_case.core.str_maps("shape"))
	# b = test_case.get_openmc_baffle()
	# print(str(b))
	
	# core_lattice = test_case.get_openmc_core_lattice()
	# print(core_lattice)
	test_case.build_reactor()



