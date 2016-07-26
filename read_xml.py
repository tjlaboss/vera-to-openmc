# Test 
#
# Learning how to read XML with Python modules
# This is my first time working with XML in Python. Bear with me.
#
# For this program, I want to keep running if errors are encountered in the XML to allow the user
# to fix everything in as few iterations as possible. Therefore, when it detects that something is
# not quite right, it prints out an error message but keeps moving. These events are counted to
# Case.errors, so that somebody using an instance of the Case object can check if they can proceed
# with the results of the XML reading.


import xml.etree.ElementTree as ET
import objects
try:
	import openmc
except ImportError:
	print "Error: Cannot import openmc. You will not be able to generate OpenMC objects."
try:
	import opencg
except ImportError:
	print "Error: Cannot import opencg. You will not be able to generate OpenCG objects."


'''The VERAin XML files have the following structure:

<ParameterList>
	<Parameter name="" ... />
	<ParameterList>
		<Parameter name="" ... />
	</ParameterList>
	...
</ParameterList>

One big ParameterList of ParameterLists containing Parameters and ParameterLists (themselves containing other Parameters and ParameterLists)
The goal here is to extract all of the information needed to construct OpenCG or OpenMC objects. Haven't figured out how to do that part yet.
'''

class Case(object):
	'''Each VERA input deck represents a unique case.
	This is a class of such a case.'''
	
	def __init__(self, source_file):
		'''Loads the VERA XML file, creates some placeholder variables, and calls __read_xml()'''
		
		# Location in the file system of the VERA XML.gold
		self.source_file = source_file
		
		# Read the XML file from disk
		self.tree = ET.parse(self.source_file)
		self.root = self.tree.getroot()
		
		# Initialize the case_id in case we can't find it in the XML
		self.case_id = "Unnamed VERA Case"
		
		# Blocks to use and ignore
		# TODO: Verify that these lists are 100% correct.
		self.usable = ("CORE", "INSERTS", "STATES", "CONTROLS", "DETECTORS", "ASSEMBLIES") # Relevant to OpenMC
		self.ignore = ("SHIFT", "MPACT", "INSILICO", "COBRATF")			# Blocks specific to other codes 
		
		# Initialize some parameters with empty lists
		self.materials = {}
		self.assemblies = {}
		self.states = []
		self.openmc_surfaces = {}
		self.opencg_surfaces = []
		# and more to come... 
		
		# Initialize an important material
		'''The outside of each cell is automatically filled with the special material "mod", which refers to
		the moderator (or coolant). The composition of "mod" is calculated by the codes using the local T/H
		conditions and the soluble boron concentration, and cannot be specified by a user on a mat card.'''
		# TODO: Figure out how to implement this
		# For now, just make it pure H20 at 1 g/cc so that this program runs
		mod = objects.Material(key_name = "mod", density = 1.0, mat_names=["h-1", "o-16"], mat_fracs=[2.0/18, 16.0/18])
		self.materials["mod"] = mod
		
		# Then populate everything:
		self.errors = 0; self.warnings = 0
		self.__read_xml()
		
		
		# ID Counters
		# 0 is special for universes, and in some codes, surfs/cells/mats start at 1;
		# so I'm starting the count at 1 here instead of 0.
		self.openmc_surface_count = 1; self.openmc_cell_count = 1 ;self.openmc_material_count = 1; self.openmc_universe_count = 1
		self.opencg_surface_count = 1; self.opencg_cell_count = 1 ;self.opencg_material_count = 1; self.opencg_universe_count = 1
		
		
		print "There were", self.warnings, "warnings and", self.errors, "errors."
		
	
	def __read_xml(self):
		'''Get and categorize the important parameters from self.source_file
		All entries should be either "Parameter" or "ParameterList"'''
		for child in self.root:
			if child.tag == "Parameter":
				# Get the name of the case
				if child.attrib["name"] == "case_id":
					self.case_id = child.attrib["value"]
				# case_id is the only parameter I expect to see at this level
				# If there are more, they'll go here. Notify the user.
				else:
					print "Error: child.tag is", child.tag + "; name is",  child.attrib["name"]
					print "The script does not know how to handle this; ignoring.\n"
					self.errors += 1
					
			
			elif child.tag == "ParameterList":
				# Proper use of recursion could probably save me a lot of effort here.
				name = child.attrib["name"].upper()	# for brevity
				if name in self.ignore:
					print "Ignoring block", name
				elif name in self.usable:
					# Then handle them appropriately
					if name == "CORE":
						'''The [CORE] block describes the nuclear reactor core configuration. This block describes the core
						layout, including the placement of nuclear fuel assemblies, control rods, detectors, inserts, and
						other core parameters that do not change during a cycle depletion.
						The geometric objects inside the core are defined in separate input blocks; the [CORE] block
						simply describes how all of these objects are placed together.'''
						# The CORE block will contain the deck's global materials
						# and some other stuff
						for core_child in child:
							cname = core_child.attrib["name"].lower()	# for brevity
							if core_child.tag == "ParameterList" and cname == "materials":
								for mat in core_child:
									# Create a material object for each listed material
									new_material = self.__get_material(mat)
									self.materials[new_material.key_name] = new_material
									# WARNING: Right now, this overwrites any material that has the same key.
									# Check if the objects are the same (that is, have the same attributes) before doing this.
																
							elif core_child.tag == "ParameterList":
								print "Unknown parameter list: " + cname + ". Ignoring."
								self.warnings += 1
								
							elif core_child.tag == "Parameter":
								# TODO: This is where the program gets boundary conditions and various other core properties.
								# Things to watch for: apitch, assm_map, bc_bot, bc_rad, bc_top, core_size, height,
								# 	rated_flow, rated_power, and shape
								continue
								
									
							else:
								print "Error: Entry", core_child.tag, "is neither a Parameter nor ParameterList. Ignoring."
								self.errors += 1
								
						
					elif name == "ASSEMBLIES":
						# TODO: Get cells, materials, and all that stuff from the Assemblies block
						# TODO: Check for duplicate materials. (Probably at the end of __init__ after running this function)
						
						for asmbly in child:
							cname = asmbly.attrib["name"].lower()	# for brevity
							# dictionary of all independent parameters for this assembly
							asmbly_params = {}
							grids = {}
							maps = {}
							cells = {}
									
							for asmbly_child in asmbly:
								aname = asmbly_child.attrib["name"].lower()
								if asmbly_child.tag == "Parameter":
									asmbly_params[aname] = asmbly_child.attrib["value"]
								elif asmbly_child.tag == "ParameterList":
									if aname == "cells":
										for cell in asmbly_child:
											new_cell = self.__get_cell(cell, cname)
											cells[new_cell.name] = new_cell
									elif aname ==  "fuels":
										# More materials are found here
										# TODO: "Fuel" and "Material" blocks are written differently.
										# The method self.__get_fuel() really needs some work.
										for fuel in asmbly_child:
											# Create a material object for each listed material
											new_material = self.__get_fuel(fuel)
											self.materials[new_material.key_name] = new_material
									elif aname == "cellmaps":
										for cmap in asmbly_child:
											new_map = self.__get_map(cmap)
											maps[new_map.name] = new_map
									elif aname ==  "spacergrids":
										for grid in asmbly_child:
											new_grid = self.__get_grid(grid)
											grids[new_grid.name] = new_grid
												
									
									else:
										print "Unknown ASSEMBLIES.ParameterList", aname, "-- ignoring"
										self.warnings += 1
								
								else:
									print "Error: Entry", asmbly_child.tag, "is neither a Parameter nor ParameterList. Ignoring for now."
									self.errors += 1
									
							
							# Instantiate an Assembly object and pass it the parameters
							new_assembly = objects.Assembly(name = cname, cells = cells, cellmaps = maps, spacergrids = grids, params = asmbly_params)
							self.assemblies[cname] = new_assembly
							print "Unsure what to do with", len(asmbly_params), "Parameters in", cname, "at this point."
						
						
					elif name == "STATES":
						do_states_stuff = True
					elif name == "CONTROLS":
						do_control_stuff = True
					elif name == "DETECTORS":
						do_detector_stuff = True
					elif name == "INSERTS":
						do_insert_stuff = True
					
					# tmp
					else:
						print name
				
				else:
					print "Warning: Unexpected block encountered:\t", child.attrib["name"]
					print "This may be a flaw within the XML file, or a shortcoming of this script. Ignoring for now."
					self.warnings += 1
			
			else:
				print "Error: child.tag =", child.tag, "-- Ignoring."
				print "Expected either Parameter or ParameterList. There is probably something wrong with the XMl."
				self.errors += 1
		
		# note; end of the giant for loop
	
	
	def __get_material(self, mat):
		'''When a material or fuel block is encountered in the XML,
		extract the useful information.
		
		Inputs:Pass on the assembly Parameters to the instance
			mat: The ParameterList object describing a VERA material
		
		Outputs:
			a_material: Instance of the Material object populated with the properties from the XML.'''
		
		# Initialize the 4 material properties
		mname = ""; mdens = 0.0; mfracs = []; miso_names = []
			
		for prop in mat:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "key_name":
				mname = v
			elif p == "density":
				mdens = float(v)
			elif p == "mat_fracs":
				# Convert a string to a list of floating point numbers
				mfracs = map(float, v.strip('}').strip('{').split(','))
			elif p == "mat_names":
				# Convert a string to a list of strings
				miso_names = v.strip('}').strip('{').split(',')
			else:
				print "Warning: unused property", p
		
		# Check if isotopic fractions each have an associated element
		if len(mfracs) != len(miso_names):
			warning = "Unequal number of isotopes and associated fractions in material", mname
			#raise IndexError(warning)
			print warning
			self.warnings += 1
			
		
		# Instantiate a new material and add it to the dictionary
		a_material = objects.Material(mname, mdens, mfracs, miso_names)
		return a_material
	
	
	
	def __get_fuel(self, fuel):
		'''When a fuel block is encountered in the XML, extract the useful information
		and do the math to create a Material instance.
		
		Inputs:
			fuel: The ParameterList object describing a VERA fuel
		
		Outputs:
			a_material: Instance of the Material object. Should be indistinguishable from
						one generated by self.__get_material().'''
		
		
		'''A fuel is a Material object that is described differently.
	
		Fuel materials are defined with fuel cards. Fuel materials are heavy metal oxides which are
		usually UO 2 with different U-235 enrichments. Fuel materials may also include MOX fuel, which
		consists of mixtures of uranium, plutonium, and other actinides. Fuel materials are different from
		structural materials in that they deplete and have additional properties as described below.


				fuel user-mat density thden / U-235 enrichment {HM material i =HM enrichment i , i=1, N}
				{ / gad material=gad fraction }
		
		Where:
			* user-mat is a user-defined fuel name.
			* density is the fuel material density in g/cc.
			* thden is the percent of theoretical density in the pellet (%). The theoretical density
				is only used to look up material properties in the fuel performance, it is not used
				to calculate number densities. There is no "double counting" between density and thden.
			* U-235 enrichment is the U-235 enrichment in the fuel in weight % (No default).
				- If U-234 and U-236 are not specified, they will automatically be added to the fuel by
					a pre-determined function (see below)
				- If the sum of the heavy metal (HM) enrichments does not equal 100%, the remainder
					of the HM composition will be assigned to U-238.
			* HM material i is the material name for HM isotope i (Pu-239, Pu-241, etc.) (optional) The
				names of the HM materials must be valid library-names.
			* HM enrichment i is the enrichment of HM isotope i in weight % (optional)
			* gad material is the material name for the gadolina oxide (or other material) (optional). The
				gad material is usually a mixture defined on a separate mat card.
			* gad fraction is the weight percent of the gad material relative to the total fuel mass (optional)
				Oxygen should not be included on the fuel card. The correct amount of oxygen will automatically
				be added to the HM to create an oxide (either UO 2 or (HM)O 2 ).
				The density is the "stack density" or "smeared density" and should include the volume of the
				pellet dishing and chamfers. It is calculated as the total mass of the fuel pellets divided by the
				total volume of the fuel
			
				                               (fuel mass)
				stack density =   ----------------------------------------
									pi*(pellet radius)^2 * (fuel height)
			
			The thden refers to the actual theoretical density of the pellet. This quantity is used in fuel
			performance codes to evaluate material properties.
		'''
		
		# So if I understand that all correctly, for the purposes of OpenMC, I only need to 
		# extract the key_name; density; fuel_names; and enrichment.
		#
		# From those, calculate the weight fractions for each isotope, 
		# and add the proper quantity of oxygen to the material.
		#
		# This may be better suited to a Case.__get_fuel() method that just creates a vanilla
		# Material object, instead.

		
		
		# Initialize the 4 material properties
		mname = ""; mdens = 0.0; mfracs = []; miso_names = []
			
		for prop in fuel:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "key_name":
				mname = v
			elif p == "density":
				mdens = float(v)
			elif p == "enrichments":
				# Convert a string to a list of floating point numbers
				mfracs = map(float, v.strip('}').strip('{').split(','))
			elif p == "fuel_names":
				# Convert a string to a list of strings
				miso_names = v.strip('}').strip('{').split(',')			
			elif p == "thden":
				# A studiously ignored property
				continue
			else:
				print "Warning: unused property", p, "in", mname
				self.warnings += 1
				
		
		# Check if isotopic fractions each have an associated element
		if len(mfracs) != len(miso_names):
			warning = "Unequal number of isotopes and associated fractions in material", mname
			#raise IndexError(warning)
			print warning
			self.errors += 1
			
		
		# Instantiate a new material and add it to the dictionary
		a_material = objects.Material(mname, mdens, mfracs, miso_names)
		return a_material
	
	
	def __get_grid(self, grid):
		'''Same as self.__get_material, but for a grid
		
		Inputs:
			grid: The ParameterList object describing a spacer grid
		
		Outputs:
			a_grid: Instance of the SpacerGrid object populated with the properties from the XML.'''
		
		# Initialize the 5 grid properties
		name = grid.attrib["name"]
		height = 0.0; mass = 0.0; label = ""; mat = None
			
		for prop in grid:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "height":
				height = float(v)
			elif p == "mass":
				mass = float(v)
			elif p == "label":
				label = str(v)
			elif p == "material":
				# Check if the material has been defined yet. If not, throw an error
				# This is probably not the desired behavior. Because this way "spacergrid"
				# must necessarily be evaluated after all material/fuel blocks in this case. 
				try:
					mat = self.materials[v]
				except KeyError as e:
					print "**Error: material", e, "has not been defined."
					self.errors += 1
			else:
				print "Warning: unused property", p, "in", name
				self.warnings += 1
		
		
		# Instantiate a new material and add it to the dictionary
		a_grid = objects.SpacerGrid(name, height, mass, label, mat)
		return a_grid
	
	def __get_map(self, cmap):
		'''Same as self.__get_grid, but for a cellmap
		
		Inputs:
			cmap: The ParameterList object describing a cell map
		
		Outputs:
			a_map: Instance of the CellMap object populated with the properties from the XML.'''
		
		# Initialize the 3 cell map properties
		name = cmap.attrib["name"]
		label = ""; map_itself = ()
			
		for prop in cmap:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "cell_map":
				# Convert to a list of integers
				# function name is unrelated
				map_itself = map(int, v.strip('}').strip('{').split(','))
			elif p == "label":
				label = str(v)
			else:
				print "Warning: unused property", p, "in", name
				self.warnings += 1
		
		
		# Instantiate a new material and add it to the dictionary
		a_cell_map = objects.CellMap(name, label, map_itself)
		return a_cell_map
	
	
	def __get_cell(self, cell, asname):
		'''Reads the CELL block
		
		Inputs:
			cell:		The ParameterList object describing a cell
			asname:		Name of the assembly in which the cell exists   
		
		Outputs:
			TBD
		'''
		
		'''Cell cards are used to describe pin cells. A pin cell is defined as a configuration of concentric
		cylinders (or rings) centered in a square region of coolant. Cell configurations can be used to
		model fuel rods or guide tubes. Parameters include cell ID, a list of radii for each ring
		in the cell, and a list of materials that compose each ring.'''
		
		# The plan is to extract the information describing each concentric layer of the
		# pin cells, and then export an object containing that information. In OpenMC/CG,
		# use this information to create several surfaces of concentric cylinders, and to create
		# a universe for the pin cell bounded by the outermost layer and defined by the materials.
		
		# Initialize the relevant variables:
		name = cell.attrib["name"]
		num_rings = 0; radii = []; mats = []; label = "" 

		
		for prop in cell:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "num_rings":
				num_rings = int(v)
			elif p == "radii":
				# Convert to a list of floating point nums
				radii = map(float, v.strip('}').strip('{').split(','))
			elif p == "mats":
				# Convert to a list of strings, which serve as the keys to the dictionary self.materials
				mats = v.strip('}').strip('{').split(',')
				# Check if the materials are defined
				for m in mats:
					try:
						self.materials[m]
					except KeyError:
						print "Error: material", m, "has not been defined yet. (" + asname + ')'
						self.errors += 1
			elif p == "label":
				label = str(v)
			elif p == "type":
				# ignore
				continue
			else:
				print "Warning: unused property", p, "in", name
				self.warnings += 1
		
		# Check if the information was parsed properly
		# If not, warn the user and keep at it
		if len(radii) != num_rings:
			print "Error: there are", num_rings, "rings of", name, "but", len(radii), "radii were found!", '(' + asname + ')'
			self.errors += 1
		if len(mats) != num_rings:
			print "Error: there are", num_rings, "rings of", name, "but", len(mats), "materials were provided!", '(' + asname + ')'
			self.errors += 1
			
			
		a_cell = objects.Cell(name, num_rings, radii, mats, label)
		return a_cell
	
		
	def __str__(self):
		'''Return the name of the VERA input case if I try to print this object'''
		return self.case_id


	def describe(self):
		'''Returns some useful information about this object as a string.'''
		d = "\ncase_id: " + self.case_id
		
		if self.materials:
			d += "\nMaterials:"
			for mat in self.materials.values():
				d += '\n - ' + str(mat)
		else:
			d += "\nNo materials found."

		if self.states:
			d += "\nStates:"
			for stat in self.states:
				d += str(stat)
		else:
			d += "\nNo states found."
		
		if self.assemblies:
			d += "\nAssemblies:"
			for a in self.assemblies.values():
				d += "\n - " + a.name + "\t(" + str(len(a.cells)) + " cells, " + str(len(a.params)) + " parameters)"
		else:
			d += "\nNo assemblies found."
		
		
		if self.errors == 1:
			d += "\n1 error "
		elif self.errors > 1:
			d += "\n" + str(self.errors) + " errors "
		else:
			d += "\nNo errors"
		if self.warnings == 1:
			d += "and 1 warning "
		elif self.warnings > 1:
			d += "and " + str(self.warnings) + " warnings "
		elif self.errors and not self.warnings:
			d += "and no warnings "
		else:
			d += "or warnings "
		d += "found.\n"
		
		
		return d
	
	
	
	def get_openmc_material(self, material):
		'''Given a vera material (objects.Material) as extracted by self.__get_material(),
		create and return an instance of openmc.Material.
		
		This method is  a placeholder for now, as I am still figuring out how to
		use this IDE and haven't imported openmc yet. However, I've tested it with 
		the existing OpenMC code (as of 2016-07-05) and it works as expected!
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
				self.opencg_surface_count += 1
				s = openmc.ZCylinder(surf_id, "transmission", 0, 0, r)
				cell_surfs[surf_id] = s
				# Thought: Currently, this method returns a list of the new surfaces.
				# Would it be better just to add them directly to the registry from within?
				#self.openmc_surfaces[str(surf_id)] = s
				
			# Otherwise, the surface s already exists
			# Proceed to define the cell inside that surface:
			last_id = s
			new_cell = openmc.universe.Cell(cell_id, name)
			new_cell.add_surface(s, -1)
			if ring == 0:
				# Inner ring
				continue
			else:
				# Then this OpenMC cell is outside the previous (last_id), inside the current
				new_cell.add_surface(last_id, 1)
			
			
			
			# The next line is a quick hack for debugging purposes
			fill = self.get_openmc_material(self.materials[vera_cell.mats[ring]])
			# What I want to do instead is, somewhere else in the code, generate the corresponding
			# openmc material for each objects.Material instance. Then, just look it up in that dictionary.			
			new_cell.fill = fill
			openmc_cells.append(new_cell)
		
		# end of "for ring" loop
		universe = self.openmc_universe_count
		self.openmc_universe_count += 1
		return openmc_cells, cell_surfs, universe

				
		
		
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
		universe = self.opencg_universe_count
		self.opencg_universe_count += 1
		return opencg_cells, cell_surfs, universe
	
	
	




	



# Instantiate a case with a simple VERA XML.gold
#filename = "p7.xml.gold"
filename = "2a_dep.xml.gold"
test_case = Case(filename)

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

#mc_test_mat = test_case.get_openmc_material(test_case.materials["pyrex"])
#cg_test_mat = test_case.get_opencg_material(test_case.materials["ss"])
#print mc_test_mat
#print cg_test_mat

#pincell_cells = test_case.get_openmc_pincell(c)[0]
pincell_cells = test_case.get_opencg_pincell(c)[0]
print pincell_cells



