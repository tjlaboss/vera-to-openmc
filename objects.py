# objects.py
#
# Module containing useful objects for read_xml.py

from math import sqrt
from functions import clean
import isotopes

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
				total_wt += self.isotopes[iso] * isotopes.MASS[iso]
			for iso in self.isotopes:
				iso_wts[iso] = abs( self.isotopes[iso] * isotopes.MASS[iso] / total_wt )
		
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
				total_at += self.isotopes[iso] / isotopes.MASS[iso]
			for iso in self.isotopes:
				iso_ats[iso] = -abs( self.isotopes[iso] / isotopes.MASS[iso] / total_at )
		
			self.isotopes = iso_ats



class Mixture(Material):
	'''Two mixed Material instances. 
	Functionally exactly the same as Material, but initialized differently.'''
	def __init__(self, key_name, materials, vfracs):
		self.key_name = key_name
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
		
		self.params = params
		# Unpack the parameters that should appear in every case
		self.label = params["label"].lower()
		self.axial_labels = clean(params["axial_labels"], str)
		self.axial_elevations = clean(params["axial_elevations"], float)
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
		material:	string; key referring to an instance of class Material
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
				printable += str(col) + ' '
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
		rep = self.name + " (radius = " + str(max(self.radii)) + ')'
		return rep


class Core(object):
	'''Container for all the general and full-core properties
	
	Inputs:
		pitch:		float; 	assembly pitch in cm
		size:		int; 	number of assemblies across one axis of the full core
		height:		float;	total axial distance (cm) from the bottom core plate
					to the top core plate, excluding plate thickness
		shape:		list of integers containing a map of the shape of the core,
					which is converted to an instance of CoreMap. (Alternatively,
					an instance of CoreMap may be directly specified.)
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
		baffle:			dictionary of baffle properties: {"mat":Material key (string), 
						"gap": gap between oustside assembly and baffle in cm (float),
						"thick": thickness of the baffle material in cm (float) }
		control_bank,
		control_map,	Not coded yet, but they will likely be lists of strings in the
		detector_map:	style of asmbly_map
	'''

	def __init__(self, pitch, size, height, shape, asmbly, params, #rpower, rflow,
				 bc = {"bot":"vacuum",	"rad":"vacuum",	"top":"vacuum"},
				 bot_refl = None, top_refl = None, vessel_radii = [], vessel_mats = [], 
				 baffle = {}, control_bank = [], control_map = [], detector_map = []):
		
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
			space:	string (len=1) to represent a spot outside the core.
					Default is whitespace.'''
		# Create a new blank map for the assembly layout
		n = self.size
		amap = [['',]*n, ]*n
		j = 0
		for row in range(n):
			new_row = ['']*n
			for col in range(n):
				a = self.shape.square_map()[row][col]
				if a == 0:
					new_row[col] = space[0]
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
		mat:	instance of Material or Mixture
		thick:	float;	thickness in cm
	Optional input:
		name:	string;	default is empty string
	'''
	def __init__(self, mat, thick, vfrac, name = ""):
		self.mat = mat
		self.thick = thick
		self.name = name
	def __str__(self):
		return self.name + " Reflector"


class Baffle(object):
	'''Inputs:
		mat:	instance of Material
		thick:	thickness of baffle (cm)
		gap:	thickness of gap (cm) between the outside assembly
				(including the assembly gap) and the baffle itself
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
 - Core(pitch, size, height, rpower, rflow, asmbly,
 	[bc, bot_refl, top_refl, vessel_radii, vessel_mats,
 	baffle, control_bank, control_map, detector_map])
 - Reflector(mat, thick, vfrac, [name])
 - Baffle(mat, thick, vfrac)
''')
	
	
	
	

