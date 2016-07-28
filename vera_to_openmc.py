# Vera to OpenMC
#
# Takes a VERA case and attempts to construct 
# the required files for an OpenMC input.

from read_xml import Case
from openmc.opencg_compatible import get_openmc_material

try:
	import openmc
except ImportError:
	print "Error: Cannot import openmc. You will not be able to generate OpenMC objects."



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
		
		
		# Create the essential moderator material
		# FIXME: This uses a simple form of water as a placeholder and
		# does NOT represent the actual material composition of the moderator!
		mod_id = self.openmc_material_count
		self.openmc_material_count += 1
		self.mod = openmc.Material(mod_id, "mod")
		self.mod.set_density("g/cc", 1.0)
		self.mod.add_nuclide("h-1", 2.0/3, 'ao')
		self.mod.add_nuclide("o-16", 1.0/3, 'ao')
		
		
		
	def get_openmc_material(self, material):
		'''Given a vera material (objects.Material) as extracted by self.__get_material(),
		create and return an instance of openmc.Material.
		'''
		
		mat_id = self.openmc_material_count
		self.openmc_material_count += 1
		
		
		
		openmc_material = openmc.material.Material(mat_id, material.key_name)
		openmc_material.set_density("g/cc", material.density)
		for i in range(len(material.mat_names)):
			nuclide = material.mat_names[i]
			frac = material.mat_fracs[i]
			# TODO: Figure out from VERAin whether wt% or atom fraction
			openmc_material.add_nuclide(nuclide, frac, 'wo')
		return openmc_material
	
	def get_openmc_pincell(self, vera_cell):
		'''Inputs:
			vera_cell:		instance of objects.Cell from the vera deck
		
		Outputs:
			openmc_cells:	list of instance of openmc.universe.Cell
			cell_surfs:		dictionary of the surfaces that openmc_cell is bounded by
							{surf_id : openmc.surface.Surface} '''
		
		openmc_cells = []
		cell_surfs = {}
		
		# First, define the OpenMC surfaces (Z cylinders)
		for ring in range(vera_cell.num_rings):
			r = vera_cell.radii[ring]
			name = vera_cell.name + "-ring" + str(ring)
			cell_id = self.openmc_cell_count
			self.openmc_cell_count += 1
			# Check if the outer bounding surface exists
			surf_id = None
			for s in self.openmc_surfaces:
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
				cell_surfs[surf_id] = s
				# Thought: Currently, this method returns a list of the new surfaces.
				# Would it be better just to add them directly to the registry from within?
				#self.openmc_surfaces[str(surf_id)] = s
				
			# Otherwise, the surface s already exists
			# Proceed to define the cell inside that surface:
			last_s = s
			new_cell = openmc.universe.Cell(cell_id, name)
			if ring == 0:
				# Inner ring
				new_cell.region = -s
			else:
				# Then this OpenMC cell is outside the previous (last_s), inside the current
				new_cell.region = -s & +last_s 
			
			
			
			# The next line is a quick hack for debugging purposes
			fill = self.get_openmc_material(self.materials[vera_cell.mats[ring]])
			# What I want to do instead is, somewhere else in the code, generate the corresponding
			# openmc material for each objects.Material instance. Then, just look it up in that dictionary.			
			new_cell.fill = fill
			openmc_cells.append(new_cell)
		
		# end of "for ring" loop
		
		# Then add the moderator outside the pincell
		mod_cell_id = self.openmc_cell_count
		self.openmc_cell_count += 1
		mod_cell = openmc.universe.Cell(mod_cell_id, vera_cell.name + "-Mod")
		mod_cell.fill = self.mod
		mod_cell.region = +last_s
		openmc_cells.append(mod_cell)
		
		# Create a new universe in which the pin cell exists 
		u_num = self.openmc_universe_count
		self.openmc_universe_count += 1
		pincell_universe = openmc.universe.Universe(u_num, vera_cell.name + "-verse")
		pincell_universe.add_cells(openmc_cells)
		
		return pincell_universe, cell_surfs 
	
	
	

if __name__ == "__main__":
	# Instantiate a case with a simple VERA XML.gold
	#filename = "p7.xml.gold"
	filename = "2a_dep.xml.gold"
	test_case = MC_Case(filename)
	
	#print "Testing:",  test_case
	
	
	print "\nInspecting the children"
	for child in test_case.root:
		if child.tag == "ParameterList":
			print child.attrib["name"]
			
	
	print
	
	#print test_case.describe()
	for a in test_case.assemblies.values():
		for g in a.spacergrids:
			print a, '\t:\t', g
		#print a.params
		for c in a.cells.values():
			#print c
			continue
	
	mc_test_mat = test_case.get_openmc_material(test_case.materials["pyrex"])
	print mc_test_mat
	
	#print test_case.mod
	
	pincell_cells = test_case.get_openmc_pincell(c)[0]
	print pincell_cells
	
	
	
	
	
	


