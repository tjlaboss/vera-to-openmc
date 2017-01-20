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
from warnings import warn
from functions import clean, calc_u234_u236_enrichments
import objects
from objects import FUELTEMP, MODTEMP
from openmc.data import atomic_mass


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
		self.usable = ("CORE", "INSERTS", "STATES", "CONTROLS", "DETECTORS", "ASSEMBLIES", "SHIFT") # Relevant to OpenMC
		self.ignore = ("MPACT", "INSILICO", "COBRATF", "EDITS")			# Blocks specific to other codes 
		
		# Initialize some parameters with empty lists
		self.materials = {}
		self.assemblies = {}
		self.inserts = {}
		self.states = []
		self.controls = {};	self.detectors = {}
		
		
		# Placeholder for an essential material
		mod_density = 1.0; mod_isotopes = {"H1":-2.0/3, "O16":-1.0/3}
		self.materials['mod'] = objects.Material("mod", mod_density, mod_isotopes)
		
		# Set the default Monte Carlo simulation parameters (which may be changed later)
		self.mc = objects.MonteCarlo()
		
		# Then populate everything:
		self.errors = 0; self.warnings = 0
		self.__read_xml()
		
		# And now, select a state and use its properties
		#FIXME: Right now, this just selects the first state encountered
		self.state = self.states[0]
		self.materials['mod'] = self.state.mod
		'''
		# Set control rod position
		for bank in self.state.rodbank.keys():
			nsteps = self.state.rodbank[bank]
			print(self.controls)
			crd = self.controls[bank]
			crd.depth = (nsteps/crd.maxstep) * self.core.height 
		'''
		
		#debug
		print(self.inserts, self.controls)
		
		
		# Set all material temperatures based off the STATE block
		for mat in self.materials.values():
			if mat.temperature:
				# Then we know what material temperature to set
				if mat.temperature == FUELTEMP:
					mat.temperature = self.state.tfuel
				elif mat.temperature == MODTEMP:
					mat.temperature = self.state.tinlet
			else:
				mat.temperature = self.state.tinlet
				warnstr = "Material " + mat.name + " does not have a temperature specified; defaulting to tinlet."
				warn(warnstr)
				self.warnings += 1
		
		print("There were", self.warnings, "warnings and", self.errors, "errors.")
		
	
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
					print("Error: child.tag is", child.tag + "; name is",  child.attrib["name"])
					print("The script does not know how to handle this; ignoring.\n")
					self.errors += 1
					
			
			elif child.tag == "ParameterList":
				# Proper use of recursion could probably save me a lot of effort here.
				name = child.attrib["name"].upper()	# for brevity
				if name in self.ignore:
					print("Ignoring block", name)
				elif name in self.usable:
					# Then handle them appropriately
					if name == "CORE":
						'''The [CORE] block describes the nuclear reactor core configuration. This block describes the core
						layout, including the placement of nuclear fuel assemblies, control rods, detectors, inserts, and
						other core parameters that do not change during a cycle depletion.
						The geometric objects inside the core are defined in separate input blocks; the [CORE] block
						simply describes how all of these objects are placed together.'''
						# The CORE block will contain the deck's global materials
						# and some geometric parameters
						core_params = {}
						for core_child in child:
							cname = core_child.attrib["name"].lower()	# for brevity
							if core_child.tag == "ParameterList" and cname == "materials":
								for mat in core_child:
									# Create a material object for each listed material
									new_material = self.__get_material(mat)
									newname = new_material.name
									# Check if a material with this name already exists
									# If it does, keep adding exclamation marks to it until it doesn't,
									# giving a warning each time
									exists = True
									while exists: 
										try:
											old_material = self.materials[newname]
										except KeyError:
											exists = False
											self.materials[newname] = new_material
										else:
											# If the material does exist, check if it is any different
											if new_material != old_material:
												# In the core block, it is an error
													print("Error: a material of the name", new_material.name, "already exists.")
													self.errors += 1
											# Else; it's the same, and do nothing
											exists = False # exit the loop
											
																	
							elif core_child.tag == "ParameterList":
								warn("Unknown parameter list: " + cname + ". Ignoring.")
								self.warnings += 1
								
							elif core_child.tag == "Parameter":
								core_params[cname] = core_child.attrib["value"]
								
							else:
								print("Error: Entry", core_child.tag, "is neither a Parameter nor ParameterList. Ignoring.")
								self.errors += 1
						
						
						# TODO: This is where the program gets boundary conditions and various other core properties.
						# Things to watch for: apitch, assm_map, bc_bot, bc_rad, bc_top, core_size, height,
						# 	rated_flow, rated_power, and shape
						
						# Initialize variables to be passed to the Core instance
						pitch = 0.0; 	asmbly = []; shape = [];
						core_size = 0; 	core_height = 0.0;  
						bcs = {"bot":"vacuum",	"rad":"vacuum",	"top":"vacuum"}
						baffle = {}; lower = {}; upper = {}; lower_refl = None; upper_refl = None
						radii = []; mats = [] 
						insert_cellmap = [];	detector_cellmap = []
						# NOTE: the bank_cellmap can probably be safely removed.
						control_cellmap = [];	control_bank_cellmap = []  
						
						# Unpack these variables from core_params
						# Delete them from the dict, and pass the remaining params on to objects.Core
						for p in core_params:
							v = core_params[p]
							if p == "apitch":
								pitch = float(v)
							elif p == "assm_map":
								asmbly = clean(v, str)
							elif p == "shape":
								shape = clean(v, int)
							elif p == "core_size":
								core_size = int(v)
							elif p == "height":
								core_height = float(v)
							elif p == "insert_map":
								insert_cellmap = clean(v, str)
							elif p == "crd_bank":
								control_bank_cellmap = clean(v, str)
							elif p == "crd_map":
								control_cellmap = clean(v, str)
							elif p == "det_map":
								detector_cellmap = clean(v, str)
			
							elif p[:3] == "bc_":
								bcs[p[3:]] = v
								if len(bcs) < 3:
									# don't delete
									continue
							elif p[:7] == "baffle_":
								b = p[7:] 
								if b == "mat":
									baffle[b] = v
								else:
									baffle[b] = float(v)
								if len(baffle) < 3:
									continue
								elif len(baffle) == 3:
									# Redefine the variable from a dictionary to an object
									baffle = objects.Baffle(baffle["mat"], baffle["thick"], baffle["gap"])
							elif p[:6] == "lower_":
								b = p[6:] 
								if b == "mat":
									lower[b] = v
								else:
									lower[b] = float(v)
								if len(lower) == 3:
									name = "lowerplate"
									lower_mat = objects.Mixture(name = name, 
												materials = (self.materials[lower["mat"]], self.materials["mod"]),
												vfracs = (lower["vfrac"], 1.0 - lower["vfrac"]) )
									self.materials[name] = lower_mat
									lower_refl = objects.Reflector(name, lower["thick"], "lower")
								else:
									continue
							elif p[:6] == "upper_":
								b = p[6:] 
								if b == "mat":
									upper[b] = v
								else:
									upper[b] = float(v)
								if len(upper) == 3:
									name = "upperplate"
									upper_mat = objects.Mixture(name = name, 
												materials = (self.materials[upper["mat"]], self.materials["mod"]),
												vfracs = (upper["vfrac"], 1.0 - upper["vfrac"]) )
									self.materials[name] = upper_mat
									upper_refl = objects.Reflector(name, upper["thick"], "upper")
								else:
									continue
							elif p == "vessel_radii":
								radii = clean(v, float)
							elif p == "vessel_mats":
								mats = clean(v, str)
							else:
								# Don't delete it from the misc params
								continue
							#del core_params[p]
						
						
						# Generate some core maps from the ugly cellmaps
						if insert_cellmap:
							insert_map = objects.CoreMap(insert_cellmap, "Core insertion map")
						else:	insert_map = None
						if control_bank_cellmap:
							control_bank = objects.CoreMap(control_bank_cellmap, "Control rod location map")
						else:	control_bank = None
						if control_cellmap:
							control_map = objects.CoreMap(control_cellmap, "Control rod insertion map")
						else:	control_map = None
						if detector_cellmap:
							detector_map = objects.CoreMap(detector_cellmap, "Detector location map")
						else:	detector_map = None
							
							
						# Check that each pressure vessel radius has a corresponding material
						if len(radii) != len(mats):
							warn("Error: there are " + str(len(radii)) + " core radii, but " + str(len(mats)) + " materials!")
							self.errors += 1
						self.core = objects.Core(pitch, core_size, core_height, shape, asmbly, core_params,
												 bcs, lower_refl, upper_refl, radii, mats, baffle,
												 control_bank, control_map, insert_map, detector_map)
								
						
					elif name == "ASSEMBLIES":
						for asmbly in child:
							cname = asmbly.attrib["name"].lower()	# for brevity
							# dictionary of all independent parameters for this assembly
							asmbly_params = {}
							grids = {}; maps = {}; cells = {}
									
							for asmbly_child in asmbly:
								aname = asmbly_child.attrib["name"].lower()
								if asmbly_child.tag == "Parameter":
									asmbly_params[aname] = asmbly_child.attrib["value"]
								elif asmbly_child.tag == "ParameterList":
									if aname == "cells":
										for cell in asmbly_child:
											new_cell = self.__get_cell(cell, cname)
											cells[new_cell.key] = new_cell
									elif aname == "materials":
										for mat in asmbly_child:
											# Create a material object for each listed material
											new_material = self.__get_material(mat, cname)
											newname = new_material.name
											# Check if a material with this name already exists
											if newname in self.materials:
												print("In self.materials")
												self.materials[newname + cname] = new_material
											else:
												self.materials[newname] = new_material
									elif aname ==  "fuels":
										# More materials are found here
										for fuel in asmbly_child:
											# Create a material object for each listed material
											new_material = self.__get_fuel(fuel)
											newname = new_material.name
											# Check if a material with this name already exists
											# If it does, rename it.
											exists = True
											while exists: 
												try:
													old_material = self.materials[newname]
												except KeyError:
													exists = False
													self.materials[newname] = new_material
												else:
													# If the material does exist, check if it is any different
													if new_material != old_material:
														# In the assembly block, different materials by the same name
														# in different assemblies are possible
														newname = cname + newname
														warn("Warning: different versions of material " + new_material.name + " exist; renaming to " + newname)
														new_material.name = newname
													else:
														# Exit the loop
														exists = False
													
									elif aname == "cellmaps":
										for cmap in asmbly_child:
											new_map = self.__get_map(cmap)
											maps[new_map.label] = new_map
									elif aname ==  "spacergrids":
										for grid in asmbly_child:
											new_grid = self.__get_grid(grid)
											grids[new_grid.label] = new_grid
												
									
									else:
										warn("Unknown ASSEMBLIES.ParameterList" + aname + "-- ignoring")
										self.warnings += 1
								
								else:
									print("Error: Entry", asmbly_child.tag, "is neither a Parameter nor ParameterList. Ignoring for now.")
									self.errors += 1
									
							
							# Instantiate an Assembly object and pass it the parameters
							new_assembly = objects.Assembly(name = cname, cells = cells, cellmaps = maps, spacergrids = grids, params = asmbly_params)
							self.assemblies[new_assembly.label] = new_assembly
						
						
					elif name == "STATES":
						# For different states: read all of them and create
						# a description of each. Generate a geometry for each
						# of them, or ask the user which one he wants?
						
						for stat in child:
							new_state = self.__get_state(stat)
							self.states.append(new_state)
					
					
					elif name == "SHIFT":
						particles = 0; cycles = 0; inactive = 0
						for prop in child:
							pname = prop.attrib["name"].lower()
							if prop.tag == "ParameterList" and pname == "kcode_db":
								for mcparam in prop:
									p = mcparam.attrib["name"].lower()
									v = mcparam.attrib["value"]
									if p == "np":
										particles = int(v)
									elif p == "num_cycles":
										cycles = int(v)
									elif p == "num_inactive_cycles":
										inactive = int(v)
									else:
										warnstr = "Warning: unknown Parameter " + p + " in ParameterList " + pname
										warn(warnstr)
										self.warnings += 1
							elif prop.tag == "ParameterList":
								warnstr = "Warning: unknown ParameterList " + pname + " in [SHIFT] block."
								warn(warnstr)
								self.warnings += 1
									
						self.mc = objects.MonteCarlo(cycles, inactive, particles)
					
							
					elif name == "INSERTS":
						for insert in child:
							new_insert = self.__get_insert(insert)
							self.inserts[new_insert.key] = new_insert
							print(new_insert)#debug
					elif name == "CONTROLS":
						for insert in child:
							new_insert = self.__get_insert(insert, is_control = True)
							self.controls[new_insert.key] = new_insert
							print(new_insert)#debug
					elif name == "DETECTORS":
						for insert in child:
							new_insert = self.__get_insert(insert)
							self.detectors[new_insert.key] = new_insert
							print(new_insert)#debug
					else:
						warn("Unexpected ParameterList " + name + " encountered; ignoring.")
				
				else:
					w = ("Unexpected block encountered:\t" + child.attrib["name"] + \
						"\nThis may be a flaw within the XML file, or a shortcoming of this script. Ignoring for now.")
					warn(w)
					self.warnings += 1
			
			else:
				print("Error: child.tag =", child.tag, "-- Ignoring.\n", \
				"Expected either Parameter or ParameterList. There is probably something wrong with the XMl.")
				self.errors += 1
		
		# note; end of the giant for loop
	
	
	def __get_material(self, mat, asname = ""):
		'''When a material or fuel block is encountered in the XML,
		extract the useful information.
		
		Inputs:Pass on the assembly Parameters to the instance
			mat: 	The ParameterList object describing a VERA material
			asname:	Assembly or Insert name in which the material is defined.
					Cells made will check for materials suffixed with this first.
		
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
				mfracs = clean(v, float)
			elif p == "mat_names":
				# Convert a string to a list of strings
				miso_names = clean(v.replace("-", "").title(), str)
			else:
				warn("Warning: unused property " + p)
				self.warnings += 1
		
		# Check if isotopic fractions each have an associated element
		if len(mfracs) != len(miso_names):
			warn("Unequal number of isotopes and associated fractions in material " + mname)
			self.warnings += 1
		
		# Turn isotope names and fractions into a dictionary
		isos = {}
		for i in range(len(miso_names)):
			isos[miso_names[i]] = mfracs[i]
		
		# Instantiate a new material return it
		a_material = objects.Material(mname + asname, mdens, isos, MODTEMP)
		return a_material
	
	
	
	def __get_fuel(self, fuel, asname = ""):
		'''When a fuel block is encountered in the XML, extract the useful information
		and do the math to create a Material instance.
		
		Inputs:
			fuel: 	The ParameterList object describing a VERA fuel
			asname:	The assembly in which this fuel appears
		
		Outputs:
			a_material: Instance of the Material object. Should be indistinguishable from
						one generated by self.__get_material().'''
		
		
		
		# Initialize the 6 material properties
		mname = ""; mdens = 0.0; mfracs = []; miso_names = []
		gad_name = ""; gad_frac = 0.0
			
		for prop in fuel:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "key_name":
				mname = v
			elif p == "density":
				mdens = float(v)
			elif p == "enrichments":
				# Convert a string to a list of floating point numbers
				mfracs = clean(v, float)
			elif p == "fuel_names":
				# Convert a string to a list of strings
				miso_names = clean(v.replace("-", "").title(), str)			
			elif p == "thden":
				# A studiously ignored property
				continue
			elif p == "gad_frac":
				gad_frac = float(v)/100.0  # wt fractions are given as percents
			elif p == "gad_mat":
				gad_name = v
			else:
				warn("Warning: unused property " + p + "in" + mname)
				self.warnings += 1
		
		# Check if isotopic fractions each have an associated element
		if len(mfracs) != len(miso_names):
			warn("Error: Unequal number of isotopes and associated fractions in material " + mname)
			#raise IndexError(warning)
			self.errors += 1
		# Turn isotope names and fractions into a dictionary
		isos = {}
		for i in range(len(miso_names)):
			iname = miso_names[i].replace("-", "").title()
			isos[iname] = mfracs[i]/100.0
		
		# Do NOT use miso_names/mfracs after this point!	
		
		# Complete the material composition (done implicitly in VERA)
		if (miso_names[0][0].title() == 'U') or (miso_names[0][:1] == '92'):
			# Uranium
			# Add U-234 and U-236 to the composition, according to the formulas in the VERA manual,
			# if the user has not specified them himself
			u234, u236 = calc_u234_u236_enrichments(isos['U235'])
			if 'U236' not in isos:
				isos['U236'] = u236
			if 'U234' not in isos:
				isos['U234'] = u234
			# Add U-238 to composition
			isos['U238'] = ( 1 - sum(isos.values()) )
		# With other HMs, the complete composition is already specified in the VERA deck
		
		# Calculate the weight of the HMs, add the weight of oxygen and gadolinia, and normalize
		mass = 0.0
		for i in isos:
			isomass = atomic_mass(i)
			mass += isos[i]*isomass
		# Add Oxygen: (HM)-O2
		oname = 'O16'
		omass = atomic_mass(oname)*2.0
		ofrac = omass/mass  # Non-normalized; use: ( omass/(mass + omass) ) to pre-normalize oxygen
		mass += omass
		isos[oname] = ofrac
		# And normalize
		total_wt = sum(isos.values())
		for i in isos:
			isos[i] = isos[i] * (1.0 - gad_frac) / total_wt
		
		# Then, add the gadolinia if necessary
		if gad_frac:
			try:
				gad_mat = self.materials[gad_name]
			except KeyError:
				warn("Error: gad_mat " + gad_name + "is specified, but does not seem to exist.")
				self.errors += 1
			else:
				# Normalize the gadolinia and mix it into the fuel
				for i in gad_mat.isotopes:
					if i in isos:
						# Then the isotope is already in the mixture; add to it
						isos[i] += gad_frac*gad_mat.isotopes[i]
					else:
						# Then the material doesn't exist; make a new entry
						isos[i] = gad_frac*gad_mat.isotopes[i]
		
		
		# Instantiate a new material and add it to the dictionary
		a_material = objects.Material(mname + asname, mdens, isos, FUELTEMP)
		return a_material
	
	
	def __get_state(self, state):
		'''Similar to the other __get_thing() methods
		
		Input:
			state:		The ParameterList object describing an operating state
		Output:
			a_state:	instance of objects.State
		'''
		key = state.attrib["name"].lower()
		
		# Initialize variables
		name = ""
		tinlet = 0.0;	tfuel = 0.0;
		b10 = 0.184309	# wt fraction
		density = 0.0
		bank_labels = (); bank_pos = ()
		for prop in state:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			state_params = {}
			'''Parameters to look for:
				title,
				tinlet,			(mod/clad temperature, C)
				tfuel,			(fuel temperature, K)
				boron, 			(boron concentration, ppm) 
				b10,			(boron 10 atom percent; default is 19.9)
				modden			(moderator density, g/cc)
			...and more...
			'''
			
			if p == "title":
				name = v
			elif p == "tinlet":
				tinlet = float(v) + 273.15
			elif p == "tfuel":
				tfuel = float(v)
			elif p == "boron":
				bfrac = float(v)/10**6
			elif p == "b10":
				b10 = float(v)/100
			#elif p == "b10_depl":
			elif p == "modden":
				density = float(v)
			elif p == "bank_labels":
				bank_labels = clean(v, str)
			elif p == "bank_pos":
				bank_pos = clean(v, int)
			else:
				state_params[p] = v
		
		# Define the rodbank dictionary using 'bank_labels' as keys and 'bank_pos' as values
		rodbank = dict(zip(bank_labels, bank_pos))
		
		# Calculate the actual boron composition, and create
		# a new VERA material for it.
		# The following are WEIGHT fractions
		
		h2ofrac = 1.0 - bfrac
		b10frac = b10*bfrac
		b11frac = (1.0-b10)*bfrac
		hmass = atomic_mass('H1')*2
		omass = atomic_mass('O16')
		mod_isos = {"B10" : b10frac,
					"B11" : b11frac,
					"H1"  : h2ofrac * hmass/(hmass + omass),
					"O16" : h2ofrac * omass/(hmass + omass)}
		mod = objects.Material("mod", density, mod_isos, tinlet)
		
		# Instantiate and return the State object
		a_state = objects.State(key, tfuel, tinlet, mod, name, 
								rodbank, state_params)
		return a_state
	
	
	def __get_insert(self, insert, is_control = False):
		'''Similar to the other __get_thing() methods
		
		Inputs:
			insert:			The ParameterList object describing an assembly insert
			is_control:		Whether to instantiate this as a Control object.
		Output:
			an_insert:		instance of objects.Insert
		'''
		in_name = insert.attrib["name"].lower()
		# dictionary of all independent parameters for this assembly
		key = in_name; title = in_name
		cellmaps = {};		cells = {}
		axial_elevs = ();	axial_labels = ()
		npins = 0
		max_step = 0;		stroke = 0.0			
		insert_params = {}
		for prop in insert:
			p = prop.attrib["name"]
			if prop.tag == "Parameter":
				v = prop.attrib["value"]
				if p == "axial_elevations":
					axial_elevs = clean(v, float)
				elif p == "axial_labels":
					axial_labels = clean(v, str)
				elif p == "num_pins":
					npins = int(v)
				elif p == "label":
					key = v
				elif p == "title":
					title += "-" + str(v)
				elif p == "maxstep":
					max_step = int(v)
				elif p == "stroke":
					stroke = float(v)
				else:
					insert_params[p] = v
					
			elif prop.tag == "ParameterList":
				if p == "Cells":
					for cell in prop:
						new_cell = self.__get_cell(cell, in_name)
						cells[new_cell.key] = new_cell
				elif p == "CellMaps":
					for cellmap in prop:
						new_cellmap = self.__get_map(cellmap)
						cellmaps[new_cellmap.label] = new_cellmap
				elif p == "Materials":
					for mat in prop:
						new_material = self.__get_material(mat, asname = in_name)
						self.materials[new_material.name] = new_material
				else:
					errstr = "Error: Unexpected ParameterList " + p
					warn(errstr)
					self.errors += 1
					
			else:
				errstr = "Error: Unknown data structure " + p
				warn(errstr)
				self.errors += 1
		
				
		if is_control:
			an_insert = objects.Control(key, title, npins, cells, cellmaps, axial_elevs, axial_labels,
										insert_params, stroke, max_step)
		else:
			an_insert = objects.Insert(key, title, npins, cells, cellmaps, axial_elevs, axial_labels,
										insert_params)
		return an_insert
			
	
	
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
				mat = str(v)
			else:
				warn("Warning: unused property " + p + "in" + name)
				self.warnings += 1
		
		# Instantiate a new material and add it to the dictionary
		a_grid = objects.SpacerGrid(name, height, mass, label, mat)
		return a_grid
	
	def __get_map(self, cmap):
		'''Same as self.__get_grid, but for a cellmap
		
		Inputs:
			cmap: The ParameterList object describing a cell map
		
		Outputs:
			a_map: Instance of the CoreMap object populated with the properties from the XML.'''
		
		# Initialize the 3 cell map properties
		name = cmap.attrib["name"]
		label = ""; map_itself = ()
			
		for prop in cmap:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "cell_map":
				# Convert to a list of strings
				map_itself = clean(v, str)
			elif p == "label":
				label = str(v)
			else:
				warn("Warning: unused property " + p + "in" + name)
				self.warnings += 1
		
		
		# Instantiate a new material and add it to the dictionary
		a_cell_map = objects.CoreMap(map_itself, name, label)
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
		name = cell.attrib["name"] + '-' + asname
		num_rings = 0; radii = []; mats = []; label = "" 

		
		for prop in cell:
			p = prop.attrib["name"]
			v = prop.attrib["value"]
			if p == "num_rings":
				num_rings = int(v)
			elif p == "radii":
				# Convert to a list of floating point nums
				radii = clean(v, float)
			elif p == "mats":
				# Convert to a list of strings, which serve as the keys to the dictionary self.materials
				mats = clean(v, str)
			elif p == "label":
				label = str(v)
			elif p == "type":
				# ignore
				continue
			else:
				warn("Warning: unused property " + p + " in " + name)
				self.warnings += 1
		
		# Check if the information was parsed properly
		# If not, warn the user and keep at it
		if len(radii) != num_rings:
			print("Error: there are", num_rings, "rings of", name, "but", len(radii), "radii were found!", '(' + asname + ')')
			self.errors += 1
		if len(mats) != num_rings:
			print("Error: there are", num_rings, "rings of", name, "but", len(mats), "materials were provided!", '(' + asname + ')')
			self.errors += 1
			
			
		a_cell = objects.Cell(name, num_rings, radii, mats, label, asname)
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
	
	
	
	






