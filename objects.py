# objects.py
#
# Module containing useful objects for read_xml.py

from math import sqrt

class Material(object):
	'''Basics of a material card'''
	def __init__(self, key_name, density, mat_fracs, mat_names):
		self.key_name = key_name
		self.density = density
		self.mat_fracs = mat_fracs
		self.mat_names = mat_names

	def __str__(self):
		'''Use this to print a brief description of each material'''
		description = self.key_name + '\t@ ' + str(self.density) + ' g/cc\t(' + str(len(self.mat_names)) + ' isotopes)'
		return description
	

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
		
		self.params = params		# Note: I probably want to unpack these somehow
		
		
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
		
		

class CellMap(object):
	'''
	Inputs: 
		name: 		String containing the unique Assembly name
		cell_map: 	List of integers describing the assembly layout
		label:		string
	'''
	def __init__(self, name, label, cell_map):
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
		name: 		String containing the unique Cell name
		num_rings:	Number of concentric rings of different materials
		radii:		List of length {num_rings} containing the lengths of the respective rings
		mats:		List of length {num_rings} referencing Material objects of the respective rings
		label:		string
	'''
	
	
	def __init__(self, name, num_rings, radii, mats, label):
		self.name = name
		self.num_rings = num_rings
		self.radii = radii
		self.mats = mats
		self.label = label
	
	def __str__(self):
		return self.name


# What to do if somebody tries to run the module
if __name__ == "__main__":
	print '''This is a module containing classes
 - Material(key_name, density, mat_fracs, mat_names)
 - Assembly(name, [params, cellmaps, spacergrids])
 - SpacerGrid(name, height, mass, label, material)
 - CellMap(name, label, cell_map)
 - Cell(name, num_rings, radii, mats, label)
'''

