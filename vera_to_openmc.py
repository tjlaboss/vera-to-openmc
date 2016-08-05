# Vera to OpenMC
#
# Takes a VERA case and attempts to construct 
# the required files for an OpenMC input.

from read_xml import Case

try:
	import openmc
except ImportError:
	raise SystemExit("Error: Cannot import openmc. You will not be able to generate OpenMC objects.")



class MC_Case(Case):
	'''An extension of the Case class from read_xml,
	customized with some new attributes and methods to 
	generate objects for OpenMC.'''
	def __init__(self, source_file):
		super(MC_Case, self).__init__(source_file)
		
		self.openmc_surfaces = {}
		
		# ID Counters
		# 0 is special for universes, and in some codes, surfs/cells/mats start at 1;
		# so I'm starting the count at 1 here instead of 0.
		self.openmc_surface_count = 1; self.openmc_cell_count = 1 ;self.openmc_material_count = 1; self.openmc_universe_count = 1
		
		self.openmc_materials = {}
		
		
		# Create the essential moderator material
		'''The outside of each cell is automatically filled with the special material "mod", which refers to
		the moderator (or coolant). The composition of "mod" is calculated by the codes using the local T/H
		conditions and the soluble boron concentration, and cannot be specified by a user on a mat card.
		FIXME: The material uses a simple form of water as a placeholder and does NOT represent the actual
		composition of the moderator!'''
		mod_id = self.openmc_material_count
		self.openmc_material_count += 1
		self.mod = openmc.Material(mod_id, "mod")
		self.mod.set_density("g/cc", 1.0)
		self.mod.add_nuclide("h-1", 2.0/3, 'ao')
		self.mod.add_nuclide("o-16", 1.0/3, 'ao')
		self.openmc_materials["mod"] = self.mod
		
		
	def get_openmc_material(self, material):
		'''Given a vera material (objects.Material) as extracted by self.__get_material(),
		create and return an instance of openmc.Material.
		
		All of the material fractions sum to either +1.0 or -1.0. If positive fractions are used, they
		refer to weight fractions. If negative fractions are used, they refer to atomic	fractions.
		'''
		
		mat_id = self.openmc_material_count
		self.openmc_material_count += 1
		
		openmc_material = openmc.Material(mat_id, material.key_name)
		openmc_material.set_density("g/cc", material.density)
		for i in material.isotopes:
			nuclide = i
			frac = material.isotopes[i]
			if frac < 0:
				openmc_material.add_nuclide(nuclide, abs(frac), 'ao')			
			else:
				openmc_material.add_nuclide(nuclide, frac, 'wo')
		return openmc_material
	
	
	def try_openmc_material(self, m):
		'''Check if a material exists; if it doesn't, add it to the index
		
		Input:
			m:		string; key of a VERA material in self.materials
		Output:
			mat:	instance of openmc.Material
		'''
		try:
			# Look it up as normal
			mat = self.openmc_materials[m]
		except KeyError:
			# Then the material really doesn't exist yet in OpenMC form
			# Generate it and add it to the index 
			mat = self.get_openmc_material(self.materials[m])
			self.openmc_materials[m] = mat
		
		return mat
	
	
	
	
	def get_openmc_pincell(self, vera_cell):
		'''Inputs:
			vera_cell:			instance of objects.Cell from the vera deck
		
		Outputs:
			pincell_universe:	instance of openmc.Universe, containing:
				.cells:				list of instances of openmc.Cell, describing the
									geometry and composition of this pin cell's universe
				.universe_id:	integer; unique identifier of the Universe
				.name:			string; more descriptive name of the universe (pin cell)			
			'''
		
		openmc_cells = []
		
		# First, define the OpenMC surfaces (Z cylinders)
		for ring in range(vera_cell.num_rings):
			r = vera_cell.radii[ring]
			name = vera_cell.name + "-ring" + str(ring)
			# Check if the outer bounding surface exists
			surf_id = None
			for s in self.openmc_surfaces.values():
				if (s.type == "z-cylinder"):
					if (s.r == r) and (s.x0 == 0) and (s.y0 == 0):
						# Then the cylinder is the same
						surf_id = s.id
						break # from the "for s in" loop
			if not surf_id:
				# Generate new surface and get its surf_id
				surf_id = self.openmc_surface_count
				self.openmc_surface_count += 1
				s = openmc.ZCylinder(surf_id, "transmission", 0, 0, r)
				#cell_surfs[surf_id] = s
				# Add the new surfaces to the registry
				self.openmc_surfaces[str(surf_id)] = s
				
			# Otherwise, the surface s already exists
			# Proceed to define the cell inside that surface:
			cell_id = self.openmc_cell_count
			self.openmc_cell_count += 1
			new_cell = openmc.Cell(cell_id, name)
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
			try:
				# First, check if this is a local, duplicate material
				fill = self.openmc_materials[vera_cell.asname + m]
				# This normally will not exist, so:
			except KeyError:
				fill = self.try_openmc_material(m)
			
				
			# What I want to do instead is, somewhere else in the code, generate the corresponding
			# openmc material for each objects.Material instance. Then, just look it up in that dictionary.			
			new_cell.fill = fill
			openmc_cells.append(new_cell)
		
		# end of "for ring" loop
		
		# Then add the moderator outside the pincell
		mod_cell_id = self.openmc_cell_count
		self.openmc_cell_count += 1
		mod_cell = openmc.Cell(mod_cell_id, vera_cell.name + "-Mod")
		mod_cell.fill = self.mod
		mod_cell.region = +s
		openmc_cells.append(mod_cell)
		
		# Create a new universe in which the pin cell exists 
		u_num = self.openmc_universe_count
		self.openmc_universe_count += 1
		pincell_universe = openmc.Universe(u_num, vera_cell.name + "-verse")
		pincell_universe.add_cells(openmc_cells)
		
		return pincell_universe
	
	
	
	def get_openmc_assemblies(self, vera_asmbly):
		'''Creates the  assembly geometry and lattices of pin cells
		required to define an assembly in OpenMC.
		
		Inputs:
			vera_asmbly:		instance of objects.Assembly
		
		Outputs:
			openmc_asmblies:	list of instance of openmc.RectLattice
		'''
		
		
		ps = vera_asmbly.params
		pitch = vera_asmbly.pitch
		npins = vera_asmbly.npins
		# Look for optional parameters available from vera_asmbly.params
		# Possible params include:
		# axial_elevations, axial_labels, grid_elev, grid_map,
		# lower_nozzle_comp, lower_nozzle_height, lower_nozzle_mass,
		# upper_nozzle_comp, upper_nozzle_height, upper_nozzle_mass,
		# ppitch, title, num_pins, label
		openmc_asmblies = []
		
		# Instantiate all the pin cells (openmc.Universes) that appear in the Assembly
		cell_verses = {}
		for vera_cell in vera_asmbly.cells.values():
			c = self.get_openmc_pincell(vera_cell)
			cell_verses[vera_cell.label] = c
		
		
		for latname in vera_asmbly.axial_labels:
		
			u_num = self.openmc_universe_count
			self.openmc_universe_count += 1
			
			openmc_asmbly = openmc.RectLattice(u_num, latname)
			
			
			openmc_asmbly.pitch = (pitch, pitch)
			openmc_asmbly.lower_left = [-pitch * float(npins) / 2.0] * 2
			# And populate with universes from cell_verses
			asmap = vera_asmbly.cellmaps[latname].square_map()
			lattice = [[None,]*npins]*npins
			for i in range(npins):
				new_row = [None,]*npins
				for j in range(npins):
					c = asmap[i][j]
					new_row[j] = cell_verses[c]
				lattice[i] = new_row
				
			openmc_asmbly.universes = lattice
			openmc_asmblies.append(openmc_asmbly)
		
		return openmc_asmblies
	
	
	def get_openmc_reactor_vessel(self, vera_core):
		'''Creates the pressure vessel representation in OpenMC
		
		Inputs:
			vera_core:		instance of objects.Core
		
		Outputs:
			openmc_core:	instance of openmc.Universe containing all the cells
							describing the reactor pressure vessel EXCEPT inside_cell
			inside_cell:	instance of openmc.Cell containing the innermost ring
							of the vessel, TO BE FILLED with assemblies
			inside_fill:	string; key of the openmc.Material to fill all spaces
							within inside_cell, outside of the assemblies
			vessel_surf:	instance of openmc.ZCylinder describing the outermost
							surface of the reactor vessel
		'''
		
		ps = vera_core.params
		core_cells = []
		
		# Create the top and bottom planes of the core and core plate
		plate_bot = openmc.ZPlane(z0 = -vera_core.lower_refl.thick, boundary_type = vera_core.bc["bot"])
		core_bot = openmc.ZPlane(z0 = 0.0)
		core_top = openmc.ZPlane(z0 = vera_core.height)
		plate_top = openmc.ZPlane(z0 = vera_core.height + vera_core.upper_refl.thick, boundary_type = vera_core.bc["top"])
		
		# Create the concentric cylinders of the vessel
		for ring in range(len(vera_core.vessel_radii) - 1):
			r = vera_core.vessel_radii[ring]
			m = vera_core.vessel_mats[ring]
			
			s = openmc.ZCylinder(R = r)
			
			cell_id = self.openmc_cell_count
			self.openmc_cell_count += 1
			cell_name = "Vessel-" + str(ring)
			new_cell = openmc.Cell(cell_id, cell_name)
			
			if ring == 0:
				# For the center ring,
				new_cell.region = -s    & +core_bot & -core_top
				inside_cell = new_cell
				inside_fill = m
				last_s = s
				vessel_surf = s
			else:
				new_cell.region = -s & +last_s	& +core_bot & -core_top
				new_cell.fill = self.try_openmc_material(m)
				last_s = s
				core_cells.append(new_cell)
		
		# And finally, the outermost ring
		cell_id = self.openmc_cell_count
		self.openmc_cell_count += 1
		s = openmc.ZCylinder(R = max(vera_core.vessel_radii), boundary_type = vera_core.bc["rad"])
		new_cell = openmc.Cell(cell_id, "Vessel-Outer")
		new_cell.region = -s    & +core_bot & -core_top
		core_cells.append(new_cell)
		
		# TODO: Define the regions between the plates
		# 
		
		
		u_num = self.openmc_universe_count
		self.openmc_universe_count += 1
		openmc_core = openmc.Universe(u_num, "Reactor Vessel")
		openmc_core.add_cells(core_cells)
		
		return openmc_core, inside_cell, inside_fill, vessel_surf
	
	
	
			
	
	
	

if __name__ == "__main__":
	# Instantiate a test case with a simple VERA XML.gold
	filename = "p7.xml.gold"
	#filename = "2a_dep.xml.gold"
	#filename = "2o.xml.gold"
	test_case = MC_Case(filename)
	#print "Testing:",  test_case
	
	
	print("\nInspecting the children")
	for child in test_case.root:
		if child.tag == "ParameterList":
			print(child.attrib["name"])
			
	print
	
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
	
	#mc_test_mat = test_case.get_openmc_material(test_case.materials["pyrex"])
	#print mc_test_mat
	
	#print test_case.mod
	
	
	'''Note: Attempting to print an assembly doesn't work. Could be due to a bug in the
	__repr__() method? Printing here yields an AttributeError: 'NoneType' object has no attribute '_id',
	and printing the example assembly from the OpenMC Python API docs
	<http://openmc.readthedocs.io/en/latest/pythonapi/examples/pandas-dataframes.html>
	causes a TypeError: 'NoneType' object has no attribute '__getitem__' '''
	
	test_asmblys = test_case.get_openmc_assemblies(a)[0]
	#print(test_asmbly)
	
	#print('\n', a.name, test_asmblys.name, '\n')
	#for cmap in test_case.core.str_maps(space = "~"):
	#	print(cmap)
	
	core, icell, ifill, cyl = test_case.get_openmc_reactor_vessel(test_case.core)
	print(core)
	
	
	


