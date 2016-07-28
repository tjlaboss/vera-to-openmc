# Vera to OpenCG
#
# Takes a VERA case and attempts to construct 
# the required files for an OpenCG geometry

from read_xml import Case

try:
	import opencg
except ImportError:
	print "Error: Cannot import opencg. You will not be able to generate OpenCG objects."


class CG_Case(Case):
	'''An extension of the Case class from read_xml,
	customized with some new attributes and methods to 
	generate objects for OpenCG.'''
	def __init__(self, source_file):
		super(CG_Case, self).__init__(source_file)
		
		self.opencg_surfaces = []
		
		
		# ID Counters
		# 0 is special for universes, and in some codes, surfs/cells/mats start at 1;
		# so I'm starting the count at 1 here instead of 0.
		self.opencg_surface_count = 1; self.opencg_cell_count = 1 ;self.opencg_material_count = 1; self.opencg_universe_count = 1
		
		# Create the essential moderator material
		mod_id = self.opencg_material_count
		self.opencg_material_count += 1
		self.mod = opencg.material.Material(mod_id, "mod")
		

	
	
	def get_opencg_material(self, material):
		'''Given a vera material (objects.Material) as extracted by self.__get_material(),
		create and return an instance of opencg.Material.
		
		NOTE: This section is largely a placeholder for now, as I am still
		figuring out how to properly use this IDE and haven't imported OpenCG yet.
		'''
		
		mat_id = self.opencg_material_count
		self.opencg_material_count += 1
		
		opencg_material = opencg.material.Material(mat_id, material.key_name)
		# OpenCG materials, to my understanding, do not deal with nuclides
		return opencg_material

				
		
		
	def get_opencg_pincell(self, vera_cell):
		'''Inputs:
			vera_cell:		instance of objects.Cell from the vera deck
		
		Outputs:
			opencg_cells:	list of instance of opencg.universe.Cell
			cell_surfs:		dictionary of the surfaces that opencg_cell is bounded by
							{surf_id : opencg.surface.Surface} '''
		
		opencg_cells = []
		cell_surfs = {}
		#known_surfs = []
		
		# First, define the OpenCG surfaces (Z cylinders)
		for ring in range(vera_cell.num_rings):
			r = vera_cell.radii[ring]
			name = vera_cell.name + "-ring" + str(ring)
			cell_id = self.opencg_cell_count
			self.opencg_cell_count += 1
			# Check if this surface exists
			surf_id = 0
			for s in self.opencg_surfaces:
				if (s.type == "z-cylinder"):
					if (s.r == r) and (s.x0 == 0) and (s.y0 == 0):
						# Then the cylinder is the same
						surf_id = s.id
						break 
			if not surf_id:
				# Generate new surface and get its surf_id
				surf_id = self.opencg_surface_count
				self.opencg_surface_count += 1
				s = opencg.ZCylinder(surf_id, '', "interface", 0, 0, r)
				cell_surfs[surf_id] = s
				
				# Thought: Currently, this method returns a list of the new surfaces.
				# Would it be better just to add them directly to the registry from within?
				#self.opencg_surfaces[str(surf_id)] = s
				
			
			# Otherwise, the surface s already exists
			# Proceed to define the cell inside that surface:
			new_cell = opencg.universe.Cell(cell_id, name)
			new_cell.add_surface(s, -1)
			if ring == 0:
				# Inner ring
				last_s = s
			else:
				# Then this OpenCG cell is outside the previous (last_s), inside the current (s.id)
				new_cell.add_surface(last_s, 1)
				last_s = s
			
			
			# The next line is a quick hack for debugging purposes
			fill = self.get_opencg_material(self.materials[vera_cell.mats[ring]])
			# What I want to do instead is, somewhere else in the code, generate the corresponding
			# opencg material for each objects.Material instance. Then, just look it up in that dictionary.			
			new_cell.fill = fill
			opencg_cells.append(new_cell)
		
		# end of "for ring" loop
		
		# Add one more cell containing the moderator (everything outside the outermost ring)
		mod_cell_id = self.opencg_cell_count
		self.opencg_cell_count += 1
		mod_cell = opencg.universe.Cell(mod_cell_id, vera_cell.name + "-Mod")
		mod_cell.add_surface(last_s, 1)
		mod_cell.fill = self.mod
		opencg_cells.append(mod_cell)
		# Instantiate an OpenCG universe
		u_num = self.opencg_universe_count
		self.opencg_universe_count += 1
		pincell_universe = opencg.universe.Universe(u_num, vera_cell.name + "-verse")
		pincell_universe.add_cells(opencg_cells)
		
		return pincell_universe, cell_surfs
	
	
	
	
	
	
	
	
if __name__ == "__main__":
	# Instantiate a case with a simple VERA XML.gold
	#filename = "p7.xml.gold"
	filename = "2a_dep.xml.gold"
	test_case = CG_Case(filename)
	
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
	
	#cg_test_mat = test_case.get_opencg_material(test_case.materials["ss"])
	#print cg_test_mat
	
	pincell_verse = test_case.get_opencg_pincell(c)[0]
	print pincell_verse		
		




