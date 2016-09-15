# Module for smeared materials (mixtures)

from openmc import Material

class Mixture(Material):
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
	
		
if __name__ == "__main__":
	print("This is a module for Mixture(), a child class of openmc.Material.")
	
	
