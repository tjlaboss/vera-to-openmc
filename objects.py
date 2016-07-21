# objects.py
#
# Module containing useful objects for read_xml.py


class Assembly(object):
	'''VERA decks often contain descriptions of fuel assemblies.
	Although I am not sure how to represent these in OpenMC/OpenCG yet,
	it is useful to store assemblies as objects owned by a Case instance.
	
	Inputs:
		name: 		String containing the unique Assembly name
		cellmaps: 	List of CellMap objects
		cells:		List of Cell objects
		label:		...
	'''
	
	def __init__(self, name, params = {}, cellmaps = {}, spacergrids = {}): # more inputs to come
		self.name = name
		self.cellmaps = cellmaps
	
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
	'''Object to hold properties of an assembly's spacer grids'''
	
	def __init__(self, name, height, mass, label, material):
		self.name = name		# string (serves as dictionary key in Case.grids)
		self.height = height	# float
		self.mass = mass		# float
		self.label = label		# string
		self.material = material# instance of class Material
		
	def __str__(self):
		return self.name
		
		



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

