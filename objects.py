# objects.py
#
# Module containing useful objects for read_xml.py

from math import sqrt

class Material(object):
	'''Basics of a material card
	Parameters:
		key_name:	string; unique material name
		density:	float; density in g/cm^3
		isotopes:	dictionary of {"isotope name":isotope_fraction}
	'''
	def __init__(self, key_name, density, isotopes):
		self.key_name = key_name
		self.density = density
		self.isotopes = isotopes

	def __str__(self):
		'''Use this to print a brief description of each material'''
		description = self.key_name + '\t@ ' + str(self.density) + ' g/cc\t(' + str(len(self.isotopes)) + ' isotopes)'
		return description
	
	def __eq__(self, other):
		return self.__dict__ == other.__dict__
	

class Assembly(object):
	'''VERA decks often contain descriptions of fuel assemblies.
	Although I am not sure how to represent these in OpenMC/OpenCG yet,
	it is useful to store assemblies as objects owned by a Case instance.
	
	Inputs:
		name: 			String containing the unique Assembly name
		cells:			Dictionary of Cell objects in this assembly {cell.label:cell}
		params:			Dictionary of all the other parameters provided
						in the Assembly block
		cellmaps: 		Dictionary of CellMap objects
		spacergrids:	Dictionary of SpacerGrid objects
	'''
	
	def __init__(self, name, cells, params = {}, cellmaps = {}, spacergrids = {}): # more inputs to come
		self.name = name
		self.cells = cells
		self.cellmaps = cellmaps
		self.spacergrids = spacergrids
	
		''' At this point, I'm thinking there has to be a better way to do this than to
		go through and grab ever parameter. Is there some way I can automate this so that
		
			<Parameter name="lower_nozzle_comp" type="string" value="ss"/>	# for example
			<Parameter name="lower_nozzle_mass" type="double" value="6250.0"/>
		
		gets translated to
		
			self.lower_nozzle_comp = str("ss")
			self.lower_nozzle_mass = float("6250.0") ??
		
		There must be. Will use a dictionary for now.'''
		
		self.params = params
		# Unpack the parameters that should "appear" in every case
		self.axial_labels = map(str, params["axial_labels"].strip('}').strip('{').split(','))
		self.axial_elevations = map(float, params["axial_elevations"].strip('}').strip('{').split(','))
		self.pitch = float(params["ppitch"])
		self.npins = int(params["num_pins"])
		
		
	def __str__(self):
		return self.name
	


class SpacerGrid(object):
	'''Object to hold properties of an assembly's spacer grids
	
	Inputs:
		name: 		String containing the name, which serves as a dictionary key in Case.grids
		height:		float
		mass:		float
		label:		string
		material:	instance of class Material
		'''
	
	def __init__(self, name, height, mass, label, material):
		self.name = name		
		self.height = height	
		self.mass = mass		
		self.label = label		
		self.material = material
		
	def __str__(self):
		return self.name
		
		

class CoreMap(object):
	'''
	Inputs: 
		cell_map: 	List of integers describing the assembly layout
	Optional:
		name: 		String containing the descriptive Assembly name
		label:		string containing the unique Assembly identifier
	'''
	def __init__(self, cell_map, name = "", label = ""):
		self.name = name 
		self.label = label
		self.cell_map = cell_map
	
	def __str__(self):
		return self.name
	
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
		printable = ""
		for row in smap:
			for col in row:
				printable += col + ' '
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
		asname:		string containing the name of the VERA assembly the cell is in (optional)
	'''
	
	
	def __init__(self, name, num_rings, radii, mats, label, asname = ""):
		self.name = name
		self.num_rings = num_rings
		self.radii = radii
		self.mats = mats
		self.label = label
		self.asname = asname
	
	def __str__(self):
		return self.name


class Core(object):
	'''Container for all the general and full-core properties
	
	Inputs:
		pitch:		float; 	assembly pitch in cm
		size:		int; 	number of assemblies across one axis of the full core
		height:		float;	total axial distance (cm) from the bottom core plate
					to the top core plate, excluding plate thickness
		shape:		list of integers containing a map of the shape of the core,
					which is converted to an instance of CoreMap (self.shape_map) 
					A 1 marks a valid assembly location; a 0, an invalid location
		asmbly:		list of stronggs containing a map of the fuel assemblies in the core, 
					which is converted to an instance of CoreMap (self.asmbly_map)
					Must conform to self.shape
		params:		dictionary of miscellaneous core parameters for possible later use
	
	Optional parameters:			
		bc:				dictionary of boundary conditions for top, bot, and rad.
						May be either "reflecting" or "vacuum". (Default: "vacuum")
		bot_refl:		instance of Reflector(mat, thick, vfrac) 
		top_refl:	 	  ^
		vessel_radii:	list of floats describing the radii of the reactor vessel layers
		vessel_mats:	list of strings referring to Material keys for each layer of the
						reactor vessel--must be same length as vessel_radii
		baffle:			
		
	
	'''
	def __init__(self, pitch, size, height, shape, asmbly_map, params, #rpower, rflow,
				 bc = {"bot":"vacuum",	"rad":"vacuum",	"top":"vacuum"},
				 bot_refl = None, top_refl = None, vessel_radii = [], vessel_mats = [], 
				 baffle = {}, control_bank = [], control_map = [], detector_map = []):
		
		self.pitch = pitch
		self.size = size
		self.height = height
		self.shape = shape
		self.asmbly_map = asmbly_map
		self.params = params
		
		self.bc = bc
		self.bot_refl = bot_refl
		self.top_refl = top_refl
		self.vessel_mats = vessel_mats
		self.vessel_radii = vessel_radii
		self.baffle = baffle
		self.control_bank = control_bank
		self.control_map = control_map
		self.detector_map = detector_map
	
	def __str__(self):
		c = str(max(self.vessel_radii))
		h = str(self.height)
		return "Core: r=" + c + "cm, z=" + h + "cm"


class Reflector(object):
	'''Inputs:
		mat:	instance of Material
		thick:	float;	thickness in cm
		vfrac:	float;	volume fraction
		[name]:	string;	default is empty string
	'''
	def __init__(self, mat, thick, vfrac, name = ""):
		self.mat = mat
		self.thick = thick
		self.vfrac = vfrac
		self.name = name
	def __str__(self):
		return self.name + " Reflector"


class Baffle(object):
	'''Inputs:
		mat:	instance of Material
		thick:	thickness of baffle (cm)
		gap:	thickness of gap (cm) between the outside assembly
				(including the assembly gap) and the baffle itself
		[name]:	string;	default is empty string
		'''
	def __init__(self, mat, thick, gap):
		self.mat = mat
		self.thick = thick
		self.vfrac = gap
	def __str__(self):
		return "Baffle (" + self.thick + " cm thick)"




# What to do if somebody tries to run the module
if __name__ == "__main__":
	print('''This is a module containing classes
 - Material(key_name, density, mat_fracs, mat_names)
 - Assembly(name, [params, cellmaps, spacergrids])
 - SpacerGrid(name, height, mass, label, material)
 - CellMap(name, label, cell_map)
 - Cell(name, num_rings, radii, mats, label)
 - Core(pitch, size, height, rpower, rflow, asmbly_map,
 	[bc, bot_refl, top_refl, vessel_radii, vessel_mats,
 	baffle, control_bank, control_map, detector_map])
 - Reflector(mat, thick, vfrac, [name])
 - Baffle(mat, thick, vfrac)
''')

