# counter.py
#
# Container for the 'Counter' class, which allows the transfer of the 4 essential
# OpenMC counters back and forth between modules

from pwr.settings import SURFACE, CELL, MATERIAL, UNIVERSE
from openmc import AUTO_SURFACE_ID, AUTO_CELL_ID, AUTO_MATERIAL_ID, AUTO_UNIVERSE_ID

class Counter(object):
	'''An essential class for the counting of OpenMC 
	surface, cell, material, and universe IDs.
	
	Parameters: [integer; defaults are openmc.AUTO_(type)_ID]
		surface_count:		initial surface count
		cell_count:			initial cell count
		material_count:		initial material count
		universe_count:		initial universe count
	
	Attributes:	[integer]
		surface:			current surface count
		cell:				current cell count
		material:			current material count
		universe:			current universe count
	'''
	def __init__(self, 	surface = AUTO_SURFACE_ID,
				 cell = AUTO_CELL_ID,
				 material = AUTO_MATERIAL_ID, 
				 universe = AUTO_UNIVERSE_ID):
		self.surface = surface
		self.cell = cell
		self.material = material
		self.universe = universe
	
	def __str__(self):
		rep = "Counter"
		rep += "\nSurface: \t" + str(self.surface)
		rep += "\nCell:    \t" + str(self.cell)
		rep += "\nMaterial:\t" + str(self.material)
		rep += "\nUniverse:\t" + str(self.universe)
		return rep
	
	
	def count(self, TYPE):
		if TYPE == SURFACE:
			c = self.add_surface()
		elif TYPE == CELL:
			c = self.add_cell()
		elif TYPE == MATERIAL:
			c = self.add_material()
		elif TYPE == UNIVERSE:
			c = self.add_universe()
		else:
			raise TypeError("TYPE must be SURFACE, CELL, MATERIAL, or UNIVERSE")
		return c
		
	
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
	
	
	
	
	
	
