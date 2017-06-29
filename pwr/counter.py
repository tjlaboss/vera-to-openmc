# counter.py
#
# Container for the 'Counter' class, which allows the transfer of the 5 essential
# OpenMC counters back and forth between modules

class Counter(object):
	"""An essential class for the counting of OpenMC
	surface, cell, material, and universe IDs.
	
	Parameters: 	[integer; default value is 1]
		surface_count:		initial surface count
		cell_count:			initial cell count
		material_count:		initial material count
		universe_count:		initial universe count
		tally_count:        initial tally count
	
	Attributes:	[integer]
		surface:			current surface count
		cell:				current cell count
		material:			current material count
		universe:			current universe count
		tally:              current tally count
	"""
	def __init__(self, 	surface = 1,
				 cell = 1,
				 material = 1, 
				 universe = 1,
	             tally = 1 
	             ):
		self.surface = surface
		self.cell = cell
		self.material = material
		self.universe = universe
		self.tally = tally
	
	def __str__(self):
		rep = "Counter"
		rep += "\nSurface: \t" + str(self.surface)
		rep += "\nCell:    \t" + str(self.cell)
		rep += "\nMaterial:\t" + str(self.material)
		rep += "\nUniverse:\t" + str(self.universe)
		rep += "\nTally:   \t" + str(self.tally)
		return rep
		
	def add_surface(self):
		self.surface += 1
		return self.surface
	def add_cell(self):
		self.cell += 1
		return self.cell
	def add_material(self):
		self.material += 1
		return self.material
	def add_universe(self):
		self.universe += 1
		return self.universe
	def add_tally(self):
		self.tally += 1
		return self.tally
	
	
	
	
	
