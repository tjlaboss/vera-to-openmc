# PWR Assembly
# 
# Module for the OpenMC Python API. Once developed, it should
# contain everything needed to generate an openmc.Universe containing
# a model of a Westinghouse-style PWR assembly

import openmc
import objects
from functions import fill_lattice


class Mixture(openmc.Material):
	'''Mixture of multiple OpenMC materials.
	Designed to be functionally identical to a regular openmc.Material,
	but defined differently.
	
	WARNING: Currently only works for weight fractions and densities in
	grams per cubic centimeter (g/cc and g/cm^3).
	
	
	Parameters
    ----------
	
	materials:		list of instances of openmc.Material to mix
    vfracs:			list of floats describing the volume fraction of each
    				Material listed above.  
    
    material_id:	int, optional
        Unique identifier for the material. If not specified, an identifier will
        automatically be assigned.
    name:			str, optional
        Name of the material. If not specified, the name will be the empty
        string.
       
    
    Attributes
    ----------
    id : int
        Unique identifier for the material
    density : float
        Density of the material (units defined separately)
    density_units : str
        Units used for `density`. Can be one of 'g/cm3', 'g/cc', 'kg/cm3',
        'atom/b-cm', 'atom/cm3', 'sum', or 'macro'.  The 'macro' unit only
        applies in the case of a multi-group calculation.
    elements : list of tuple
        List in which each item is a 3-tuple consisting of an
        :class:`openmc.Element` instance, the percent density, and the percent
        type ('ao' or 'wo').
    nuclides : list of tuple
        List in which each item is a 3-tuple consisting of an
        :class:`openmc.Nuclide` instance, the percent density, and the percent
        type ('ao' or 'wo').
	
	'''
	
	def __init__(self, materials, vfracs, material_id = None, frac_type = 'wo', name = ""):
		super(Mixture, self).__init__(material_id, name)
		
		mix_isos = []
		density = 0.0
	
		for i in range(len(materials)):
			density += materials[i].density * (vfracs[i] / sum(vfracs))
		for i in range(len(materials)):
			mat = materials[i]
			#mat.convert_ao_to_wo() --> Exists in VERA-to-OpenMC, but not here
			wtf = vfracs[i]*mat.density 	# weight fraction of entire material
			for iso in mat.get_all_nuclides().values():
				nuclide = iso[0]
				new_wt = wtf*iso[1] / density
				if iso in mix_isos:
					old_wt = mix_isos[iso][1]
					mix_isos.append((nuclide, new_wt + old_wt, frac_type))
				else:
					mix_isos.append((nuclide, new_wt, frac_type))
					
		self._nuclides = mix_isos
		self.set_density("g/cc", density)



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
		[name:		string; optional name for the nozzle. Default is "nozzle-material".]
	
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
		vfracs = [mat_vol / v, mat_vol / v]
		
		material = Mixture((mat, mod), vfracs, name = self.name)
		return material
		
	def __str__(self):
		return self.name


def add_grid_to(cell, t, material):
	'''Given a pincell to be placed in a lattice, add
	the spacer grid to the individual cell.
	
	Inputs:
		cell:		instance of openmc.Universe describing the pincell
					and its concentric rings of instances of openmc.Cell
		t:			float; thickness in cm of one edge of the spacer between
					two pincells (HALF the total thickness)
		material:	instance of openmc.Material from which the spacer is made
	
	Output:
		new_cell:	instance of openmc.Universe describing the pincell
					surrounded by the spacer
	'''
	assert isinstance(cell, openmc.Universe), str(cell) + "must be an openmc.Universe (not a Cell)"
	assert isinstance(material, openmc.Material), str(material) + "is not an instance of openmc.Material" 
	
	


# Test
if __name__ == '__main__':
	
	# Define a global test moderator
	mod = openmc.Material(1, "mod")
	mod.set_density("g/cc", 1.0)
	mod.add_nuclide("h-1", 2.0/3, 'ao')
	mod.add_nuclide("o-16", 1.0/3, 'ao')
	
	# Define a simple test material
	iron = openmc.Material(2, "iron")
	iron.set_density("g/cc", 7.8)
	iron.add_element("Fe", 1, 'ao', expand=True)
	
	mix1 = Mixture([mod, iron], [0.5,0.5], 33, 'watery iron')
	assert isinstance(mix1, openmc.Material)	
	noz1 = Nozzle(10, 6250, iron, mod, 1, 10)

	# Test a pincell
	

