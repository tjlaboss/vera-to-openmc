# counter.py
#
# Holder for the 'Counter' class, which allows the transfer of the 4 essential
# OpenMC counters back and forth between modules

from pwr.settings import SURFACE, CELL, MATERIAL, UNIVERSE
import openmc.AUTO_CELL_ID, openmc.AUTO_SURFACE_ID, openmc.AUTO_MATERIAL_ID, openmc.AUTO_UNIVERSE_ID

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
	def __init__(self, 	surface = openmc.AUTO_SURFACE_ID,
				 cell = openmc.AUTO_CELL_ID,
				 material = openmc.AUTO_MATERIAL_ID, 
				 universe = openmc.AUTO_UNIVERSE_ID):
		self.surface = surface + 1
		self.cell = cell + 1
		self.material = material + 1
		self.universe = universe + 1
	
	def __str__(self):
		rep = "Counter"
		rep += "\nSurface: \t" + str(self.surface)
		rep += "\nCell:    \t" + str(self.cell)
		rep += "\nMaterial:\t" + str(self.material)
		rep += "\nUniverse:\t" + str(self.universe)
		return rep
	
	
	def add_surface(self):
		self.surface += 1
	def add_cell(self):
		self.cell += 1
	def add_material(self):
		self.material += 1
	def add_universe(self):
		self.universe += 1
	
	
	
	
	
	
