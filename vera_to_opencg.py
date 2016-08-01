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
		
		self.opencg_surfaces = {}
		
		
		# ID Counters
		# 0 is special for universes, and in some codes, surfs/cells/mats start at 1;
		# so I'm starting the count at 1 here instead of 0.
		self.opencg_surface_count = 1; self.opencg_cell_count = 1 ;self.opencg_material_count = 1; self.opencg_universe_count = 1
		
		
		# Create the essential moderator material
		mod_id = self.opencg_material_count
		self.opencg_material_count += 1
		self.mod = opencg.material.Material(mod_id, "mod")
		self.opencg_materials = {"mod":self.mod,}
		

	
	
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
			for s in self.opencg_surfaces.values():
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
				self.opencg_surfaces[str(surf_id)] = s
				
			
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
			
			
			# Fill the cell in with a material
			m = vera_cell.mats[ring]
			try:
				fill = self.opencg_materials[m]
			except KeyError:
				# Then the material doesn't exist yet in OpenCG form
				# Generate it?
				fill = self.get_opencg_material(self.materials[m])
				# And add it to the index
				self.opencg_materials[m] = fill
			
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
		
		return pincell_universe
	
	
	def get_opencg_assemblies(self, vera_asmbly):
		'''Creates the assembly geometry (WIP) and lattices of pin cells (done)
		required to define a rectangular lattice in OpenCG.
		
		Inputs:
			vera_asmbly:		instance of objects.Assembly
		
		Outputs:
			opencg_asmblies:	list of instance of opencg.Lattice
		'''
		
		ps = vera_asmbly.params
		pitch = vera_asmbly.pitch
		npins = vera_asmbly.npins
		opencg_asmblies = []
		
		# Instantiate all the pin cells (opencg.Universe) that appear in the Assembly
		cell_verses = {}
		for vera_cell in vera_asmbly.cells.values():
			c = self.get_opencg_pincell(vera_cell)
			cell_verses[vera_cell.label] = c
		
		for latname in vera_asmbly.axial_labels:
			u_num = self.opencg_universe_count
			self.opencg_universe_count += 1	
			opencg_asmbly = opencg.Lattice(u_num, latname, "rectangular")
			opencg_asmbly.pitch = (pitch, pitch)
			opencg_asmbly.lower_left = [-pitch * float(npins) / 2.0] * 2
			# And populate with universes from cell_verses
			asmap = vera_asmbly.cellmaps[latname].square_map()
			lattice = [[None,]*npins]*npins
			for i in range(npins):
				new_row = [None,]*npins
				for j in range(npins):
					c = asmap[i][j]
					new_row[j] = cell_verses[c]
				lattice[i] = new_row
			
			opencg_asmbly.universes = lattice
			opencg_asmblies.append(opencg_asmbly)
		
		return opencg_asmblies
	
	
	
	
	
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
	
	#pincell_verse = test_case.get_opencg_pincell(c)[0]
	#print pincell_verse
	
	asmblys = test_case.get_opencg_assemblies(a)
	#print len(test_case.get_opencg_assemblies(a))		
		




