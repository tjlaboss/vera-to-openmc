# nozzle.py
#
# Module for the Nozzle class used in the construction of Assembly instances

from pwr.mixture import Mixture


class Nozzle(object):
	'''Nozzle defined as a smeared material of a certain height and mass
	
	Parameters:
		height:		float; z-coordinate of the top of this nozzle.
					The coordinate of the bottom is determined automatically.
		mass:		float; mass in grams of nozzle material
		nozzle_mat:	instance of openmc.Material; composition of the nozzle itself
		mod_mat:	instance of openmc.Material; composition of the moderator
		npins:		integer; number of pins in a row. Used to calculate Nozzle area
		pitch:		float; pitch in cm between pins.  Used to calculate Nozzle area
		[name:		string; optional name for the nozzle material. Default is "nozzle-material".]
	
	Attributes:
		height:		[same as above]
		mass:		[same as above]
		material:	instance of openmc.Material; smearing of nozzle_mat and mod_mat
	'''
	
	def __init__(self, height, mass, nozzle_mat, mod_mat, npins, pitch, name = "nozzle-material"):
		self.height = height
		self.mass = mass
		self.name = name
		volume = (npins*pitch)**2 * height
		self.material = self.__mix(nozzle_mat, mod_mat, volume)
		
	def __mix(self, mat, mod, v):
		'''Mix materials in the way necessary to create the nozzle.
		
		WARNING: Currently only supports the same type of fraction (weight or atomic)
		
		Inputs:
			mat:	instance of openmc.Material describing the nozzle composition
			mod:	instance of openmc.Material describing the moderator
			v:		float; total volume in cm^3 of the nozzle region
		
		Output:
			mix:	instance of openmc.Material describing the smearing of 'mat' and 'mod'
		'''
		mat_vol = self.mass / mat.density
		mod_vol = v - mat_vol
		vfracs = [mat_vol / v, mod_vol / v]
		
		material = Mixture((mat, mod), vfracs, name = self.name)
		return material
		
	def __str__(self):
		return self.name


if __name__ == "__main__":
	print("This is a module for the Nozzle() class.")


