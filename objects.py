# objects.py
#
# Module containing useful objects for read_xml.py

from math import sqrt
from functions import *
from openmc.data import atomic_mass
from copy import copy

FUELTEMP = -1; MODTEMP = -2

class Material(object):
	'''Basics of a material card
	Parameters:
		name:			string; unique material name
		density:		float; density in g/cm^3
		isotopes:		dictionary of {"isotope name":isotope_fraction}
		temperature:	float; temperature of the material in Kelvins [optional]
						-1 indicates fuel temperature; -2 indicates moderator temperature.
						0 is unknown. Positive values are real temperatures.  
	'''
	def __init__(self, key_name, density, isotopes, temperature = 0):
		self.name = key_name
		self.density = density
		self.isotopes = isotopes
		self.temperature = temperature

	def __str__(self):
		'''Use this to print a brief description of each material'''
		description = self.name + '\t@ ' + str(self.density) + ' g/cc\t(' + str(len(self.isotopes)) + ' isotopes)'
		return description
	
	def __eq__(self, other):
		return self.__dict__ == other.__dict__
	
	
	def convert_at_to_wt(self):
		'''Convert atomic fraction to weight fraction for this material's isotopes'''
		total_at = sum(self.isotopes.values())
		total_wt = 0.0
		iso_wts = {}
	
		if total_at >= 0:
			# already in weight fraction
			return
		else:
			for iso in self.isotopes:
				total_wt += self.isotopes[iso] * atomic_mass(iso)
			for iso in self.isotopes:
				iso_wts[iso] = abs( self.isotopes[iso] * atomic_mass(iso) / total_wt )
		
			self.isotopes = iso_wts
	

	def convert_wt_to_at(self):
		'''Convert weight fraction to atomic fraction for this material's isotopes'''
		total_at = 0.0
		total_wt = sum(self.isotopes.values())
		iso_ats = {}
	
		if total_wt <= 0:
			# already in atomic fraction
			return 
		else:
			for iso in self.isotopes:
				total_at += self.isotopes[iso] / atomic_mass(iso)
			for iso in self.isotopes:
				iso_ats[iso] = -abs( self.isotopes[iso] / atomic_mass(iso) / total_at )
		
			self.isotopes = iso_ats



class Mixture(Material):
	'''Two mixed Material instances. 
	Functionally exactly the same as Material, but initialized differently.'''
	def __init__(self, name, materials, vfracs, temperature = 0):
		self.name = name
		mix_isos = {}
		density = 0.0
	
		for i in range(len(materials)):
			density += materials[i].density * (vfracs[i] / sum(vfracs))
		for i in range(len(materials)):
			mat = materials[i]
			mat.convert_at_to_wt()
			wtf = vfracs[i]*mat.density 	# weight fraction of entire material
			for iso in mat.isotopes:
				new_wt = wtf*mat.isotopes[iso] / density
				if iso in mix_isos:
					mix_isos[iso] += new_wt
				else:
					mix_isos[iso] = new_wt
					
		self.isotopes = mix_isos
		self.density = density
		self.temperature = temperature


class State(object):
	'''The [STATE] block defines the state of the core (power, flow, pressure, inlet temperature, rod
	positions, boron concentration, etc.) at a particular point in time. These values will typically
	change during a cycle depletion.
	
	Required Parameters:
		key:		str; unique name of the state
		tfuel:		float; fuel temperature (K)
		tinlet:		float; coolant inlet temperature (K)
		## boron:		float; boron concentration in ppm
		mod:		instance of Material describing the moderator
	Optional:
		##b10:		atom fraction of boron which is b-10
		##			[Default: 0.199]
		name:		str; descriptive title of the state
					[Default: empty string]
		rodbank:	dictionary of control rod banks in the format { crd_key : crd_position }
		params:		catch-all dictionary for the raw parameters from the deck
		 
	'''
	def __init__(self, key, tfuel, tinlet, mod,
					#boron, b10 = 0.199,
					name = "", rodbank = {}, params = {},):
		self.key = key
		self.tfuel = tfuel
		self.tinlet = tinlet
		self.mod = mod
		
		self.rodbank = rodbank
		self.params = params


class MonteCarlo(object):
	'''Container for all the Monte Carlo simulation parameters
	
	Inputs:
		min_batches:		int; minimum number of batches to simulate
							[Default: 275]
		inactive:			int; number of batches to ignore in criticality calculation
							[Default: 75]
		particles:			int; number of particles per batch to simulate
							[Default: 200000]
		max_batch_mult:		float; factor * min_batches. Used to cut off a simulation that is
							looking for a certain tally to be hit. Usually, this parameter is
							not important and can be safely ignored.
							[Default: 10]
	
	Other attributes:
		max_batches:		int; min_batches*max_batch_mult
	'''
	def __init__(self, min_batches = 275, inactive = 75, particles = 200000, max_batch_mult = 10):
		self.min_batches = min_batches
		self.max_batches = int(max_batch_mult*min_batches)
		self.inactive = inactive
		self.particles = particles
	
	def __str__(self):
		d = "Monte Carlo Simulation Parameters:"
		d += "\n\tMin. batches:\t" + str(self.min_batches)
		d += "\n\tMax. batches:\t" + str(self.max_batches)
		d += "\n\tInactive cycles:\t" + str(self.inactive)
		d += "\n\tParticles/cycle:\t" + str(self.particles)
		return d



class Assembly(object):
	'''VERA decks often contain descriptions of fuel assemblies.
	Although I am not sure how to represent these in OpenMC/OpenCG yet,
	it is useful to store assemblies as objects owned by a Case instance.
	
	Inputs:
		name: 			String containing the unique Assembly name
		cells:			Dictionary of Cell objects in this assembly {cell.key:cell}
		params:			Dictionary of all the other parameters provided
						in the Assembly block
		cellmaps: 		Dictionary of CellMap objects containing the original cell maps
		spacergrids:	Dictionary of SpacerGrid objects
	Other attributes:
		key_maps:		Dictionary of CellMap objects containing the unique Cell keys
		pwr_nozzles:	Dictionary of pwr.Nozzle instances which have been created for this
		pwr_spacers: 	Dictionary of pwr.SpacerGrid instances which have been created for this
	'''
	
	def __init__(self, name, cells, params = {}, cellmaps = {}, spacergrids = {}): # more inputs to come
		self.name = name
		self.cells = cells
		self.cellmaps = cellmaps
		self.spacergrids = spacergrids
		
		self.params = params
		# Unpack the parameters that should appear in every case
		self.label = params["label"].lower()
		self.axial_labels = clean(params["axial_labels"], str)
		self.axial_elevations = clean(params["axial_elevations"], float)
		self.pitch = float(params["ppitch"])
		self.npins = int(params["num_pins"])
		
		self.pwr_spacers = {}
		self.pwr_nozzles = {}
		
		self.construct_maps()
		
		
	def construct_maps(self):
		"""Construct the cell dictionary and key map"""
		self.celldict = {}
		for cell in self.cells.values():
			self.celldict[cell.label] = cell.key
		
		self.key_maps = {}
		for cmap in self.cellmaps:
			self.cellmaps[cmap] = CoreMap(self.cellmaps[cmap], name = self.name+'-'+cmap, label = cmap)
			self.key_maps[cmap] = CoreMap(fill_lattice(self.cellmaps[cmap], self.lookup, self.npins), \
										name=self.name+"-"+cmap + " (keymap)", label = cmap)
		
		
	def __str__(self):
		rep = self.key
		rep += ": "
		rep += self.name
		return rep
	
	
	def lookup(self, c, blank = "-"):
		if c != blank:
			'''
			# NASTY HACK, NEED TO REMOVE
			if c in self.celldict:
				return self.celldict[c]
			else:
				return self.cells[c].key
				'''
			return self.celldict[c]
		else:
			return blank
	
	
	def add_insert(self, insertion, depth = 0.0):
		"""Merge levels
		
		Inputs:
			insertion:		instance of Insert
			depth:			for partially withdrawn Inserts (such control rods),
							the depth at which the Insert begins.
							[Default: 0]
		"""
		
		
		# First of all, ignore insertions in the nozzle region
		# TODO: At a later date, figure out if it is important to model them.
		# If so, a "nozzle lattice" can be created to handle this.
		
		# TODO: This method needs to account for the depth of insertion, for control rods.
		# The control rod insertion is given in the [STATE] block.
		na_levels = len(self.axial_elevations) 
		ni_levels = len(insertion.axial_elevations)
		if depth:
			# Truncate at the top of the assembly
			max_elev = max(insertion.axial_elevations + insertion.axial_elevations)
			insert_elevations = []
			insert_labels = insertion.axial_labels[0:1]
			for i in range(ni_levels):
				z = insertion.axial_elevations[i] + depth
				if z < max_elev:
					insert_elevations.append(z)
					insert_labels.append(insertion.axial_labels[i+1])
				else:
					break
			ni_levels = len(insert_elevations)	
			#next two lines are debug
			print("Before:", insertion.axial_elevations, insertion.axial_labels)
			print("After:", insert_elevations, insert_labels)
		else:
			insert_elevations = insertion.axial_elevations
			insert_labels = insertion.axial_labels
		
		
		# Merge and remove the duplicates
		all_elevs = list(set(self.axial_elevations + insert_elevations))
		all_elevs.sort()
		all_labels = [None,]*(len(all_elevs) - 1)
		all_key_maps = dict(self.key_maps)
		
		for kk in range(len(all_labels)):
			z = all_elevs[kk+1]
			a_label = None
			i_label = None
			# See where we are
			for k in range(na_levels-1):
				if (z >= max(self.axial_elevations)) or (z <= self.axial_elevations[k+1] and z > self.axial_elevations[k]):
					a_label = self.axial_labels[k]
					akeymap = self.key_maps[a_label]
					break
				elif z == min(self.axial_elevations):
					a_label = self.axial_labels[0]
					akeymap = self.key_maps[a_label]
					break
				
			for k in range(ni_levels-1):
				if (z == max(insert_elevations)) or (z <= insert_elevations[k+1] and z > insert_elevations[k]):
					i_label = insert_labels[k]
					ikeymap = insertion.key_maps[i_label]
					break
			# Now we know the label of this level in self (assembly) and insertion
			if a_label and i_label:
				# Then we've got an insertion acting here.
				new_label = a_label + '+' + i_label
				new_lattice = replace_lattice(new_keys = ikeymap, original = akeymap)
				new_map = CoreMap(new_lattice, name = new_label + " (keymap)", label = new_label)
			elif a_label:
				# No insertion
				new_lattice = self.key_maps[a_label]
				new_map = CoreMap(new_lattice, name = a_label + " (keymap)", label = a_label)
			else:
				print("z:", z, "\ta_label:", a_label, "\ti_label:", i_label)
				errstr = "Something went wrong. There should be an Assembly level here, but there isn't.\n"
				errstr += "z = " + str(z) + "\ta_label = " + a_label + "\ti_label = " + i_label
				raise IndexError(errstr)
				
			all_labels[kk] = new_map.label
			all_key_maps[new_map.label] = new_map
		
		self.axial_elevations = all_elevs
		self.axial_labels = all_labels
		self.cells.update(insertion.cells)
		self.key_maps.update(all_key_maps)
		
		
		
	def get_cell_insert(self, insertion, imap, amap, i, j, blank = "-"):
		'''For a cell within a lattice, check if an insertion goes here.
		If so, see if it exists. If it does, look it up in self.cells.
		If it doesn't, make a copy of the original and modify it with
		cell.insert(the insertion cell). Return the key of whichever cell
		belongs at this position.
		
		Input:
			insertion:		Insert instance
			amap:			CoreMap instance of the assembly pre-insertion
			imap:			CoreMap instance of the insertion locations
			i,j:			int; indices marking the location in imap and amap
			new_label:		str; what to call the new cell+insert --> this may be unnecessary
		Output:
			akey:			If there is no insertion here, the original amap[i][j]
			new_key			If there is an insertion here, key of the new cell
		'''
		
		akey = amap[i][j]		# key of the original pin cell
		ikey = imap[i][j]		# key of the Insert cell
		
		
		if ikey == blank:
			return akey
		else:
			acell_key = self.lookup(akey)
			icell_key = insertion.celldict[ikey]
			new_key = acell_key + "+" + icell_key
			if new_key not in self.cells:
				cell_w_insert = copy(self.cells[acell_key])
				cell_w_insert.insert(insertion.cells[icell_key])
				cell_w_insert.key = new_key
				self.cells[new_key] = cell_w_insert
			return new_key
		
		

class Insert(Assembly):
	'''Container for information about an assembly insertion
	
	An insert_map (attribute of class Core) is used to show where assembly
	inserts are located within the core; for example, burnable poison assemblies
	with different numbers of pyrex rods. It can also be used to place objects
	such as thimble plugs. The description of such inserts is given
	in the VERA input deck under the [INSERT] block
	
	Inputs:
		key:			str; unique identifier of this insert
		name:			str; more descriptive name of this insert
						[Default: empty string]
		npins:			int; number of pins across the assembly this insert is to be placed in.
						Must be equal to assembly.npins.
						[Default: 0]
		cells:			dictionary of instances of Cell 	{cell.key:Cell}
		cellmaps:		dictionary of instances of Cellmap 	{???:Cellmap}
		axial_elevs:	list of floats describing the axial elevations of the lattice layers
	'''
	
	def __init__(self, key, name = "", npins = 0,
				 cells = [], cellmaps = {}, axial_elevs = [], axial_labels = [],
				 params = {}):
		
		
		if axial_elevs or axial_labels:
			assert (len(axial_elevs) == len(axial_labels)+1), \
				"The number of axial elevations must be exactly one more than the number of axial labels."
		
		self.key = key
		self.name = name
		self.npins = npins
		self.cells = cells
		self.cellmaps = cellmaps
		self.axial_elevations = axial_elevs
		self.axial_labels = axial_labels
		self.params = params
		
		self.construct_maps()


class Control(Insert):
	"""Container for information about control rods.
	
	An insert_map (attribute of class Core) is used to show where assembly
	inserts are located within the core; for example, burnable poison assemblies
	with different numbers of pyrex rods. It can also be used to place objects
	such as thimble plugs. The description of such inserts is given
	in the VERA input deck under the [INSERT] block
	
	Inputs:
		key:			str; unique identifier of this insert
		name:			str; more descriptive name of this insert
						[Default: empty string]
		npins:			int; number of pins across the assembly this insert is to be placed in.
						Must be equal to assembly.npins.
						[Default: 0]
		cells:			dictionary of instances of Cell 	{cell.key:Cell}
		cellmaps:		dictionary of instances of Cellmap 	{???:Cellmap}
		axial_elevs:	list of floats describing the axial elevations of the lattice layers
		stroke:			float; Control rod stroke. Distance (cm) between
						full-insertion and full-withdrawal
						[Default: 0]
		maxstep:		int; Total number of steps between full-insertion and full-withdrawal
						Default: 0]
		
	Other attributes:
		step_size:		stroke/maxstep
	"""
		
	def __init__(self, key, name = "", npins = 0,
				 cells = [], cellmaps = {}, axial_elevs = [], axial_labels = [],
				 params = {}, stroke = 0.0, maxstep = 0, depth = 0.0):
	
	
		super().__init__(key, name, npins, cells, cellmaps, axial_elevs, axial_labels, params)
		self.stroke = stroke
		self.maxstep = maxstep
		self.step_size = stroke/float(maxstep)
	


class SpacerGrid(object):
	'''Object to hold properties of an assembly's spacer grids
	
	Inputs:
		name: 		String containing the name, which serves as a dictionary key in Case.grids
		height:		float
		mass:		float
		label:		string
		material:	string; key referring to an instance of class Material
		'''
	
	def __init__(self, name, height, mass, label, material):
		self.name = name		
		self.height = height	
		self.mass = mass		
		self.label = label		
		self.material = material
		self.thickness = 0	# to be set later
		
	def __str__(self):
		return self.name
		
		

class CoreMap(object):
	"""A core mapping for assembly, control rod, and detector positions
	Inputs: 
		cell_map: 	List of integers or strings describing the assembly layout
					You can also give it a square_map, and it will process it appropriately
		name: 		String containing the descriptive Assembly name
					[Default: empty string]
		label:		string containing the unique Assembly identifier
					[Default: empty string]	
	"""
	def __init__(self, cell_map, name = "", label = ""):
		self.name = name 
		self.label = label
		if isinstance(cell_map[0], list):
			# If you feed it a square map:
			self.cell_map = []
			for row in cell_map:
				self.cell_map += row
		else:
			self.cell_map = cell_map
	
	def __str__(self):
		rep = self.name
		rep += ":\n"
		rep += self.str_map()
		return rep
	
	def __len__(self):
		return len(self.square_map())
	
	def __iter__(self):
		for i in self.square_map():
			yield i
	
	def __getitem__(self,i):
		return self.square_map()[i]

	#def __setitem__(self,index,value):
	#	self.square_map()[index] = value
	
	
	def square_map(self):
		'''Return the cell map as a square array'''
		n = int(sqrt(len(self.cell_map)))
		smap = [['',]*n, ]*n
		for row in range(n):
			smap[row] = self.cell_map[row*n:(row+1)*n]
		return smap
	
	def str_map(self):
		'''Return a string of the square map nicely.'''
		smap = self.square_map()
		ml = len( max(map(str, self.cell_map), key=len) )	#max length of a key
		printable = ""
		for row in smap:
			for col in row:
				printable += str(col).rjust(ml) + ' '
			printable += '\n'
		return printable


class Cell(object):
	'''
	Inputs: 
		name: 		String containing the full Cell name
		num_rings:	Number of concentric rings of different materials
		radii:		List of length {num_rings} containing the lengths of the respective rings
		mats:		List of length {num_rings} referencing Material objects of the respective rings
		label:		string containing the unique identifier of the cell
		asname:		string containing the name of the VERA assembly or insert the cell is in (optional)
	
	Other Attributes
		inname:		string containing the name of the VERA insert (INSERT, DETECTOR, or CONTROL)
					that has been inserted into this cell.
	'''
	
	
	def __init__(self, name, num_rings, radii, mats, label, asname = ""):
		self.name = name
		self.num_rings = num_rings
		self.radii = radii
		self.mats = mats
		self.label = label
		self.asname = asname
		
		self.inname = ""
		self.key = name
	
	def __str__(self):
		rep = self.key + " (radius = " + str(max(self.radii)) + ')'
		return rep
	
	
	def insert(self, insert_cell):
		'''I heard you like cells, so I put a cell in your cell.
		This method allows the insertion of 'insert_cell' into the innermost
		radius of self. 
		
		Input:
			insert_cell:		instance of Cell (same as self)
		'''
		
		assert isinstance(insert_cell, Cell), "'insert_cell' must be a VERA pin cell (objects.Cell)."
		assert (insert_cell.radii[-1] <= self.radii[0]), \
			"The outer radius of the insertion must be less than the innermost radius of the guide tube."
		
		self.radii = insert_cell.radii + self.radii
		self.mats = insert_cell.mats + self.mats
		self.num_rings += len(insert_cell.radii)
		self.name += "+" + insert_cell.asname
		self.inname = insert_cell.asname
		


class Core(object):
	'''Container for all the general and full-core properties
	
	Inputs:
		pitch:		float; 	assembly pitch in cm
		size:		int; 	number of assemblies across one axis of the full core
		height:		float;	total axial distance (cm) from the bottom core plate
					to the top core plate, excluding plate thickness
		shape_map:	list or CoreMap of integers containing a map of the shape of the core.
					If a list is given, it will be transformed into a CoreMap.
					A 1 marks a valid assembly location; a 0, an invalid location
		asmbly:		list of strings containing a map of the fuel assemblies in the core, 
					which may be specified or converted as above. **Must conform to self.shape**
		params:		dictionary of miscellaneous core parameters for possible later use
	
	Optional parameters:			
		bc:				dictionary of boundary conditions for top, bot, and rad.
						May be either "reflecting" or "vacuum". (Default: "vacuum")
		bot_refl:		instance of Reflector(mat, thick, vfrac) 
		top_refl:	 	  ^
		vessel_radii:	list of floats describing the radii of the reactor vessel layers
		vessel_mats:	list of strings referring to Material keys for each layer of the
						reactor vessel--must be same length as vessel_radii
		baffle:			instance of class Baffle
		control_bank,	\
		control_map,	 instance of CoreMap 
		insert_map,		 /
		detector_map:	/
	'''

	def __init__(self, pitch, size, height, shape, asmbly, params, #rpower, rflow,
				 bc = {"bot":"vacuum",	"rad":"vacuum",	"top":"vacuum"},
				 bot_refl = None, top_refl = None, vessel_radii = [], vessel_mats = [], 
				 baffle = {}, control_bank = [], control_map = [], insert_map = [], detector_map = []):
		
		self.pitch = pitch
		self.size = size
		self.height = height
		self.asmbly = asmbly
		self.params = params
		
		if not isinstance(shape, CoreMap):
			self.shape = CoreMap(shape, "Core shape map")
		else:
			self.shape = shape
		if not isinstance(asmbly, CoreMap):
			self.asmbly = CoreMap(asmbly, "Fuel assembly map")
		else:
			self.asmbly = asmbly
		#if not isinstance(control, class_or_tuple)
		
		self.bc = {}
		# Correct for OpenMC syntax
		for key in bc:
			if bc[key].lower() == "reflecting":
				self.bc[key] = "reflective"
			else:
				self.bc[key.lower()] = bc[key].lower()
		
		
		self.bot_refl = bot_refl
		self.top_refl = top_refl
		self.vessel_mats = vessel_mats
		self.vessel_radii = vessel_radii
		self.baffle = baffle
		self.control_bank = control_bank
		self.control_map = control_map
		self.insert_map = insert_map
		self.detector_map = detector_map
	
	
	def __str__(self):
		if self.vessel_radii and self.height:
			c = str(max(self.vessel_radii))
			h = str(self.height)
			return "Core: r=" + c + "cm, z=" + h + "cm"
		else:
			return "Core"
	
	
	def __asmbly_square_map(self, space = ' '):
		'''Returns array of the assembly map
		
		Optional input:
			space:	string (len=0 or 1) to represent a spot outside the core.
					Default is whitespace.'''
		if space:
			space = space[0]
		# Create a new blank map for the assembly layout
		n = self.size
		amap = [['',]*n, ]*n
		j = 0
		for row in range(n):
			new_row = ['']*n
			for col in range(n):
				a = self.shape.square_map()[row][col]
				if a == 0:
					new_row[col] = space
				else:
					new_row[col] = self.asmbly.cell_map[j]
					j += 1
			amap[row] = new_row
		return amap
		
		
	def __asmbly_str_map(self, space):
		'''Returns a nice printable string of the core assembly map'''
		printable = ""
		for row in self.__asmbly_square_map(space):
			for col in row:
				printable += str(col) + ' '
			printable += '\n'
		return printable
	
	
	def square_maps(self, which = "", space = ' '):
		'''Return arrays of the core shape map and the assembly map
		The user must specify "s"/"shape", or "a"/"ass"/"asmbly"/"assembly";
		else, the method will return both.'''
		which = which.lower()
		if which in ("s", "shape"):
			return self.shape.square_map()
		elif which in ("a", "ass", "asmbly", "assembly"):
			return self.__asmbly_square_map(space)
		elif not which:
			return (self.shape.square_map(), self.__asmbly_square_map(space))
		else:
			return which + " is not a valid option."
	
	def str_maps(self, which = "", space = ' '):
		'''Return nice little maps for printing of the core shape and assembly locations)
		The user must specify "s"/"shape", or "a"/"ass"/"asmbly"/"assembly";
		else, the method will return both.'''
		which = which.lower()
		if which in ("s", "shape"):
			return self.shape.str_map()
		elif which in ("a", "ass", "asmbly", "assembly"):
			return self.__asmbly_str_map(space)
		elif not which:
			return (self.shape.str_map(), self.__asmbly_str_map(space))
		else:
			return which + " is not a valid option."


class Reflector(object):
	'''Inputs:
		mat:	string; key of an instance of Material or Mixture
		thick:	float;	thickness in cm
	Optional input:
		name:	string;	default is empty string
	'''
	def __init__(self, material, thick, vfrac, name = ""):
		self.material = material
		self.thick = thick
		self.name = name
	def __str__(self):
		return self.name + " Reflector"


class Baffle(object):
	'''Inputs:
		mat:	key referring to an instance of Material in Case.materials
		thick:	thickness of baffle (cm)
		gap:	thickness of gap (cm) between the outside assembly
				(including the assembly gap) and the baffle itself
		'''
	def __init__(self, mat, thick, gap):
		self.mat = mat
		self.thick = thick
		self.gap = gap
	def __str__(self):
		return "Baffle (" + self.thick + " cm thick)"





# What to do if somebody tries to run the module
if __name__ == "__main__":
	print('''This is a module containing classes
 - Material(key_name, density, mat_fracs, mat_names)
 - Assembly(name, cells, [params, cellmaps, spacergrids])
 - Insert(key, [name, npins, cells, cellmaps, axial_elevs,
    axial_labels, npins, params, stroke, maxstep])
 - CoreMap(cell_map, [name, label])
 - SpacerGrid(name, height, mass, label, material)
 - CellMap(name, label, cell_map)
 - Cell(name, num_rings, radii, mats, label)
 - Core(pitch, size, height, rpower, rflow, asmbly,
 	[bc, bot_refl, top_refl, vessel_radii, vessel_mats,
 	baffle, control_bank, control_map, detector_map])
 - Reflector(mat, thick, vfrac, [name])
 - Baffle(mat, thick, gap)
''')
	
	
	
	

